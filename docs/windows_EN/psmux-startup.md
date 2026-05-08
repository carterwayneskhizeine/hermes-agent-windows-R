# psmux One-click Launch

The `start-hermes.ps1` script in the repository root is a Windows PowerShell example script based on [psmux](https://github.com/psmux/psmux). It launches multiple Hermes Gateway / Dashboard sessions with a single command.

This script is a local customization tool. Before using it you need to edit it for your machine:

- Absolute path to the repository
- Virtual environment path (`venv` or `.venv`)
- Profile names
- Dashboard ports
- `HERMES_HOME` for each profile

## Install psmux

```powershell
winget install psmux
```

## Run the Script

```powershell
.\start-hermes.ps1
```

Common management commands:

```powershell
psmux list-sessions
psmux attach -t default-gw
psmux kill-session -t default-gw
```

## AI Prompt to Customize start-hermes.ps1

Hand the following prompt to an AI and fill in your own machine details:

```text
Please modify only start-hermes.ps1 in the root of this repository.
Turn it into a one-click launch script for my Windows PowerShell environment.

Goals:
- Use psmux to manage multiple independent sessions.
- Kill any existing psmux sessions with the same names before starting.
- For each Hermes profile, launch a set of services: Gateway and Dashboard Web UI.
- Start Dashboard with `python -m hermes_cli.main dashboard --no-open --tui`,
  assigning a different port to each profile to avoid conflicts.
- For Gateway, prefer `hermes -p <profile> gateway run`; use `hermes gateway run`
  for the default profile.
- If the dashboard subcommand does not support `-p` directly, set `$env:HERMES_HOME`
  to the profile's Hermes home in that session.
- Use `.\venv\Scripts\Activate.ps1` for the virtual environment; change to
  `.\.venv\Scripts\Activate.ps1` if the repo uses `.venv`.
- Replace `$projectDir` with the absolute path of this repository.
- At the end, attach to the default gateway session, or print the available
  `psmux attach -t <session>` commands.

My environment:
- Repository path: <fill in absolute path, e.g. D:\Code\hermes-agent-windows-R>
- Default Hermes home: <fill in, e.g. C:\Users\<username>\.hermes>
- Profiles to launch: <fill in list, e.g. default,turing,belbin,mem,goldie>
- Dashboard ports: <fill in mapping, e.g. default=9119,turing=9120,belbin=9121,mem=9122,goldie=9123>

Constraints:
- Do not modify any Hermes core code.
- Do not remove existing comments unless they conflict with the new logic.
- After the changes, describe each session's name, start command, and access URL.
```
