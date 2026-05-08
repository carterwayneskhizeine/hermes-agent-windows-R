# Windows Quick Start

This document is for users running the Hermes Agent development fork on native Windows (no WSL required). All commands are run in PowerShell 7+ by default.

## Requirements

Make sure the following tools are installed and added to `PATH`:

| Tool | Purpose | How to Install |
|------|---------|----------------|
| Python 3.12 | Hermes runtime | [python.org](https://www.python.org/downloads/) |
| Git for Windows | Provides `bash.exe`, Hermes local shell backend | [git-scm.com](https://git-scm.com/download/win) |
| uv | Virtual environment and package manager | `irm https://astral.sh/uv/install.ps1 \| iex` |
| ripgrep (`rg.exe`) | Fast file search, optional but recommended | `winget install BurntSushi.ripgrep.MSVC` |
| psmux | Multi-session manager for one-click launch script, optional | `winget install psmux` |

## Installation

```powershell
git clone https://github.com/carterwayneskhizeine/hermes-agent-windows-R.git
cd hermes-agent-windows-R
uv venv venv --python 3.12
.\venv\Scripts\Activate.ps1
uv pip install -e ".[all,dev]"
```

If PowerShell blocks the activation script:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Initial Configuration

Configure the model:

```powershell
hermes model
```

Configure messaging platforms (Telegram, Discord, Slack, WhatsApp, Signal, etc.):

```powershell
hermes gateway setup
```

Start the Gateway:

```powershell
hermes gateway run
```

Start the interactive CLI:

```powershell
hermes
```

## Git Bash Path

Hermes requires `bash.exe` from Git for Windows on Windows. Auto-detection order:

1. Environment variable `HERMES_GIT_BASH_PATH`
2. `%ProgramFiles%\Git\bin\bash.exe`
3. `%ProgramFiles(x86)%\Git\bin\bash.exe`
4. `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`
5. `shutil.which("bash")`, but skips `C:\Windows\System32\bash.exe`

If auto-detection fails, set the path manually:

```powershell
$env:HERMES_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"
```

Do not use WSL bash. WSL's `/mnt/d/...` paths are incompatible with Git Bash's `/d/...` paths and may cause tools to write files into the WSL filesystem.

## Common Commands

```powershell
hermes                  # Start interactive CLI
hermes gateway run      # Start message gateway
hermes gateway stop     # Stop gateway
hermes model            # Switch LLM model
hermes tools            # Manage tool toggles
hermes config set       # Edit a single config value
hermes doctor           # Diagnose environment issues
```

## Running Tests

```powershell
.\venv\Scripts\python.exe -m pytest tests/tools/test_windows_compat.py -v

.\venv\Scripts\python.exe -m pytest tests/tools/test_windows_compat.py `
    tests/gateway/test_status.py tests/hermes_cli/test_profiles.py -v
```
