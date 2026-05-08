<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

<p align="center">
  <img src="docs/Chat.jpg" alt="Hermes Chat UI" width="100%">
</p>

# Hermes Agent — Windows Development Fork

This is a Windows-native development fork of Hermes Agent, focused on fixing encoding, Git Bash path handling, TUI, Dashboard Chat, and multi-profile runtime experience on Windows.

Original upstream README: [README_hermes.md](README_hermes.md). Chinese version of this README: [中文版](README_R_CN.md). Original fork repository: https://github.com/carterwayneskhizeine/hermes-agent

## Quick Start

```powershell
git clone https://github.com/carterwayneskhizeine/hermes-agent-windows-R.git
cd hermes-agent-windows-R
uv venv venv --python 3.12
.\venv\Scripts\Activate.ps1
uv pip install -e ".[all,dev]"
hermes model
hermes gateway run
```

For full installation instructions, Windows-specific notes, and multi-instance configuration, see the documentation links below.

## Documentation

| Topic | Description |
|-------|-------------|
| [Windows Docs Overview](docs/windows_EN/README.md) | Entry point for Windows installation, running, and troubleshooting |
| [Windows Quick Start](docs/windows_EN/quickstart.md) | Requirements, installation steps, initial config, Git Bash paths, common commands |
| [psmux One-click Launch](docs/windows_EN/psmux-startup.md) | Install `psmux`, use `start-hermes.ps1`, AI script modification prompts |
| [Profiles & Multi-instance](docs/windows_EN/profiles-and-multi-instance.md) | Create profiles, `-p` flag, `HERMES_HOME`, run multiple Gateways/Dashboards in parallel |
| [Profile Config Examples](docs/windows_EN/profile-config.md) | Sanitized config examples: default / belbin / goldie / mem / turing |
| [Dashboard Web UI](docs/windows_EN/dashboard.md) | Launch Dashboard, frontend build, TUI Chat, multi-profile ports |
| [Windows-specific Notes](docs/windows_EN/windows-notes.md) | Git Bash path conversion, CWD, dangerous command interception, process management, adaptation summary |
| [Windows Troubleshooting](docs/windows_EN/troubleshooting.md) | Common install, port, Web UI, Gateway lock, and path issues |
| [Windows Adaptation Log](docs/winodws_support_EN/) | Full porting records and historical change notes (English) |

## Common Commands

```powershell
hermes                  # Start interactive CLI
hermes gateway run      # Start message gateway
hermes model            # Switch LLM model
hermes tools            # Manage tool toggles
hermes doctor           # Diagnose environment issues
```

Build Dashboard frontend (first time):

```powershell
cd web
npm install
npm run build
cd ..
```

Start Dashboard:

```powershell
python -m hermes_cli.main dashboard --no-open --tui
```

Open in browser:

```text
http://127.0.0.1:9119
```

psmux one-click launch:

```powershell
winget install psmux
.\start-hermes.ps1
```
