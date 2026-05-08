# Hermes Windows Adaptation Code Changes Summary

> Updated: 2026-04-30
> Baseline: Branch hermes/2026-04-29 (commit 23ae0dfb)
> Scope: Sync upstream v2026.4.30 (262 commits), resolve 4 merge conflicts, retain all Windows optimizations

---

## Operation Overview

Created `hermes/2026-04-30` from `hermes/2026-04-29`, merged upstream tag `v2026.4.30` (Hermes Agent v0.12.0, The Curator release), bringing in 262 new commits, resolved 4 conflicts, all Windows adaptation patches fully retained.

---

## Merge Statistics

| Item | Count |
|------|-------|
| Upstream commits merged | 262 |
| Files auto-merged successfully | All except 4 |
| Files with manually resolved conflicts | 4 |
| Windows optimizations lost | 0 |

---

## Conflict Resolution Details

### 1. tools/environments/local.py (2 conflicts)

#### Conflict 1: `__init__` Method

**Conflict cause:**
Upstream added `os.path.expanduser(cwd)` to expand user directories (`~` path support); our 04-24 changes applied MSYS path conversion + dual-path storage for Windows.

**Resolution:**
Both retained — Windows branch uses our MSYS conversion, non-Windows branch uses upstream's `expanduser`:

```python
def __init__(self, cwd: str = "", timeout: int = 60, env: dict = None):
    if _IS_WINDOWS:
        from tools.platform_compat import windows_path_to_msys
        init_cwd = windows_path_to_msys(cwd) if cwd else windows_path_to_msys(os.getcwd())
    else:
        init_cwd = os.path.expanduser(cwd) if cwd else os.getcwd()

    super().__init__(cwd=init_cwd, timeout=timeout, env=env)

    if _IS_WINDOWS:
        from tools.platform_compat import msys_path_to_windows
        self._snapshot_path_win = msys_path_to_windows(self._snapshot_path)
        self._cwd_file_win = msys_path_to_windows(self._cwd_file)
    else:
        self._snapshot_path_win = self._snapshot_path
        self._cwd_file_win = self._cwd_file

    self.init_session()
```

#### Conflict 2: `_update_cwd` Method

**Conflict cause:**
Upstream changed `open(...)` to `with open(...) as f:` context manager (code quality improvement); our version uses `_cwd_file_win` (Windows path).

**Resolution:**
Adopted upstream's context manager form while retaining `_cwd_file_win`:

```python
with open(self._cwd_file_win) as f:
    cwd_path = f.read().strip()
```

---

### 2. hermes_cli/gateway.py

**Conflict cause:**
We added `encoding="utf-8", errors="replace"` in 04-26; upstream also added `encoding="utf-8"` but changed `errors` to `"ignore"`.

**Resolution:**
Upstream already has the same UTF-8 encoding fix; adopted upstream version (`errors="ignore"`):

```python
result = subprocess.run(
    ["wmic", "process", "get", ...],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="ignore",
    timeout=10,
)
```

---

### 3. hermes_cli/main.py

**Conflict cause:**
Upstream extracted the large inline `argparse.ArgumentParser(...)` definition from the `main()` function into a standalone module `hermes_cli/_parser.py` (`build_top_level_parser()`); our 04-26 changes added a Windows stdout/stderr UTF-8 reconfiguration block at the beginning of `main()`. Both changes overlapped at the `main()` function entry point.

**Resolution:**
Retained our Windows UTF-8 reconfiguration block, adopted upstream's `build_top_level_parser()` refactoring (discarding the large inline epilog):

```python
def main():
    # Reconfigure stdout/stderr to UTF-8 on Windows so that Unicode symbols
    # (✓, ✗, →, etc.) don't crash on CJK codepages (GBK / cp949 / …).
    if sys.platform == "win32":
        for _stream in (sys.stdout, sys.stderr):
            if hasattr(_stream, "reconfigure"):
                try:
                    _stream.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass

    from hermes_cli._parser import build_top_level_parser

    parser, subparsers, chat_parser = build_top_level_parser()
```

---

### 4. tui_gateway/server.py

**Conflict cause:**
Upstream extracted the inline `_build()` thread function from `session.create` into a top-level function `_start_agent_build(sid, session)`, changing the trigger method to `threading.Timer(0.05, _deferred_build)`. Our 04-26 `_build` inline function added an `ephemeral` check (`if db is not None and not ephemeral:`).

The upstream-extracted `_start_agent_build` function (line 473) was missing the `ephemeral` check.

**Resolution:**

1. Adopted upstream's Timer trigger approach (discarding our duplicate inline `_build` code):
```python
build_timer = threading.Timer(0.05, _deferred_build)
build_timer.daemon = True
build_timer.start()
```

2. Added `ephemeral` check inside `_start_agent_build`'s `_build()`:
```python
db = _get_db()
if db is not None and not current.get("ephemeral"):
    db.create_session(key, source="tui", model=_resolve_model())
```

This ensures ephemeral sessions created by the web sidebar still don't write to the database.

---

## Upstream Important Changes (v0.12.0 The Curator Release)

| Direction | Description |
|-----------|-------------|
| Curator autonomous maintenance | Added `agent/curator.py`, Hermes can run background Curator loops autonomously |
| New inference providers | Expanded to 20+ inference backends |
| Microsoft Teams | Teams support via pluggable gateway platform |
| Spotify / Google Meet | New integrations |
| ComfyUI / TouchDesigner-MCP | Bundled by default |
| TUI cold start performance | ~57% cold start time reduction |
| `_start_agent_build` refactoring | Agent build logic for session.create extracted to standalone function, Timer-deferred |
| `build_top_level_parser` refactoring | CLI argument parser extracted to `hermes_cli/_parser.py` |

---

## Windows Optimization Retention Confirmation

| Windows Patch | File | Status |
|---------------|------|--------|
| WSL bash detection (`_is_wsl_bash`) | `tools/environments/local.py` | ✅ Auto-merged, retained |
| Git Bash path detection priority | `tools/environments/local.py` | ✅ Auto-merged, retained |
| MSYS path conversion + dual-path storage | `tools/environments/local.py` | ✅ Manually resolved conflict, retained (merged with expanduser) |
| Windows pipe reading (`_drain_windows`) | `tools/environments/base.py` | ✅ Auto-merged, retained |
| Cross-platform helper library | `tools/platform_compat.py` | ✅ Auto-merged, retained |
| Dangerous command interception (`find /` etc.) | `tools/approval.py` | ✅ Auto-merged, retained |
| stdin/stdout/stderr UTF-8 reconfiguration | `tui_gateway/entry.py` | ✅ Auto-merged, retained |
| StdioTransport bypasses TextIOWrapper | `tui_gateway/transport.py` | ✅ Auto-merged, retained |
| slash_worker full UTF-8 reconfiguration | `tui_gateway/slash_worker.py` | ✅ Auto-merged, retained |
| ephemeral session support | `tui_gateway/server.py` | ✅ Manually resolved conflict, retained (moved into `_start_agent_build`) |
| PID file encoding + taskkill encoding | `gateway/status.py` | ✅ Auto-merged, retained |
| ConPTY Windows backend | `hermes_cli/pty_bridge.py` | ✅ Auto-merged, retained |
| HERMES_PYTHON environment variable passing | `hermes_cli/web_server.py` | ✅ Auto-merged, retained |
| npm subprocess UTF-8 encoding | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| main() UTF-8 reconfiguration | `hermes_cli/main.py` | ✅ Manually resolved conflict, retained (before build_top_level_parser refactoring) |
| 146 subprocess encoding fixes | 41 files | ✅ Auto-merged, retained |

---

## Commit History

| Commit | Description |
|--------|-------------|
| `a164f2b85` | Merge v2026.4.30 into hermes/2026-04-30, preserve Windows compat patches |

---

## Operation Summary

The 04-30 work was a pure sync operation with no new Windows adaptation code (except correcting the upstream-missed `ephemeral` check). The core work was:

1. **Losslessly merged 262 upstream commits**: Feature updates include Curator autonomous maintenance loop, multiple new inference providers, TUI cold start 57% speedup, Teams/Spotify/Google Meet integrations, etc.
2. **Resolved 4 conflicts**: `local.py` merged expanduser + MSYS conversion; `gateway.py` adopted upstream's `errors="ignore"`; `main.py` retained UTF-8 reconfiguration and adopted parser refactoring; `server.py` adopted Timer trigger and added ephemeral check to `_start_agent_build`
3. **All Windows optimizations fully retained**: All 16 Windows patches (including all 04-24, 04-26, 04-27, 04-29 changes) lost none

---

> Merge baseline: hermes/2026-04-29 (23ae0dfb) merged upstream tag v2026.4.30 (73bf3ab1b)
> Merge commit: a164f2b85
