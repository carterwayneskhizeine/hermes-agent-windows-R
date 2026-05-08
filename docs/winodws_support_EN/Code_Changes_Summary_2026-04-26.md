# Hermes Windows Adaptation Code Changes Summary

> Updated: 2026-04-26
> Baseline: Commit 093bf90b (after upstream main sync)
> Scope: subprocess encoding fix, terminal output capture, TUI Chinese garbled text, ConPTY support, Git Bash path compatibility

---

## Modified File List

| File Path | Modification Type | Description |
|-----------|-------------------|-------------|
| `WINDOWS_CHAT_ISSUES.md` | Added | Windows TUI chat issue troubleshooting log |
| `hermes_cli/pty_bridge.py` | Refactored | pywinpty ConPTY Windows backend |
| `hermes_cli/web_server.py` | Modified | HERMES_PYTHON environment variable passing |
| `hermes_cli/main.py` | Modified | stdout UTF-8 reconfiguration + npm subprocess encoding |
| `hermes_cli/plugins.py` | Modified | plugin.yaml reading uses UTF-8 |
| `hermes_cli/banner.py` | Modified | 4 subprocess calls with added encoding="utf-8" |
| `hermes_cli/clipboard.py` | Modified | subprocess encoding fix |
| `hermes_cli/gateway.py` | Modified | subprocess encoding fix |
| `hermes_cli/doctor.py` | Modified | subprocess encoding fix |
| `hermes_cli/setup.py` | Modified | subprocess encoding fix |
| `hermes_cli/claw.py` | Modified | subprocess encoding fix |
| `hermes_cli/profiles.py` | Modified | subprocess encoding fix |
| `hermes_cli/tools_config.py` | Modified | subprocess encoding fix |
| `hermes_cli/dump.py` | Modified | subprocess encoding fix |
| `hermes_cli/commands.py` | Modified | subprocess encoding fix |
| `tui_gateway/entry.py` | Modified | stdin UTF-8 reconfiguration + SIGPIPE/SIGHUP platform guards |
| `tui_gateway/server.py` | Modified | subprocess encoding fix + ephemeral session support |
| `tui_gateway/slash_worker.py` | Modified | stdio full UTF-8 reconfiguration |
| `tui_gateway/transport.py` | Modified | StdioTransport bypasses TextIOWrapper and writes UTF-8 bytes directly |
| `gateway/status.py` | Modified | PID file encoding + PermissionError handling + taskkill encoding |
| `tools/environments/base.py` | **Key change** | `select.select()` → `read1()` Windows pipe reading |
| `tools/environments/local.py` | Modified | MSYS path conversion + dual-path storage |
| `tools/approval.py` | Modified | Added dangerous command interception patterns |
| `tools/platform_compat.py` | Added | Cross-platform helper library |
| `web/src/components/ChatSidebar.tsx` | Modified | Sidebar ephemeral session avoids polluting session list |
| `docs/winodws_support/` | Added | Windows path experience, terminal tips, 04-24 change summary |
| 41 other files | Batch fix | 146 subprocess `text=True` calls missing `encoding=` |

---

## Detailed Code Changes

### 1. tools/environments/base.py — Terminal Output Capture (Key Fix)

#### Problem

After the terminal tool executed a command, output was always empty, `exit_code=0` but `output=""`. Complex commands like `ls -la` timed out after 180 seconds.

#### Root Cause

`select.select([fd], [], [], 0.1)` on Windows can only be used with sockets; for pipe fds it raises `OSError: [WinError 10093]`. The `except OSError: break` in the drain thread catches this and immediately exits the thread, causing all output to be lost.

#### Fix

**File location:** `tools/environments/base.py`

Added platform detection constant:
```python
import platform
_IS_WINDOWS = platform.system() == "Windows"
```

Split the single `_drain()` into platform-specific implementations:

**POSIX version (unchanged):**
```python
def _drain_posix():
    while True:
        readable, _, _ = select.select([fd], [], [], 0.1)
        if not readable:
            if proc.poll() is not None:
                ...
                break
            continue
        chunk = os.read(fd, 4096)
        ...
```

**Windows version (new):**
```python
def _drain_windows():
    buf = proc.stdout.buffer if hasattr(proc.stdout, "buffer") else proc.stdout
    try:
        while True:
            try:
                chunk = buf.read1(4096)
            except (ValueError, OSError):
                break
            if not chunk:
                break
            output_chunks.append(decoder.decode(chunk))
    finally:
        try:
            tail = decoder.decode(b"", final=True)
            if tail:
                output_chunks.append(tail)
        except Exception:
            pass

_drain = _drain_windows if _IS_WINDOWS else _drain_posix
```

**Principle:** `proc.stdout.buffer.read1(4096)` is a blocking read that does not depend on `select`, and works correctly on Windows pipes. When the process exits, the buffer closes triggering `ValueError`, naturally exiting the drain loop.

---

### 2. tui_gateway/entry.py — stdin UTF-8 Reconfiguration

#### Problem

After the TUI chat page refreshed, Chinese messages entered by the user became garbled ("你好" → "浣犲ソ"), while AI replies were fine.

#### Root Cause

`entry.py` applied `reconfigure(encoding="utf-8")` to `_real_stdout` and `sys.stderr`, but missed `sys.stdin`. The Node TUI sends UTF-8 bytes via JSON-RPC → Python stdin decodes with the system default GBK (cp936) → produces garbled text → persisted to SQLite session database.

#### Fix

**File location:** `tui_gateway/entry.py:117`

```python
# Before
for _s in (_real_stdout, sys.stderr):
    ...

# After
for _s in (_real_stdout, sys.stderr, sys.stdin):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
```

#### Supplement: slash_worker.py Synchronized Fix

**File location:** `tui_gateway/slash_worker.py:58-64`

The slash worker is a persistent slash command subprocess that also reads JSON commands via stdin; the same encoding protection is needed:

```python
if sys.platform == "win32":
    for _s in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
```

---

### 3. tui_gateway/transport.py — StdioTransport Bypasses TextIOWrapper

#### Problem

Even after `reconfigure`-ing stdout, libraries like Rich may layer new TextIOWrappers on stdout, still using GBK encoding.

#### Fix

**File location:** `tui_gateway/transport.py:85-91`

```python
def write(self, obj: dict) -> bool:
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    try:
        with self._lock:
            stream = self._stream_getter()
            # Bypass TextIOWrapper encoding (GBK on CJK Windows) by
            # writing UTF-8 bytes directly to the underlying buffer.
            buf = getattr(stream, "buffer", None)
            if buf is not None:
                buf.write(line.encode("utf-8"))
                buf.flush()
            else:
                stream.write(line)
                stream.flush()
        return True
    except BrokenPipeError:
        return False
```

---

### 4. subprocess Encoding Batch Fix (146 locations / 41 files)

#### Problem

Gateway crashes on startup:
```
[gateway-crash] UnicodeDecodeError: 'gbk' codec can't decode byte 0xa1 in position 0: illegal multibyte sequence
```

#### Root Cause

Python `subprocess.run(text=True)` on Chinese Windows defaults to system code page GBK (cp936) for decoding output. When git output contains non-GBK characters (e.g., Unicode symbols ⚕ ✓ → in commit messages), decoding fails.

#### Fix

Added `encoding="utf-8", errors="replace"` to all `subprocess.run/call(..., text=True)` calls:

**Typical fix (hermes_cli/banner.py):**
```python
# Before
subprocess.run(["git", "rev-parse", ...], text=True, capture_output=True)

# After
subprocess.run(["git", "rev-parse", ...], text=True, capture_output=True,
               encoding="utf-8", errors="replace")
```

**Key files affected:**
- `hermes_cli/banner.py` — 4 git commands
- `hermes_cli/main.py` — npm subprocess
- `hermes_cli/gateway.py` — process management
- `hermes_cli/clipboard.py` — clipboard reading
- `hermes_cli/doctor.py` — diagnostic commands
- `tui_gateway/server.py` — 3 locations
- `gateway/status.py` — taskkill calls
- `tools/environments/base.py` — shell execution
- `tools/environments/docker.py` — Docker commands
- `tools/environments/ssh.py` — SSH commands
- And 30+ other files

---

### 5. tools/environments/local.py — Git Bash Compatibility

#### Already Modified in Previous Session (04-24), Synced to New Branch This Time

- WSL bash detection (`_is_wsl_bash()`)
- Git Bash path detection priority adjustment
- MSYS path conversion + dual-path storage
- `get_temp_dir()` returns MSYS format
- `_update_cwd()` / `cleanup()` use Windows paths

See [Code_Changes_Summary_2026-04-24.md](Code_Changes_Summary_2026-04-24.md) for details.

---

### 6. tools/approval.py — Dangerous Command Interception

#### New Patterns

```python
(r'\bfind\s+/(?:\s|$)', "find from filesystem root (hangs on Windows Git Bash)"),
(r'\bfind\s+/home(?:/\s|\s|$)', "find traversal of /home (may hang on Windows Git Bash)"),
(r'\bls\s+(?:-\S+\s+)*-\S*R\S*\s+/\s*$', "recursive ls of filesystem root (hangs)"),
```

Prevents `find /` and similar commands from traversing the entire Windows file system under Git Bash, causing hangs.

---

### 7. hermes_cli/pty_bridge.py — ConPTY Windows Backend

#### New Windows PTY Support

Uses the `pywinpty` library to implement ConPTY (Windows 10+) pseudo-terminal, enabling the dashboard chat tab to embed a full TUI experience.

**Platform detection:**
```python
if sys.platform == "win32":
    try:
        from winpty.ptyprocess import PtyProcess as _WinPtyProcess
        _PTY_BACKEND = "win"
    except ImportError:
        _WinPtyProcess = None
```

**Windows reading:**
```python
def _read_win(self, timeout: float) -> Optional[bytes]:
    proc = self._proc
    try:
        old_timeout = proc.fileobj.gettimeout()
    except Exception:
        old_timeout = None
    try:
        proc.fileobj.settimeout(timeout)
        try:
            text = proc.read(65536)
        except _socket.timeout:
            return b""
        except EOFError:
            return None
        except OSError:
            return None
    finally:
        try:
            proc.fileobj.settimeout(old_timeout)
        except OSError:
            pass
    if not text:
        return b""
    return text.encode("utf-8")
```

---

### 8. tui_gateway/entry.py — Enhanced Signal Handling

#### New Signal Capture

```python
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
signal.signal(signal.SIGTERM, _log_signal)
if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, _log_signal)
signal.signal(signal.SIGINT, signal.SIG_IGN)
```

- **SIGPIPE ignored**: Background threads (TTS, beep, etc.) won't kill the process when writing to closed stdout
- **SIGTERM/SIGHUP logged**: Written to `~/.hermes/logs/tui_gateway_crash.log` for troubleshooting
- **SIGINT ignored**: Prevents Ctrl+C from accidentally killing gateway subprocesses

---

### 9. tui_gateway/server.py + ChatSidebar.tsx — Ephemeral Session Fix

#### Problem

Every time the Dashboard Chat page is opened, the sidebar (`ChatSidebar`) connects to the dashboard's own gateway (`/api/ws`) and calls `session.create`. This RPC writes a database record (`source="tui"`) via `db.create_session()`. When the sidebar unmounts, it only closes the WebSocket without calling `session.close` or cleaning up the database entry. This causes the Sessions page to gain an empty "untitled session" every time the Chat page is visited.

#### Fix

**tui_gateway/server.py — `session.create` (~L1485):**

```python
# New ephemeral parameter
ephemeral = bool(params.get("ephemeral"))

# Store in in-memory session dict
_sessions[sid] = {
    ...
    "ephemeral": ephemeral,
    ...
}

# Skip DB write in _build thread
db = _get_db()
if db is not None and not ephemeral:
    db.create_session(key, source="tui", model=_resolve_model())
```

**tui_gateway/server.py — `session.close` (~L1833):**

```python
# On close, delete DB entry for ephemeral session (safety net)
if session.get("ephemeral"):
    try:
        db = _get_db()
        if db is not None:
            db.delete_session(session["session_key"])
    except Exception:
        pass
```

**web/src/components/ChatSidebar.tsx (~L114-140):**

```typescript
// Pass ephemeral: true on creation, skip DB write
gw.request<{ session_id: string }>("session.create", { ephemeral: true })

// Call session.close on unmount to clean up in-memory session
if (sidecarSid) {
  gw.request("session.close", { session_id: sidecarSid }).catch(() => {});
}
gw.close();
```

---

### 10. gateway/status.py — Enhanced PID File Handling

#### Fix

```python
# PID file read/write uses UTF-8 encoding
with open(self._pid_file, "w", encoding="utf-8") as f:
    f.write(str(os.getpid()))

# taskkill subprocess with encoding parameters
subprocess.run(["taskkill", ...], encoding="utf-8", errors="replace")

# PermissionError handling
except PermissionError:
    pass
```

---

## Summary of Changes

### Problem Background

On Chinese Windows (system code page GBK/cp936), Hermes had three core problems:

1. **Gateway startup crash**: `subprocess.run(text=True)` decodes git output with GBK, crashes on non-GBK characters
2. **Terminal tool output empty**: `select.select()` is unavailable on Windows pipes, drain thread exits immediately
3. **TUI Chinese input garbled**: stdin not reconfigured to UTF-8, Chinese characters entered by user are incorrectly decoded by GBK and persisted

### Solutions

1. **Encoding fix (146 locations)**: Global search for `subprocess.*text=True` without `encoding=`, batch-add `encoding="utf-8", errors="replace"`
2. **Platform-specific drain**: Windows uses `proc.stdout.buffer.read1()` instead of `select.select()`, completely resolving pipe reading
3. **stdin reconfiguration**: stdin/stdout/stderr in `entry.py` and `slash_worker.py` all reconfigured to UTF-8
4. **Transport layer bypass**: `StdioTransport.write()` writes UTF-8 bytes directly to underlying buffer, bypassing TextIOWrapper encoding
5. **ConPTY support**: Uses pywinpty to implement Windows pseudo-terminal backend
6. **Ephemeral session**: Sidebar `session.create` passes `ephemeral: true` to skip DB write, unmount calls `session.close` to clean up, avoiding empty sessions in Sessions page

### Commit History

| Commit | Description |
|--------|-------------|
| `49a73677` | fix(windows): resolve encoding crashes and add ConPTY support |
| `a6f3ac4e` | fix(windows): improve Git Bash compatibility and path handling |
| `62ae82a8` | refactor(subprocess): standardize encoding and error handling for subprocess calls |
| `a7100fe1` | fix(windows): force utf-8 encoding for stdio streams |
| `f73c6dcd` | feat(tui): implement ephemeral sessions for web chat sidebar |

### Verification Results

- ✅ Gateway starts normally on Chinese Windows (no more GBK crashes)
- ✅ Terminal tool `ls -la` returns output normally (no longer empty or timed out)
- ✅ TUI chat Chinese input/display is correct (no more "浣犲ソ" garbled text)
- ✅ Chinese text in historical messages after page refresh is correct (no more GBK→UTF-8 decode misalignment)
- ✅ Dashboard chat tab can embed TUI via ConPTY
- ✅ WSL bash is correctly filtered, Git Bash paths convert correctly
- ✅ Dangerous commands (`find /`) are correctly intercepted
- ✅ Chat page no longer creates empty "untitled sessions" (ephemeral session skips DB write + unmount cleanup)

---

> Change statistics based on changes after commit 093bf90b, covering 5 commits:
> - 49a73677: fix(windows): resolve encoding crashes and add ConPTY support
> - a6f3ac4e: fix(windows): improve Git Bash compatibility and path handling
> - 62ae82a8: refactor(subprocess): standardize encoding and error handling for subprocess calls
> - a7100fe1: fix(windows): force utf-8 encoding for stdio streams
> - f73c6dcd: feat(tui): implement ephemeral sessions for web chat sidebar
