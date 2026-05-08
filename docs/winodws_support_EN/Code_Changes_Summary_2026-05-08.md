# Hermes Windows Adaptation Code Changes Summary

> Updated: 2026-05-08
> Baseline: Branch hermes/2026-05-07 (commit a57968642)
> Scope: Sync upstream main (a3131862b), resolve 4 merge conflicts in 2 files, retain all Windows optimizations

---

## Operation Overview

Created `hermes/2026-05-08` from `hermes/2026-05-07`, merged the latest upstream `main` commits (231 commits, 227 non-merge commits), covering 321 files and +32,433 / -4,973 line changes. Manually resolved 4 conflicts in 2 files, all Windows adaptation patches fully retained.

---

## Merge Statistics

| Item | Count |
|------|-------|
| Upstream commits merged | 231 (including 4 merge commits) |
| Non-merge upstream commits | 227 |
| Changed files | 321 |
| Files with manually resolved conflicts | 2 (4 conflicts) |
| Windows optimizations lost | 0 |

---

## Conflict Resolution Details

### 1. tools/environments/local.py (1 conflict + 1 redundancy cleanup)

**Conflict cause:**
We had already added Windows MSYS → Windows path conversion in 04-24 (calling `msys_path_to_windows(self.cwd)` to get `popen_cwd`), and integrated it with `_resolve_safe_cwd` in 05-07. Upstream this time added a functionally equivalent inline implementation: using a regex `re.match(r'^/[a-zA-Z]/', _popen_cwd)` to do one more Git Bash-style path conversion before `subprocess.Popen`, passing `cwd=_popen_cwd`.

**Resolution:**
Retained our centralized helper implementation (`popen_cwd` + `_resolve_safe_cwd`), deleted the redundant `_popen_cwd` inline block added by upstream as well as the `import re` that was introduced but is no longer used. The final `subprocess.Popen` only uses `cwd=popen_cwd`.

**Rationale:** Our implementation goes through `msys_path_to_windows` / `windows_path_to_msys` in `tools.platform_compat`, correctly handling multiple drive letters (including lowercase drives), escape characters, and cwd invalidation fallback. The regex version doesn't have this coverage, and having both introduces unnecessary maintenance overhead.

---

### 2. web/src/pages/ChatPage.tsx (3 conflicts)

**Conflict cause:**
Our Windows session resume fix added in 05-01 (commit `c42435d32`, documented in `WEB_SESSION_RESUME_BUG.md`) implemented lazy-loading PTY:
- Introduced `routeResumeId` / `chatActivated` / `ptyResumeId` / `shouldConnectPty` state management
- WebSocket only established when `shouldConnectPty` is true, using `ptyResumeId` as the PTY identifier
- `useEffect` depends on `[channel, ptyResumeId, shouldConnectPty]`

Upstream during the 05-07 period introduced the "follow latest child session" capability (`b12a5a72b` Follow latest child session on dashboard resume, and `12a0f5901` finalizing the resumeId → resumeParam rename):
- Added `useEffect` calling `api.getSessionLatestDescendant(resumeParam)`, automatically jumping the `?resume=` parameter to the latest child session
- Added `resumeParam` to `channel = useMemo(..., [resumeParam])` dependency
- WebSocket changed to use `resumeParam`, `useEffect` depends on `[channel, resumeParam]`

**Resolution:**
Merged both sides' logic — retained our lazy-loading PTY body (`routeResumeId` / `ptyResumeId` / `shouldConnectPty`), while introducing upstream's "follow latest child session" `useEffect`, but rewriting internal variables from `resumeParam` to our `routeResumeId`. `useSearchParams` updates flow back to `routeResumeId`, then sync to `ptyResumeId` via `if (isActive && ptyResumeId !== routeResumeId)`, naturally connecting the chain.

WebSocket / useEffect dependencies retained as our version (`buildWsUrl(token, ptyResumeId, channel)`, `[channel, ptyResumeId, shouldConnectPty]`). `channel`'s `useMemo` dependency remains `[]`, since `useEffect` already watches `ptyResumeId` and will automatically reconnect on session switch, so channel doesn't need to regenerate.

```tsx
const routeResumeId = searchParams.get("resume");
const channel = useMemo(() => generateChannelId(), []);
const [chatActivated, setChatActivated] = useState(isActive);
const [ptyResumeId, setPtyResumeId] = useState<string | null>(() =>
  isActive ? routeResumeId : null,
);
if (isActive && !chatActivated) setChatActivated(true);
if (isActive && ptyResumeId !== routeResumeId) setPtyResumeId(routeResumeId);
const shouldConnectPty = chatActivated || isActive;

// Upstream: follow latest child session
useEffect(() => {
  if (!routeResumeId) return;
  let cancelled = false;
  api.getSessionLatestDescendant(routeResumeId).then((res) => {
    if (cancelled || !res.session_id || res.session_id === routeResumeId) return;
    const next = new URLSearchParams(searchParams);
    next.set("resume", res.session_id);
    setSearchParams(next, { replace: true });
  }).catch(() => {});
  return () => { cancelled = true; };
}, [routeResumeId, searchParams, setSearchParams]);
```

---

## Upstream Important Changes

| Direction | Description |
|-----------|-------------|
| Dashboard session resume | Follow latest child session (`b12a5a72b`) + resumeId rename finalization (`12a0f5901`) |
| Kanban tooltips & docs | Dashboard new tooltips and documentation links (`7d66d30d7`) |
| Kanban specify | Added `specify` assistant LLM to enrich triage tasks (`24d48ffb8`) |
| Kanban tenant filtering | Dashboard filters panels by selected tenant (`162ad3dd1`) |
| Cron route intent | `deliver=all` fan-out to all connected channels (`486b14b42`) |
| Cron fix | Start MCP servers before constructing AIAgent (`04918345e`) |
| MCP capability gating | Tool stubs enabled based on server capability declarations (`74c9c0eec`) |
| MCP channels_list | Unpack platforms field (`292f46836`) |
| Web search | Added Brave Search and DDGS providers (`04193cf71`) |
| Auth | Nous refresh token via header; rotation payload test (`b32461f6e`, `80775d758`) |
| Auth model switch | Clear stale Ollama credentials after switching provider (`7338e5d9b`) |
| Goals | Auto-pause when judge model output cannot be parsed (`307c85e5c`); status notification delayed until after response delivery (`03ddff889`) |
| Analytics | Prevent silent token loss + Claude 4.5–4.7 pricing (`d87c7b99e`) |
| Termux | Added `termux-all` install profile + doctor fallback (`732a6c45f`, `dc5ef1ac8`, `da18fd084`) |
| ACP | File attachment inline resources + image direct-pass image_url (`733e297b8`, `7e2af0c2e`) |
| Webhook | INSECURE_NO_AUTH only allows loopback (`fb4f95356`, `898b6d7d5`) |
| Telegram | Forum General topic_id=1 typing indicator (`2564132a1`) |
| QQ Bot | Inline keyboard for tool approval UX (`4de3ef38b`) |
| Google Workspace | `--check-live` detects disabled_client and salvages (`5fa493a2c`, `83c23e886`) |
| Updater | Send heartbeat + reset-failed during dependency install (`54c0b10d1`, `1d2029b2b`) |
| Installer | `UV_NO_CONFIG=1` avoids permission denial under sudo (`c80fa728b`) |
| Hermes config | Serialize access to avoid race conditions (`34f729735`) |
| run_agent | Fix orphan tool-tail causing empty response infinite loop (`812ce0b98`) |
| TUI | Segment turns with rule above non-first user messages + ticker dead zone trim (`42f9234da`) |
| Setup wizard | Quick setup includes terminal backend (`7190e20e0`) |
| Model directory | Added multiple new model entries |

---

## Windows Optimization Retention Confirmation

| Windows Patch | File | Status |
|---------------|------|--------|
| WSL bash detection (`_is_wsl_bash`) | `tools/environments/local.py` | ✅ Auto-merged, retained |
| Git Bash path detection priority | `tools/environments/local.py` | ✅ Auto-merged, retained |
| MSYS path conversion + dual-path storage + `_resolve_safe_cwd` integration | `tools/environments/local.py` | ✅ Manually resolved conflict, retained (deleted upstream redundant regex) |
| Windows pipe reading (`_drain_windows`) | `tools/environments/base.py` | ✅ Auto-merged, retained |
| Cross-platform helper library | `tools/platform_compat.py` | ✅ Auto-merged, retained |
| Dangerous command interception | `tools/approval.py` | ✅ Auto-merged, retained |
| stdin/stdout/stderr UTF-8 reconfiguration | `tui_gateway/entry.py` | ✅ Auto-merged, retained |
| StdioTransport bypasses TextIOWrapper (CJK GBK path) | `tui_gateway/transport.py` | ✅ Auto-merged, retained |
| slash_worker full UTF-8 reconfiguration | `tui_gateway/slash_worker.py` | ✅ Auto-merged, retained |
| PID file encoding + taskkill UTF-8 | `gateway/status.py` | ✅ Auto-merged, retained |
| ConPTY Windows backend (`_PTY_BACKEND == "win"`) | `hermes_cli/pty_bridge.py` | ✅ Auto-merged, retained |
| HERMES_PYTHON environment variable passing | `hermes_cli/web_server.py` / `main.py` | ✅ Auto-merged, retained |
| npm subprocess UTF-8 encoding | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| main() UTF-8 reconfiguration | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| systemctl subprocess UTF-8 encoding (3 locations) | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| profiles.py `which` UTF-8 encoding | `hermes_cli/profiles.py` | ✅ Auto-merged, retained |
| plugins install/pull UTF-8 encoding | `hermes_cli/plugins_cmd.py` | ✅ Auto-merged, retained |
| Web session lazy-loading PTY + follow latest child session merge | `web/src/pages/ChatPage.tsx` | ✅ Manually resolved conflict, retained (merged upstream descendant-follow) |

---

## Operation Summary

The 05-08 work was a pure sync operation with no new Windows adaptation code. The core work was:

1. **Losslessly merged 231 upstream commits**: Covering Dashboard session follow-latest-child, Kanban tooltip and specify, Cron route intent, Web search Brave/DDGS provider, Auth Nous refresh header, Goals auto-pause, Termux install profile, ACP attachment inline, QQ Bot inline keyboard approval, etc.
2. **Resolved 4 conflicts in 2 files**:
   - `tools/environments/local.py` (1 conflict) — deleted upstream's regex cwd conversion that duplicates our functionality, unified through `msys_path_to_windows` + `_resolve_safe_cwd`
   - `web/src/pages/ChatPage.tsx` (3 conflicts) — retained lazy-loading PTY body, added upstream descendant-follow `useEffect` (variable names aligned to `routeResumeId`)
3. **All Windows optimizations fully retained**: All 18 Windows patches (including all 04-24, 04-26, 04-27, 04-29, 04-30, 05-01, 05-07 changes) lost none

---

> Merge baseline: hermes/2026-05-07 (a57968642) merged upstream main (a3131862b)
> Merge commit: on hermes/2026-05-08 branch
