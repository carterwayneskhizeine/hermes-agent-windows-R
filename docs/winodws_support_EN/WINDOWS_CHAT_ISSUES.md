# Windows Dashboard Chat Feature Fix Log

> Environment: Windows 11 Pro, Python 3.12 (native win32), system locale encoding cp936 (GBK)
>
> Date: 2026-04-26

## Background

The `/chat` page of `hermes dashboard --tui` was completely unusable on Windows. The original code only supported POSIX (via WSL), with multiple issues including PTY unavailability, GBK encoding crashes, and missing signals.

## Fix Overview

A total of **8 files** were modified, covering 4 categories: PTY backend replacement, encoding fixes, signal compatibility, and Python path resolution.

---

## 1. PTY Backend: pywinpty Replaces ptyprocess (Core Change)

**File:** `hermes_cli/pty_bridge.py`

**Problem:** The original code raised `PtyUnavailableError` when `sys.platform == "win32"`, making it impossible to create a pseudo-terminal on Windows.

**Fix:** Introduced `pywinpty` (Python bindings for Windows ConPTY), selecting the backend at import time via the `_PTY_BACKEND` flag:

```
win32  → pywinpty (ConPTY)
posix  → ptyprocess (openpty)
```

The `PtyBridge` class keeps its public API unchanged, branching internally by platform:

| Method | POSIX (ptyprocess) | Windows (pywinpty) |
|--------|-------------------|-------------------|
| `spawn()` | `ptyprocess.PtyProcess.spawn()` | `winpty.ptyprocess.PtyProcess.spawn()` |
| `read()` | `select.select()` + `os.read()` | `socket.settimeout()` + `proc.read()`, str→bytes |
| `write()` | `os.write()` loop handling short writes | `proc.write(str)`, bytes→str |
| `resize()` | `fcntl.ioctl(TIOCSWINSZ)` | `proc.setwinsize(rows, cols)` |
| `close()` | SIGHUP → SIGTERM → SIGKILL escalation | `proc.terminate(force=True)` |

pywinpty's `read()` returns str, converted back to bytes via `.encode("utf-8")` to match web_server's `ws.send_bytes()` contract. Read timeout is implemented through the internal socket's `settimeout()`.

---

## 2. GBK Encoding Fix (6 locations)

On Chinese Windows systems, `locale.getpreferredencoding()` returns `cp936` (GBK). Python defaults to GBK in the following scenarios, crashing when encountering UTF-8 content.

### 2a. gateway Subprocess stdin/stdout

**File:** `tui_gateway/server.py` — `_SlashWorker.__init__`

```python
# Before fix
subprocess.Popen(argv, text=True, ...)

# After fix
subprocess.Popen(argv, text=True, encoding="utf-8", errors="replace", ...)
```

### 2b. npm install / npm run build Subprocesses

**File:** `hermes_cli/main.py` — `_make_tui_argv()`

Both `subprocess.run(text=True)` calls had `encoding="utf-8", errors="replace"` added.

### 2c. plugin.yaml Parsing

**File:** `hermes_cli/plugins.py` — `_parse_manifest()`

```python
manifest_file.read_text()  →  manifest_file.read_text(encoding="utf-8")
```

Error message: `Failed to parse plugins/disk-cleanup/plugin.yaml: 'gbk' codec can't decode byte 0x94`

### 2d. PID File Reading

**File:** `gateway/status.py` — `_read_pid_record()`

```python
pid_path.read_text()  →  pid_path.read_text(encoding="utf-8")
```

Also wrapped with `try/except PermissionError` to fix permission errors caused by Windows file locks.

### 2e. print() Output to Terminal

**File:** `hermes_cli/main.py` — `main()` entry point

```python
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding="utf-8", errors="replace")
```

Fixes `UnicodeEncodeError` for `print("  ✓ Web UI built")` where `✓` (U+2713) would crash on GBK terminals.

### 2f. gateway JSON-RPC Output (Deepest Layer)

**File:** `tui_gateway/transport.py` — `StdioTransport.write()`

```python
# Before fix
stream.write(line)          # TextIOWrapper encodes with GBK, crashes on ⚕ (U+2695)

# After fix
buf = stream.buffer         # Write directly to underlying buffer
buf.write(line.encode("utf-8"))
```

`reconfigure()` does not take effect in pipe environments (`server.py` redirects `sys.stdout` to `sys.stderr` at import time), so writing bytes directly to `stream.buffer` is used instead.

**File:** `tui_gateway/entry.py` — `main()`

Applies `reconfigure(encoding="utf-8")` to `_real_stdout` (the reference saved by `server.py` before stdout redirection) as an additional safeguard.

---

## 3. Missing POSIX Signals

**File:** `tui_gateway/entry.py`

**Problem:** `signal.SIGPIPE` and `signal.SIGHUP` do not exist on Windows, causing `AttributeError` and crashing the gateway at startup.

```python
# Before fix
signal.signal(signal.SIGPIPE, signal.SIG_IGN)   # AttributeError on Windows
signal.signal(signal.SIGHUP, _log_signal)        # AttributeError on Windows

# After fix
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
signal.signal(signal.SIGTERM, _log_signal)       # SIGTERM exists on Windows
if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, _log_signal)
```

---

## 4. Python Path Resolution

**File:** `hermes_cli/web_server.py` — `_resolve_chat_argv()`

**Problem:** The TUI Node process launches `python -m tui_gateway.entry` via `child_process.spawn`, resolving the Python path using the `VIRTUAL_ENV` environment variable. When `VIRTUAL_ENV` points to a conda base environment instead of the project venv, the Python found by Node doesn't have the `tui_gateway` module, causing gateway startup failure.

```python
# Fix: always build env dict and specify HERMES_PYTHON
env = os.environ.copy()
env["HERMES_PYTHON"] = sys.executable  # Node's resolvePython() uses this variable with priority
```

---

## Modified File Index

| File | Modification Type | Description |
|------|-------------------|-------------|
| `hermes_cli/pty_bridge.py` | Core change | Added pywinpty (ConPTY) Windows backend |
| `hermes_cli/web_server.py` | Feature fix | Set `HERMES_PYTHON` to ensure subprocess finds the correct Python |
| `hermes_cli/main.py` | Encoding fix | stdout UTF-8 reconfigure + npm subprocess encoding |
| `hermes_cli/plugins.py` | Encoding fix | plugin.yaml `read_text(encoding="utf-8")` |
| `tui_gateway/entry.py` | Compatibility fix | SIGPIPE/SIGHUP platform guards + stdout reconfigure |
| `tui_gateway/server.py` | Encoding fix | subprocess `encoding="utf-8"` |
| `tui_gateway/transport.py` | Encoding fix | StdioTransport writes UTF-8 bytes directly through buffer |
| `gateway/status.py` | Encoding fix + resilience | PID file encoding + PermissionError handling |

## Verification

```bash
# Install dependencies
pip install pywinpty

# Start dashboard
python -m hermes_cli.main dashboard --tui --no-open

# Visit http://127.0.0.1:9119/chat — chat interface works normally
```
