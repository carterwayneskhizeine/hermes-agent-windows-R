# Windows-specific Notes

## File Write Paths

Hermes file tools execute through Git Bash. Windows paths are converted to MSYS paths:

```text
D:\Doc\foo\bar.md  ->  /d/Doc/foo/bar.md
```

The conversion logic lives in `windows_path_to_msys()` in `tools/platform_compat.py`.

Do not let Hermes use WSL bash. WSL's `/mnt/d/...` paths are incompatible with Git Bash's `/d/...` paths and may cause files to be written into the WSL filesystem.

## Session CWD and Temporary Files

`LocalEnvironment` on Windows handles additional concerns:

- The initial CWD is converted to `/d/Code/...` form so that bash `cd` works reliably.
- Session snapshots and CWD temp files are stored in `%LOCALAPPDATA%\Temp\hermes\`.
- Both Windows paths and MSYS paths are saved so Python (`open()` / `os.unlink()`) and bash can both access them.

## Dangerous Command Interception

Certain commands under Git Bash traverse the entire Windows root directory or hang. Hermes intercepts:

- `find /`
- `find /home`
- `ls -R /`

Use specific paths instead:

```powershell
find /d/Doc -name '*.md'
```

## Process Management

Windows does not support `os.kill(pid, 0)` or `signal.SIGKILL`. Hermes uses these alternatives:

- Process liveness check: `psutil.pid_exists()` or `tasklist`
- Force kill: `taskkill /PID <pid> /T /F`

## Known Limitations

The following features have not been thoroughly tested on Windows:

- Discord voice channels
- WhatsApp bridge
- Docker / SSH / Modal / Daytona terminal backends
- RL training (`tinker-atropos`)

## Windows Adaptation Summary

The core changes recorded in `docs/winodws_support_EN/Code_Changes_Summary_*.md` fall into these categories:

1. **Git Bash & Path Compatibility**
   - Prefer Git for Windows `bash.exe`, falling back to `PATH` last.
   - Filter out `C:\Windows\System32\bash.exe` / `Sysnative\bash.exe` (WSL launchers) to prevent Hermes from receiving `/mnt/d/...` paths.
   - Convert Windows CWD to MSYS path in `LocalEnvironment` for bash, while keeping the Windows path for Python `open()` / `os.unlink()`.
   - Convert temp directories to MSYS form so bash can write snapshot / cwd files.
   - Later syncs merged upstream `expanduser` and auto-recovery logic for stale CWDs: convert MSYS CWD back to Windows path for existence check, then sync the MSYS path back.

2. **Terminal Output & Process Management**
   - Replace `select.select()` with `proc.stdout.buffer.read1()` for Windows pipe reading, fixing empty terminal tool output.
   - Add Windows-compatible PID file read/write, `taskkill` calls, and process state checks.
   - Use atomic writes for Gateway restart markers to reduce Windows file lock conflicts.

3. **UTF-8 Encoding Fixes**
   - Add `encoding="utf-8", errors="replace"` to numerous `subprocess.run(..., text=True)` calls to prevent crashes caused by Windows default GBK decoding in Gateway / CLI.
   - Reconfigure stdout / stderr to UTF-8 in `hermes_cli/main.py`.
   - Full stdin / stdout / stderr UTF-8 reconfiguration in `tui_gateway/entry.py` and `slash_worker.py`, fixing garbled Chinese input.
   - Write UTF-8 bytes directly to the underlying buffer in `tui_gateway/transport.py`, bypassing encoding layers that Rich or TextIOWrapper might revert to GBK.
   - Subsequent upstream refactors retain the UTF-8 flag for npm, plugin install/update, `which`, `systemctl`, and other subprocesses.

4. **Dashboard / TUI Chat**
   - Add a Windows ConPTY backend in `hermes_cli/pty_bridge.py` via `pywinpty` to support embedding a real TUI in Dashboard Chat.
   - Pass `HERMES_PYTHON` when Dashboard starts TUI so the Node child process uses the current venv's Python, avoiding missing `tui_gateway`.
   - Initially used ephemeral sessions to prevent Dashboard Chat from creating empty untitled sessions; later superseded by upstream lazy session creation.
   - Windows encoding and ConPTY patches are retained when merging upstream TUI long-session performance, stdio half-close pipe, production React, and cold-start optimization changes.

5. **Dangerous Command & Safety Interception**
   - Intercept `find /`, `find /home`, `ls -R /`, and similar commands that traverse the entire Windows root under Git Bash in `tools/approval.py`.
   - Windows-specific interception rules are preserved through subsequent merges with upstream hardline blocklist and pre-compiled dangerous pattern changes.

6. **Frontend & Dependency Build**
   - Unified UTF-8 encoding for npm subprocesses to prevent Windows console output from causing decode failures.
   - Fix Web build dependency in the 04-29 sync: pin `@nous-research/ui` to a stable version, eliminating a TypeScript build error at that time.

7. **Windows Patches Retained During Upstream Syncs**
   - The main work in syncs on 04-27, 04-29, 04-30, 05-01, and 05-07 was resolving conflicts while preserving the above Windows patches.
   - The 05-01 sync also merged upstream's new ACP WSL cwd normalization and Gateway atomic write / Windows lock fixes.
   - The 05-07 merge continues to retain ConPTY, MSYS path conversion, UTF-8 subprocess encoding, plugin install encoding, and cwd recovery patches.

For more detailed porting records see [../winodws_support_EN/](../winodws_support_EN/).
