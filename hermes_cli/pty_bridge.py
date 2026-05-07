"""PTY bridge for `hermes dashboard` chat tab.

Wraps a child process behind a pseudo-terminal so its ANSI output can be
streamed to a browser-side terminal emulator (xterm.js) and typed
keystrokes can be fed back in.  The only caller today is the
``/api/pty`` WebSocket endpoint in ``hermes_cli.web_server``.

Design constraints:

* **Cross-platform.**  On POSIX the bridge uses :mod:`ptyprocess` (native
  ``openpty(3)``).  On Windows it uses :mod:`pywinpty` (ConPTY on Windows
  10+, WinPTY fallback on older systems).  :class:`PtyUnavailableError` is
  raised when neither backend is available.
* **Zero Node dependency on the server side.**  We use :mod:`ptyprocess`
  or :mod:`pywinpty`, both pure-Python wrappers around OS calls.  The browser
  talks to the same ``hermes --tui`` binary it would launch from the CLI, so
  every TUI feature (slash popover, model picker, tool rows, markdown,
  skin engine, clarify/sudo/approval prompts) ships automatically.
* **Byte-safe I/O.**  Reads and writes go through the PTY master directly
  — streaming ANSI is inherently byte-oriented and UTF-8 boundaries may land
  mid-read.  On Windows the str-based pywinpty API is bridged to bytes at
  the boundary.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional, Sequence

# ---------------------------------------------------------------------------
# Backend detection — resolved once at import time.
# ---------------------------------------------------------------------------
_PTY_BACKEND: str = "none"  # "posix" | "win" | "none"

if sys.platform == "win32":
    # Stubs so that type checkers don't complain about fcntl / termios etc.
    fcntl = None  # type: ignore[assignment]
    select = None  # type: ignore[assignment]
    signal = None  # type: ignore[assignment]
    termios = None  # type: ignore[assignment]

    try:
        from winpty.ptyprocess import PtyProcess as _WinPtyProcess  # type: ignore[import-untyped]
        _PTY_BACKEND = "win"
    except ImportError:
        _WinPtyProcess = None  # type: ignore[assignment,misc]
else:
    import errno
    import fcntl
    import select
    import signal
    import struct
    import termios

    try:
        import ptyprocess  # type: ignore[import-untyped]
        _PTY_BACKEND = "posix"
    except ImportError:  # pragma: no cover — dev env without ptyprocess
        ptyprocess = None  # type: ignore[assignment]

_PTY_AVAILABLE = _PTY_BACKEND != "none"


__all__ = ["PtyBridge", "PtyUnavailableError"]


class PtyUnavailableError(RuntimeError):
    """Raised when a PTY cannot be created on this platform.

    This means the ``ptyprocess`` package is missing (POSIX), the
    ``pywinpty`` package is missing (Windows), or the platform is
    fundamentally unsupported.  The dashboard surfaces the message to the
    user as a chat-tab banner.
    """


class PtyBridge:
    """Wrapper around a PTY-backed child process for byte streaming.

    Internally dispatches to ``ptyprocess`` (POSIX) or ``pywinpty`` (Windows).
    The public API is identical on every platform.
    """

    def __init__(self, proc, *, backend: str):
        self._proc = proc
        self._backend = backend
        self._closed = False
        if backend == "posix":
            self._fd: Optional[int] = proc.fd
        else:
            self._fd = None

    # -- lifecycle --------------------------------------------------------

    @classmethod
    def is_available(cls) -> bool:
        """True if a PTY can be spawned on this platform."""
        return bool(_PTY_AVAILABLE)

    @classmethod
    def spawn(
        cls,
        argv: Sequence[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        cols: int = 80,
        rows: int = 24,
    ) -> "PtyBridge":
        """Spawn ``argv`` behind a new PTY and return a bridge.

        Raises :class:`PtyUnavailableError` if the platform can't host a
        PTY.  Raises :class:`FileNotFoundError` or :class:`OSError` for
        ordinary exec failures (missing binary, bad cwd, etc.).
        """
        if not _PTY_AVAILABLE:
            if sys.platform == "win32":
                raise PtyUnavailableError(
                    "Pseudo-terminals are unavailable on this platform. "
                    "Install the `pywinpty` package: pip install pywinpty "
                    "(or pip install -e '.[pty]')."
                )
            if ptyprocess is None:
                raise PtyUnavailableError(
                    "The `ptyprocess` package is missing. "
                    "Install with: pip install ptyprocess "
                    "(or pip install -e '.[pty]')."
                )
            raise PtyUnavailableError("Pseudo-terminals are unavailable.")
        # PTY-hosted programs expect TERM to describe the terminal type.
        # CI often runs without TERM in the parent process, which makes
        # simple terminal probes like `tput cols` fail before winsize reads.
        # Preserve explicit caller overrides, but backfill a sensible default
        # when TERM is missing or blank.
        spawn_env = (os.environ.copy() if env is None else env.copy())
        if not spawn_env.get("TERM"):
            spawn_env["TERM"] = "xterm-256color"

        if _PTY_BACKEND == "win":
            proc = _WinPtyProcess.spawn(
                list(argv),
                cwd=cwd,
                env=spawn_env,
                dimensions=(rows, cols),
            )
            return cls(proc, backend="win")
        else:
            proc = ptyprocess.PtyProcess.spawn(  # type: ignore[union-attr]
                list(argv),
                cwd=cwd,
                env=spawn_env,
                dimensions=(rows, cols),
            )
            return cls(proc, backend="posix")

    @property
    def pid(self) -> int:
        return int(self._proc.pid)

    def is_alive(self) -> bool:
        if self._closed:
            return False
        try:
            return bool(self._proc.isalive())
        except Exception:
            return False

    # -- I/O --------------------------------------------------------------

    def read(self, timeout: float = 0.2) -> Optional[bytes]:
        """Read up to 64 KiB of raw bytes from the PTY master.

        Returns:
            * bytes — zero or more bytes of child output
            * empty bytes (``b""``) — no data available within ``timeout``
            * None — child has exited and the master fd is at EOF

        Never blocks longer than ``timeout`` seconds.  Safe to call after
        :meth:`close`; returns ``None`` in that case.
        """
        if self._closed:
            return None
        if self._backend == "posix":
            return self._read_posix(timeout)
        return self._read_win(timeout)

    def _read_posix(self, timeout: float) -> Optional[bytes]:
        try:
            readable, _, _ = select.select([self._fd], [], [], timeout)
        except (OSError, ValueError):
            return None
        if not readable:
            return b""
        try:
            data = os.read(self._fd, 65536)  # type: ignore[arg-type]
        except OSError as exc:
            if exc.errno in (errno.EIO, errno.EBADF):
                return None
            raise
        if not data:
            return None
        return data

    def _read_win(self, timeout: float) -> Optional[bytes]:
        import socket as _socket

        proc = self._proc
        # pywinpty's PtyProcess uses an internal socket thread for I/O.
        # Set a timeout on the socket so recv() won't block forever.
        try:
            old_timeout = proc.fileobj.gettimeout()
        except Exception:
            old_timeout = None
        try:
            proc.fileobj.settimeout(timeout)
            try:
                text = proc.read(65536)
            except _socket.timeout:
                return b""
            except EOFError:
                return None
            except OSError:
                return None
        finally:
            try:
                proc.fileobj.settimeout(old_timeout)
            except OSError:
                pass
        if not text:
            return b""
        return text.encode("utf-8")

    def write(self, data: bytes) -> None:
        """Write raw bytes to the PTY master (i.e. the child's stdin)."""
        if self._closed or not data:
            return
        if self._backend == "posix":
            self._write_posix(data)
        else:
            self._write_win(data)

    def _write_posix(self, data: bytes) -> None:
        view = memoryview(data)
        while view:
            try:
                n = os.write(self._fd, view)  # type: ignore[arg-type]
            except OSError as exc:
                if exc.errno in (errno.EIO, errno.EBADF, errno.EPIPE):
                    return
                raise
            if n <= 0:
                return
            view = view[n:]

    def _write_win(self, data: bytes) -> None:
        try:
            self._proc.write(data.decode("utf-8"))
        except (EOFError, OSError):
            return

    def resize(self, cols: int, rows: int) -> None:
        """Forward a terminal resize to the child process."""
        if self._closed:
            return
        if self._backend == "posix":
            self._resize_posix(cols, rows)
        else:
            self._resize_win(cols, rows)

    def _resize_posix(self, cols: int, rows: int) -> None:
        winsize = struct.pack("HHHH", max(1, rows), max(1, cols), 0, 0)
        try:
            fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)  # type: ignore[union-attr]
        except OSError:
            pass

    def _resize_win(self, cols: int, rows: int) -> None:
        try:
            self._proc.setwinsize(rows, cols)
        except Exception:
            pass

    # -- teardown ---------------------------------------------------------

    def close(self) -> None:
        """Terminate the child and clean up.

        On POSIX: SIGTERM → 0.5 s grace → SIGKILL escalation.
        On Windows: ``terminate(force=True)`` via ConPTY.
        Idempotent.
        """
        if self._closed:
            return
        self._closed = True

        if self._backend == "posix":
            self._close_posix()
        else:
            self._close_win()

    def _close_posix(self) -> None:
        for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGKILL):  # type: ignore[union-attr]
            if not self._proc.isalive():
                break
            try:
                self._proc.kill(sig)
            except Exception:
                pass
            deadline = time.monotonic() + 0.5
            while self._proc.isalive() and time.monotonic() < deadline:
                time.sleep(0.02)
        try:
            self._proc.close(force=True)
        except Exception:
            pass

    def _close_win(self) -> None:
        try:
            self._proc.terminate(force=True)
        except Exception:
            pass

    # Context-manager sugar — handy in tests and ad-hoc scripts.
    def __enter__(self) -> "PtyBridge":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
