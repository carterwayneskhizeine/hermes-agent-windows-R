# Windows Support

Hermes Agent runs natively on Windows (no WSL required) for the core CLI
workflow. This document describes how Windows-specific behaviour is wired
into the codebase, and what you should know when running or developing
on Windows.

## Runtime model

- Hermes starts from PowerShell or CMD.
- Local shell execution is routed through **Git Bash** (`bash.exe` from
  Git for Windows) so the Unix-oriented command model used elsewhere in
  the codebase keeps working.
- Python/pip/venv are plain native-Windows binaries — no mingw or WSL
  glue involved.

## Requirements

| Dependency | Why | Where |
|------------|-----|-------|
| Python 3.12 | Runtime | python.org / Anaconda |
| Git for Windows | Provides `bash.exe` used as local shell | git-scm.com |
| `uv` | Env + package manager | astral.sh/uv |
| `ripgrep` (`rg.exe`) | Fast search | winget install BurntSushi.ripgrep.MSVC |
| Node.js | Optional, used by some skills | nodejs.org |
| `ffmpeg` | Optional, used by voice/media skills | ffmpeg.org |

## Git Bash detection

On Windows, `tools/environments/local.py::_find_bash` resolves the shell
in this order:

1. `HERMES_GIT_BASH_PATH` environment variable
2. `shutil.which("bash")`
3. Well-known install locations:
   - `%ProgramFiles%\Git\bin\bash.exe`
   - `%ProgramFiles(x86)%\Git\bin\bash.exe`
   - `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`

If none are found, Hermes raises a clear error pointing at
<https://git-scm.com/download/win>.

To override manually:

```powershell
$env:HERMES_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"
```

## Cross-platform helpers

Windows-specific quirks (signal handling, process group semantics,
detached-subprocess flags, file locks) live in
`tools/platform_compat.py`. Modules that previously rolled their own
guards should import from there:

```python
from tools.platform_compat import (
    pid_alive,              # safe replacement for os.kill(pid, 0)
    terminate_pid,          # SIGTERM / taskkill /T /F
    get_detached_popen_kwargs,
    shell_join,
    file_lock,
)
```

`gateway/status.py::_pid_alive` and `terminate_pid` delegate to these
helpers so there is a single source of truth.

## Running from source (venv)

```powershell
uv venv venv --python 3.12
.\venv\Scripts\Activate.ps1
uv pip install -e ".[all]"
hermes gateway run
```

Windows-compat tests:

```powershell
.\venv\Scripts\python.exe -m pytest tests/tools/test_windows_compat.py -v
```

## Known limitations on Windows

These may work but are not tested as thoroughly as on Linux/macOS:

- Gateway/platform integrations (Discord voice, WhatsApp bridge)
- Browser-heavy workflows that rely on `camofox`
- Advanced terminal backends: Docker, SSH, Modal, Daytona, Singularity
- RL / `tinker-atropos` flows

## Cleanup

`clear.ps1` removes a previous install:

- Stops Hermes processes
- Removes `%LOCALAPPDATA%\hermes`
- Clears `HERMES_HOME` / `HERMES_GIT_BASH_PATH` user env vars
- Strips old Hermes paths from the user PATH

```powershell
powershell -ExecutionPolicy Bypass -File .\clear.ps1
```
