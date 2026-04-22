"""Cross-platform helpers for Windows/Unix runtime differences.

Centralises the subtle behavioural differences that keep biting Windows:
    * ``os.kill(pid, 0)`` can raise WinError 11/87 instead of ProcessLookupError.
    * ``signal.SIGKILL`` / ``SIGUSR1`` don't exist on Windows.
    * ``preexec_fn=os.setsid`` and ``os.killpg`` require POSIX.
    * Detached subprocesses need ``creationflags`` on Windows, ``start_new_session`` on POSIX.
    * ``fcntl.flock`` vs ``msvcrt.locking`` for file locks.

Modules needing platform guards should import from here rather than rolling
their own checks so the fix only has to live in one place.
"""

from __future__ import annotations

import os
import platform
import signal
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_IS_WINDOWS = platform.system() == "Windows"

try:
    import fcntl as _fcntl
except Exception:
    _fcntl = None

try:
    import msvcrt as _msvcrt
except Exception:
    _msvcrt = None


def pid_alive(pid: int) -> bool:
    """Cross-platform check whether ``pid`` is a living process.

    On Windows, ``os.kill(pid, 0)`` is unsafe and can raise WinError 11/87
    because signal 0 is not supported consistently. Use psutil when
    available and fall back to ``tasklist`` otherwise. On POSIX, ``os.kill
    (pid, 0)`` is the canonical existence check.
    """
    if not pid or pid <= 0:
        return False

    if _IS_WINDOWS:
        try:
            import psutil

            return psutil.pid_exists(pid)
        except ImportError:
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return str(pid) in result.stdout
            except Exception:
                return True

    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def terminate_pid(pid: int, *, force: bool = False) -> None:
    """Terminate a PID with platform-appropriate force semantics.

    POSIX uses SIGTERM/SIGKILL. Windows uses ``taskkill /T /F`` for true
    tree-killing because ``os.kill(pid, SIGTERM)`` on Windows maps to
    TerminateProcess on only the target pid, not its children.
    """
    if force and _IS_WINDOWS:
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            os.kill(pid, signal.SIGTERM)
            return

        if result.returncode != 0:
            details = (result.stderr or result.stdout or "").strip()
            raise OSError(details or f"taskkill failed for PID {pid}")
        return

    sig = signal.SIGTERM if not force else getattr(signal, "SIGKILL", signal.SIGTERM)
    os.kill(pid, sig)


def get_detached_popen_kwargs() -> dict:
    """Return platform-appropriate kwargs for detached subprocess launch."""
    if _IS_WINDOWS:
        creationflags = 0
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        return {"creationflags": creationflags}
    return {"start_new_session": True}


def shell_join(parts: list[str]) -> str:
    """Quote argv parts for a shell command string."""
    if _IS_WINDOWS:
        return subprocess.list2cmdline(parts)
    import shlex
    return " ".join(shlex.quote(part) for part in parts)


def get_host_temp_dir(app_name: str = "hermes") -> Path:
    """Return a temp directory for host-side Hermes runtime files."""
    path = Path(tempfile.gettempdir()) / app_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_host_temp_path(name: str, app_name: str = "hermes") -> Path:
    """Return a stable file path under the host temp directory."""
    return get_host_temp_dir(app_name) / name


def windows_path_to_msys(path: str) -> str:
    """Convert a Windows absolute path to MSYS/Git-Bash form.

    Git Bash runs MSYS coreutils that require paths in MSYS form:
    ``D:\\Doc\\foo`` or ``D:/Doc/foo``  →  ``/d/Doc/foo``

    Without this conversion, ``D:/Doc/foo`` is treated as a *relative* path
    by MSYS tools (there is no ``D:`` drive in the POSIX namespace they see),
    which creates junk artifacts under the current working directory.

    Idempotent: already-MSYS paths (``/d/...``) are returned unchanged.
    Non-Windows or relative paths are returned unchanged.
    """
    if not path:
        return path
    # Normalise any remaining backslashes first
    p = path.replace("\\", "/")
    # Match ``X:/...`` (drive letter + colon + optional slash)
    import re as _re
    m = _re.match(r'^([A-Za-z]):(/?)(.*)', p)
    if m:
        drive, _sep, rest = m.groups()
        rest = rest.lstrip("/")
        return f"/{drive.lower()}/{rest}" if rest else f"/{drive.lower()}/"
    return p


def msys_path_to_windows(path: str) -> str:
    """Convert an MSYS/Git-Bash absolute path back to Windows form.

    ``/d/Doc/foo``  →  ``D:/Doc/foo``

    Useful when you need to hand an MSYS-reported path back to Python's
    ``pathlib`` or other Windows-native APIs.

    Idempotent: already-Windows paths are returned unchanged.
    Non-MSYS paths (e.g. ``/usr/bin``) are returned unchanged.
    """
    if not path:
        return path
    import re as _re
    m = _re.match(r'^/([a-zA-Z])/(.*)', path)
    if m:
        drive, rest = m.groups()
        return f"{drive.upper()}:/{rest}"
    return path


# ---------------------------------------------------------------------------
# PowerShell invocation helper
# ---------------------------------------------------------------------------

_ps_exe: str | None | bool = False  # False = not yet probed


def _find_powershell() -> str | None:
    """Return the first working PowerShell executable name, or None."""
    for name in ("pwsh", "powershell"):
        try:
            r = subprocess.run(
                [name, "-NoProfile", "-NonInteractive", "-Command", "exit 0"],
                capture_output=True,
                timeout=5,
            )
            if r.returncode == 0:
                return name
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return None


def get_powershell_exe() -> str | None:
    """Return the cached PowerShell executable name, probing once per process."""
    global _ps_exe
    if _ps_exe is False:
        _ps_exe = _find_powershell()
    return _ps_exe  # type: ignore[return-value]


def run_powershell(
    script: str,
    *,
    timeout: int = 30,
    check: bool = False,
) -> "subprocess.CompletedProcess[str]":
    """Run a PowerShell script string and return the CompletedProcess.

    Uses ``pwsh`` (PowerShell 7+) if available, falls back to ``powershell``
    (Windows PowerShell 5.1).  Raises ``RuntimeError`` when no PowerShell is
    found.

    Args:
        script:  The PowerShell script text to execute.
        timeout: Seconds before the subprocess is killed.
        check:   If True, raise CalledProcessError on non-zero exit code.
    """
    exe = get_powershell_exe()
    if exe is None:
        raise RuntimeError(
            "No PowerShell executable found (tried 'pwsh' and 'powershell'). "
            "Install PowerShell 7+ or ensure Windows PowerShell 5.1 is on PATH."
        )
    return subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Acquire an exclusive cross-platform file lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(path, "a+")
    try:
        if _fcntl is not None:
            _fcntl.flock(lock_file.fileno(), _fcntl.LOCK_EX)
        elif _msvcrt is not None:
            lock_file.seek(0)
            _msvcrt.locking(lock_file.fileno(), _msvcrt.LK_LOCK, 1)
        yield
    finally:
        try:
            if _fcntl is not None:
                _fcntl.flock(lock_file.fileno(), _fcntl.LOCK_UN)
            elif _msvcrt is not None:
                lock_file.seek(0)
                _msvcrt.locking(lock_file.fileno(), _msvcrt.LK_UNLCK, 1)
        finally:
            lock_file.close()
