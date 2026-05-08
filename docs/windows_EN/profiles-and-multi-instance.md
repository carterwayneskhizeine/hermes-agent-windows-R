# Profiles & Multi-instance

Hermes supports profile isolation. Each profile has its own configuration, memory, sessions, and skills, stored at:

```text
~/.hermes/profiles/<name>/
```

The default profile uses:

```text
~/.hermes/
```

## Creating and Using Profiles

```powershell
hermes profile create turing --clone
hermes profile list
hermes profile info turing
```

In Windows PowerShell, use `-p` or `--profile`:

```powershell
hermes -p turing setup
hermes -p turing chat
hermes -p turing gateway run

hermes --profile=turing setup
```

You can also switch the default profile:

```powershell
hermes profile use turing
hermes setup
hermes chat
hermes profile use default
```

## Using Profiles with Dashboard

The `dashboard` subcommand selects a profile via `HERMES_HOME`:

```powershell
$env:HERMES_HOME = "C:\Users\<username>\.hermes\profiles\turing"
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

`$env:HERMES_HOME` is only effective in the current PowerShell window and resets when the window is closed.

## Running Multiple Agents Simultaneously

Each agent instance needs its own API Server port. If using Telegram, each instance also needs a separate Bot Token; otherwise you will get port conflicts or Telegram polling conflicts.

The API Server port must be set in `extra.port` under the platform config, not directly in `api_server.port`:

```yaml
gateway:
  platforms:
    api_server:
      enabled: true
      extra:
        port: 8643
```

Example startup:

```powershell
# default Gateway
hermes gateway run

# default Dashboard
python -m hermes_cli.main dashboard --no-open --tui

# turing Gateway
hermes -p turing gateway run

# turing Dashboard
$env:HERMES_HOME = "C:\Users\<username>\.hermes\profiles\turing"
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

To launch multiple profiles with a single command, use `start-hermes.ps1` in the repository root. See [psmux One-click Launch](psmux-startup.md).

## Management Commands

```powershell
hermes profile list
hermes profile info turing
hermes profile rename turing ada
hermes profile delete turing
hermes -p turing model
hermes -p turing doctor
```
