# Windows Troubleshooting

## `hermes` command not found

Make sure the virtual environment is activated, or use the full path:

```powershell
.\venv\Scripts\Activate.ps1
.\venv\Scripts\hermes.exe gateway run
```

## Git Bash not found

Install Git for Windows, or set the path manually:

```powershell
$env:HERMES_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"
```

## `write_file` reports success but no file is created

Usually caused by WSL bash taking precedence over Git Bash. Ask the AI to run the terminal command `pwd`:

- Returns `/d/Code/...`: Git Bash — correct.
- Returns `/mnt/d/Code/...`: WSL bash — incorrect.

Fix: install Git for Windows, or set `HERMES_GIT_BASH_PATH` to point to Git Bash, then restart Hermes.

## `uv pip install` fails

Check versions first:

```powershell
python --version
uv --version
```

Python must be 3.12.x.

## `hermes doctor` reports ripgrep missing

```powershell
winget install BurntSushi.ripgrep.MSVC
```

## API Server port conflict

Find the process using the port:

```powershell
netstat -ano | findstr :8642
```

Kill the process:

```powershell
taskkill /PID <pid> /T /F
```

When running multiple profiles simultaneously, configure a different `gateway.platforms.api_server.extra.port` for each profile.

## Dashboard port in use

The default port is `9119`. Use a different port:

```powershell
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

## `HERMES_HOME` set incorrectly

Clear it in the current PowerShell window:

```powershell
$env:HERMES_HOME = $null
```

Or close and reopen the PowerShell window. To remove a system-wide environment variable, go to System Properties → Environment Variables.

## Web UI shows `Frontend not built`

Rebuild the frontend:

```powershell
cd web
npm install
npm run build
cd ..
```

## `Gateway runtime lock is already held by another instance`

Usually means a Gateway is still running, or a previous abnormal exit left a runtime lock behind.

Check for existing processes first:

```powershell
Get-Process | Where-Object { $_.ProcessName -match "python|hermes" }
```

If you confirm no Gateway is running, delete the runtime lock under the corresponding profile directory. Do not delete the lock while another Gateway is actively running.

## `❌ Gateway already running` when starting multiple profiles with `start-hermes.ps1`

**Symptom:** The second (or later) Gateway reports "Gateway already running (PID XXXXX)" even though `stop-hermes.ps1` has been run and `Get-Process` shows no Hermes processes.

**Root cause:** The global `active_profile` file has been changed from `"default"` to a named profile (e.g. `"turing"`). This happens when you run `hermes profile use <name>` from the interactive CLI.

When `start-hermes.ps1` starts the `default-gw` session with `HERMES_HOME` pointing to the global root and no explicit `-p` flag, the CLI reads `active_profile` and silently overrides `HERMES_HOME` to the named profile's directory. The `default-gw` and `<profile>-gw` sessions then both try to start under the same profile — triggering the conflict.

**Diagnosis:** Check which profile is currently sticky-active:

```powershell
Get-Content "$env:APPDATA\..\Local\hermes\active_profile"
# or wherever your HERMES_HOME root is
hermes profile list   # the ◆ marker shows the active profile
```

**Fix — Reset active profile to default**

```powershell
hermes profile use default
```
