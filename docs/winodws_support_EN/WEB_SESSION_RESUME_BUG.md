# Web Dashboard /chat Page Extra TUI Session Creation Issue

> Date: 2026-05-01
>
> Environment: Windows 11 Pro, hermes dashboard --tui, accessing http://127.0.0.1:9119

## Problem Description

Every time the web dashboard's `/chat` page is visited (including resuming a historical session from the sessions page), an **extra empty TUI session is created**. The resumed session itself restores correctly (conversation content is not lost), but an extra empty TUI session appears on the `/sessions` page.

Specific symptoms:
- Clicking the ▶ (resume in chat) button for a session on `/sessions` → navigates to `/chat?resume=<id>` → session resumes successfully → but an extra new empty session is created simultaneously
- Directly refreshing the `/chat` page → also creates a new empty session
- Result: `/sessions` page accumulates empty sessions continuously

## Reproduction Steps

1. Launch `hermes dashboard`
2. Have some conversation on the `/chat` page
3. Switch to `/sessions` page → **at this point an extra new empty session is already visible**
4. Click the ▶ button for the conversation session, navigate to `/chat?resume=<id>`
5. The selected session resumes correctly, all conversation content is present
6. Switch back to `/sessions` page → **another new empty session appears**

## Architecture Overview

The web dashboard's chat page is not a standalone frontend application, but an **embedded TUI**:

```
Browser (xterm.js)
  ↕ WebSocket (/api/pty)
Backend web_server.py (FastAPI)
  ↕ PTY bridge (pywinpty on Windows)
TUI Node.js process (Ink-based React CLI)
  ↕ RPC
Gateway (session management / LLM API)
```

The browser connects to the backend `/api/pty` via WebSocket, and the backend spawns a TUI subprocess (Node.js + Ink) running in a PTY. **Each WebSocket connection corresponds to an independent TUI process.** When the TUI process starts, it calls `newSession()` to create a new session by default; it only calls `resumeById()` when the `HERMES_TUI_RESUME` environment variable is set.

## Root Cause Analysis

Core issue: **ChatPage mounts and creates a PTY connection when the dashboard loads, regardless of whether the user is actually on the /chat page.**

### 1. ChatPage Persistent Mount (`web/src/App.tsx` lines 576-602)

```tsx
// ChatPage renders outside Routes, mounted when dashboard loads
{embeddedChat && !chatOverriddenByPlugin && (
  <div
    data-chat-active={isChatRoute ? "true" : "false"}
    className={cn(
      "min-h-0 min-w-0",
      isChatRoute ? "flex flex-1 flex-col" : "hidden",  // hidden but still mounted
    )}
    aria-hidden={!isChatRoute}
  >
    <ChatPage isActive={isChatRoute} />
  </div>
)}
```

ChatPage is mounted immediately when the dashboard starts. Even when the user is on the `/sessions` page (ChatPage is in `hidden` state), the component already exists.

### 2. WS Effect Does Not Depend on isActive (`web/src/pages/ChatPage.tsx`)

```tsx
// Line 243: effect doesn't check isActive, connects as long as host exists
useEffect(() => {
  const host = hostRef.current;
  if (!host) return;
  // ...
  const url = buildWsUrl(token, resumeRef.current, channel);
  const ws = new WebSocket(url);
  // ...
}, [channel]);  // only depends on channel, not isActive
```

**The component creates a WebSocket immediately upon mounting → backend spawns PTY → TUI starts → `newSession()` → empty session created.** At this point the user may still be on the `/sessions` page and hasn't even entered `/chat`.

### 3. Complete Timing Issue

```
Dashboard loads
  → App.tsx renders, ChatPage mounts (hidden)
  → WS effect fires, WebSocket connects to /api/pty (no resume parameter)
  → Backend spawns TUI process, HERMES_TUI_RESUME is empty
  → TUI calls newSession() → creates empty session ①

User clicks resume on /sessions page
  → navigate('/chat?resume=<session_id>')
  → ChatPage becomes visible, but component is not remounted

If resume parameter is passed successfully:
  → Old WS disconnects → new WS reconnects with parameters
  → Backend spawns new TUI process, HERMES_TUI_RESUME=<session_id>
  → TUI calls resumeById() → restores old session ✓
  → But empty session ① already exists in sessions list
```

### 4. Resume Parameter Passing (Fixed)

The original code used `useRef` to save the resume parameter, only reading it at first mount:

```tsx
const resumeRef = useRef<string | null>(searchParams.get("resume"));
```

At first mount, the URL had no `?resume=` parameter, so `resumeRef.current` was always `null`.

Changed to `useState` + effect watching `searchParams`, **fix is effective**:

```tsx
const [resumeId, setResumeId] = useState<string | null>(
  searchParams.get("resume"),
);

useEffect(() => {
  setResumeId(searchParams.get("resume"));
}, [searchParams]);

// WS effect dependency also updated
}, [channel, resumeId]);
```

Now after clicking resume from the sessions page, the URL correctly changes to `/chat?resume=<session_id>`, the WS effect reconnects with the resume parameter, and the TUI correctly restores the specified session.

**But the root issue (extra empty sessions) still exists**, because the resume parameter fix only addresses "which session to resume", not "an empty session is created when the dashboard loads".

### 5. Configuration Workaround (Partially Effective)

```yaml
# ~/.hermes/config.yaml
display:
  tui_auto_resume_recent: true
```

This makes the TUI automatically resume the most recent session instead of creating a new one, but:
- Cannot specify which particular session to resume
- Still cannot resolve the root issue of "dashboard load creates extra sessions"

## Related File List

| File | Key Location | Purpose |
|------|--------------|---------|
| `web/src/App.tsx` | Lines 576-602 | ChatPage persistent mount (hidden but not unmounted) |
| `web/src/pages/ChatPage.tsx` | Line 149 | Resume parameter storage (original useRef) |
| `web/src/pages/ChatPage.tsx` | Lines 243-630 | WS effect, does not check isActive |
| `web/src/pages/ChatPage.tsx` | Line 486 | `buildWsUrl(token, resumeRef.current, channel)` |
| `web/src/pages/ChatPage.tsx` | Line 621 | Effect dependency `[channel]`, no resume/isActive |
| `web/src/pages/SessionsPage.tsx` | Lines 356-370 | Resume button, `navigate('/chat?resume=...')` |
| `hermes_cli/web_server.py` | ~Line 2741 | `/api/pty` WS endpoint, reads resume parameter |
| `hermes_cli/web_server.py` | ~Line 2654 | `_resolve_chat_argv()` sets `HERMES_TUI_RESUME` |
| `ui-tui/src/config/env.ts` | Line 3 | `STARTUP_RESUME_ID = process.env.HERMES_TUI_RESUME` |
| `ui-tui/src/app/createGatewayEventHandler.ts` | ~Line 181 | resume vs newSession branch |

## Possible Solution Directions

### Direction A: Delay PTY Connection Until User Actually Enters /chat

Add an `isActive` guard in the WS effect, only creating a connection when the user is truly on the `/chat` page:

```tsx
useEffect(() => {
  const host = hostRef.current;
  if (!host || !isActive) return;  // add isActive check
  // ... WebSocket creation ...
}, [channel, isActive, resumeId]);
```

This way, dashboard load won't create empty sessions — connections are only established when the user actually enters the chat page.

### Direction B: Change ChatPage from Persistent Mount to Route Mount

Have the `/chat` route render ChatPage directly, unmounting when navigated away:

```tsx
<Routes>
  <Route path="/chat" element={<ChatPage isActive={true} />} />
  {/* ... */}
</Routes>
```

Each navigation to `/chat` remounts the component, and `searchParams.get("resume")` correctly reads the URL parameter. The trade-off is that the PTY process is destroyed when leaving the chat page.

### Direction C: Use Route State or Global Variable to Pass Resume ID

Avoid depending on `useSearchParams`, use `navigate('/chat', { state: { resume } })` or `window.__HERMES_RESUME_ID__`:

```tsx
// SessionsPage.tsx
navigate('/chat', { state: { resume: session.id } });

// ChatPage.tsx
const location = useLocation();
const resumeId = location.state?.resume ?? null;
```

### Direction D: Backend Session State Management

Track channel → session mapping in `web_server.py`. When a new connection is established and there's already an active session, automatically pass `HERMES_TUI_RESUME` to the TUI.
