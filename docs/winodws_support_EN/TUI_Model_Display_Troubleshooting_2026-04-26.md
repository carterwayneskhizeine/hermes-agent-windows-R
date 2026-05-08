# TUI Model Display Error Troubleshooting: Showing claude-sonnet-4 When Resuming Sessions

> Date: 2026-04-26
> Symptom: After resuming a session via Web Dashboard `/chat?resume=<id>`, the model badge in the TUI upper-right corner always displays `claude-sonnet-4`, inconsistent with the actual model in use
> Affected components: `tui_gateway/server.py`, Web ChatSidebar, Ink TUI status bar

---

## Problem Symptom

When resuming a session via URL `http://127.0.0.1:<port>/chat?resume=<session_id>` in the Web Dashboard, the model name in the TUI upper-right corner always switches to `claude-sonnet-4`, even if the configured model is completely different (e.g., `glm-4.7`, `MiniMax-M2.7`, `deepseek-chat`).

The actual inference requests use the correct model; only the display label is wrong.

---

## Architecture Background

The web dashboard's chat page involves three independent processes:

```
┌─────────────────────────────────────────────────────┐
│  Browser (ChatPage.tsx)                              │
│    ├── xterm.js terminal ← WebSocket /api/pty        │
│    └── ChatSidebar  ← WebSocket /api/ws + /api/events│
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│  Python Web Server (FastAPI/uvicorn)                 │
│    ├── /api/pty → PtyBridge → Node.js TUI process    │
│    ├── /api/ws  → tui_gateway.ws.handle_ws (in-proc) │
│    └── /api/events ← /api/pub (event broadcast)      │
└──────────────┬──────────────────────────────────────┘
               │ PTY (ConPTY on Windows)
┌──────────────▼──────────────────────────────────────┐
│  Node.js TUI (ui-tui/dist/entry.js)                  │
│    └── spawn: python -m tui_gateway.entry             │
│        └── tui_gateway.server (independent instance)  │
└─────────────────────────────────────────────────────┘
```

Key points:

1. The **Web Server process** directly loads `tui_gateway.server` via `/api/ws`, handling ChatSidebar's JSON-RPC requests (creating ephemeral sessions).
2. The **PTY subprocess** TUI communicates with another independent `tui_gateway.server` instance via stdio.
3. Both gateway instances execute `_resolve_model()` independently but share the same `HERMES_HOME` environment variable and config file.
4. **Model display source**: ChatSidebar's model badge comes from the `session.info` event of its ephemeral session; the Ink TUI's status bar comes from the PTY gateway's `session.info` event.

---

## Root Cause Analysis

### Direct Cause

The `_resolve_model()` function in `tui_gateway/server.py` returns a hardcoded fallback value when it cannot get the model name from the config:

```python
# tui_gateway/server.py:565-576
def _resolve_model() -> str:
    env = (
        os.environ.get("HERMES_MODEL", "")
        or os.environ.get("HERMES_INFERENCE_MODEL", "")
    ).strip()
    if env:
        return env
    m = _load_cfg().get("model", "")
    if isinstance(m, dict):
        return str(m.get("default", "") or "").strip()
    if isinstance(m, str) and m:
        return m.strip()
    return "anthropic/claude-sonnet-4"  # ← hardcoded fallback
```

When `config.yaml` **has no `model` section** or the `model` section is empty:

```yaml
# Scenario A: no model config at all
providers: {}

# Scenario B: model exists but has no default key
model:
  provider: deepseek
  base_url: https://api.deepseek.com/
```

Execution path analysis:

| Step | Scenario A | Scenario B |
|------|------------|------------|
| `m = _load_cfg().get("model", "")` | `""` (empty string) | `{"provider":"deepseek","base_url":"..."}` (dict) |
| `isinstance(m, dict)` | `False` | `True` |
| `m.get("default", "")` | — | `""` (empty string) |
| `str("" or "").strip()` | — | `""` |
| Final return value | **`"anthropic/claude-sonnet-4"`** | **`""` (empty string)** |

Scenario A directly hits the hardcoded fallback. Scenario B returns an empty string, handled by upstream `_session_info()` → `getattr(agent, "model", "")`.

### Database Evidence

Recent session records in the `state.db` for the `turing` profile:

```
id=20260426_132134_...  model='anthropic/claude-sonnet-4'  ← hardcoded fallback
id=mofbh3lqo5wqm4...   model='MiniMax-M2.7'
id=20260425_122529_...  model='MiniMax-M2.7'
```

The latest session record confirms `model='anthropic/claude-sonnet-4'` comes from the hardcoded fallback, not user configuration.

### Aggravating Factor

The silent exception handling in `_load_cfg()` makes the problem hard to detect:

```python
# tui_gateway/server.py:447-468
def _load_cfg() -> dict:
    global _cfg_cache, _cfg_mtime
    try:
        import yaml
        # ... load config ...
        return data
    except Exception:   # ← swallows all exceptions
        pass
    return {}           # ← returns empty dict
```

If `pyyaml` is not installed (e.g., the gateway subprocess uses the wrong Python interpreter), config loading fails silently, returning an empty dict, causing `_resolve_model()` to fall through to the hardcoded fallback.

### Model Display Data Flow

```
session.resume / session.create
  └→ _make_agent(sid, key, session_id=...)
       ├→ model, provider = _resolve_startup_runtime()
       │    └→ model = _resolve_model()  ← returns "anthropic/claude-sonnet-4" here
       └→ AIAgent(model=model, ...)
            └→ self.model = model

_init_session(sid, key, agent, ...)
  └→ _emit("session.info", sid, _session_info(agent))
       └→ info["model"] = getattr(agent, "model", "")
            └→ WebSocket → frontend display
```

**Key**: When resuming a session, the old model is not read from the database; instead `_resolve_model()` re-parses the current config. If config is empty, the fallback is used.

---

## Fix Methods

### Immediate Fix

Ensure `model.default` has a value in `config.yaml`:

```yaml
model:
  default: deepseek-chat   # ← must be set, otherwise falls back to hardcoded value
  provider: deepseek
```

### Verification

```bash
# 1. Confirm HERMES_HOME points to the correct profile
export HERMES_HOME="C:\Users\<user>\.hermes\profiles\<profile>"

# 2. Activate venv (ensure pyyaml is available)
.\venv\Scripts\Activate.ps1

# 3. Verify _resolve_model() returns the correct value
python -c "
import os
os.environ['HERMES_HOME'] = '$env:HERMES_HOME'
from tui_gateway.server import _resolve_model
print(_resolve_model())
"
# Expected output: the model.default value you set in config.yaml

# 4. Start dashboard
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

---

## Suggested Improvements

### 1. Add Fallback Warning Log to `_resolve_model()`

```python
def _resolve_model() -> str:
    # ... existing logic ...
    fallback = "anthropic/claude-sonnet-4"
    logger.warning(
        "No model configured (no HERMES_MODEL env var, "
        "no model.default in %s/config.yaml). "
        "Falling back to hardcoded default: %s",
        _hermes_home, fallback,
    )
    return fallback
```

### 2. Improve `_load_cfg()` Exception Handling

```python
def _load_cfg() -> dict:
    # ... existing logic ...
    except Exception as e:
        logger.warning("Failed to load config from %s/config.yaml: %s", _hermes_home, e)
    return {}
```

### 3. Consider Making the Fallback Model Configurable

Define the default model in `hermes_constants.py` or `config.yaml` to avoid hardcoding a specific vendor's model name.

---

## Related File Index

| File | Line | Description |
|------|------|-------------|
| `tui_gateway/server.py` | L565-576 | `_resolve_model()` — hardcoded fallback |
| `tui_gateway/server.py` | L447-468 | `_load_cfg()` — silent exception handling |
| `tui_gateway/server.py` | L1331-1361 | `_make_agent()` — calls `_resolve_model()` when creating agent |
| `tui_gateway/server.py` | L1685-1723 | `session.resume` handler — calls `_make_agent()` when resuming |
| `tui_gateway/server.py` | L1499-1628 | `session.create` handler — calls `_make_agent()` when creating new session |
| `tui_gateway/server.py` | L917-919 | `_session_info()` — extracts model name from agent.model |
| `tui_gateway/server.py` | L579-611 | `_resolve_startup_runtime()` — model + provider resolution |
| `tui_gateway/ws.py` | L31 | `from tui_gateway import server` — in-process gateway import |
| `tui_gateway/entry.py` | L8 | Gateway subprocess entry point |
| `ui-tui/src/gatewayClient.ts` | L124 | Node.js TUI spawns gateway subprocess |
| `web/src/components/ChatSidebar.tsx` | L307 | ChatSidebar model badge rendering |
| `web/src/components/ChatSidebar.tsx` | L94-102 | ChatSidebar `session.info` event listener |
| `web/src/lib/gatewayClient.ts` | L120-122 | Browser WebSocket connects to `/api/ws` |
