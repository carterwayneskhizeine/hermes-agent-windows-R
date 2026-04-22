# Clean up a previous Hermes Agent (Windows) installation.
# Removes %LOCALAPPDATA%\hermes, HERMES_* environment variables, and PATH entries.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\clear.ps1

$ErrorActionPreference = "Continue"
$hermesRoot = Join-Path $env:LOCALAPPDATA "hermes"
$hermesAgentDir = Join-Path $hermesRoot "hermes-agent"
$hermesAgentScripts = Join-Path $hermesAgentDir "venv\Scripts"

# 1. Stop Hermes-related processes
Get-Process | Where-Object {
    ($_.Path -like "$hermesRoot*") -or
    ($_.Path -like "$hermesAgentScripts\hermes.exe")
} | Stop-Process -Force -ErrorAction SilentlyContinue

# 2. Remove the install directory and runtime data
Remove-Item -LiteralPath $hermesRoot -Recurse -Force -ErrorAction SilentlyContinue

# 3. Clear user environment variables
[Environment]::SetEnvironmentVariable("HERMES_HOME", $null, "User")
[Environment]::SetEnvironmentVariable("HERMES_GIT_BASH_PATH", $null, "User")
Remove-Item Env:HERMES_HOME -ErrorAction SilentlyContinue
Remove-Item Env:HERMES_GIT_BASH_PATH -ErrorAction SilentlyContinue

# 4. Remove old Hermes paths from user PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath) {
    $newPath = ($userPath -split ';' | Where-Object {
        $_ -and $_.Trim() -ne $hermesAgentDir -and $_.Trim() -ne $hermesAgentScripts
    }) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}

# Verification
Write-Host "Install dir exists:" (Test-Path $hermesRoot)
Write-Host "User HERMES_HOME:" ([Environment]::GetEnvironmentVariable("HERMES_HOME", "User"))
Write-Host "User HERMES_GIT_BASH_PATH:" ([Environment]::GetEnvironmentVariable("HERMES_GIT_BASH_PATH", "User"))
Write-Host "User PATH cleaned."
Write-Host "Close this PowerShell window and open a new one to pick up the changes."
