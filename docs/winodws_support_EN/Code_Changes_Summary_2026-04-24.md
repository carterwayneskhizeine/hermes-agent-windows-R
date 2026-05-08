# Hermes Windows Adaptation Code Changes Summary

> Updated: 2026-04-24
> Baseline: Before commit 032d0e7
> Scope: Windows path compatibility, WSL interference fix, dangerous command interception

---

## Modified File List

| File Path | Modification Type | Line Changes |
|-----------|-------------------|--------------|
| `README.md` | Updated | +18 -6 |
| `docs/winodws_support/Windows路径测试经验.md` | Added | +106 |
| `docs/winodws_support/rg-terminal-path-tips.md` | Added | +197 |
| `tools/approval.py` | Updated | +6 |
| `tools/environments/local.py` | Updated | +90 -21 |

---

## Detailed Code Changes

### 1. README.md

#### Git Bash Path Detection Order Adjustment

**Before:**
```markdown
Hermes automatically detects `bash.exe` in the following order:
1. Environment variable `HERMES_GIT_BASH_PATH`
2. `shutil.which("bash")`
3. `%ProgramFiles%\Git\bin\bash.exe`
4. `%ProgramFiles(x86)%\Git\bin\bash.exe`
5. `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`
```

**After:**
```markdown
Hermes automatically detects `bash.exe` in the following order (WSL launcher filtered):
1. Environment variable `HERMES_GIT_BASH_PATH`
2. `%ProgramFiles%\Git\bin\bash.exe`
3. `%ProgramFiles(x86)%\Git\bin\bash.exe`
4. `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`
5. `shutil.which("bash")` (skipping WSL launcher at `C:\Windows\System32\bash.exe`)

> ⚠️ **WSL bash is not supported**: WSL uses the `/mnt/d/...` path convention, which is incompatible with Git Bash's `/d/...`
```

**Reason:** After installing WSL, `shutil.which("bash")` returns the WSL launcher, causing path format errors.

#### Added Session CWD and Temp File Notes

**New content:**
```markdown
### Session CWD and Temp Files

`LocalEnvironment` (`tools/environments/local.py`) does extra work on Windows:
- Initial CWD is converted via `windows_path_to_msys()` to `/d/Code/...`
- Session snapshots / CWD temp files are placed in `%LOCALAPPDATA%\Temp\hermes\`
- Also saves `_snapshot_path_win` / `_cwd_file_win` (Windows form)
```

#### Added Dangerous Command Interception Notes

**New content:**
```markdown
### Dangerous Command Interception

`tools/approval.py` intercepts commands that would hang or damage entire drives under Git Bash:
- `find /` — MSYS maps `/` to the entire Windows root
- `find /home` — similar issue
- `ls -R /` — recursively lists root directory
```

---

### 2. tools/approval.py

#### New Dangerous Command Patterns

**File location:** `tools/approval.py:135-141`

**New code:**
```python
# Filesystem root traversal — hangs on Windows Git Bash because MSYS maps
# / to the Windows root, making these commands traverse the entire drive.
# Also extremely slow on Linux/macOS without a specific path target.
(r'\bfind\s+/(?:\s|$)', "find from filesystem root (hangs on Windows Git Bash)"),
(r'\bfind\s+/home(?:/\s|\s|$)', "find traversal of /home (may hang on Windows Git Bash)"),
(r'\bls\s+(?:-\S+\s+)*-\S*R\S*\s+/\s*$', "recursive ls of filesystem root (hangs)"),
```

**Purpose:** Intercepts commands that would cause Git Bash to hang, preventing traversal of the entire Windows file system.

---

### 3. tools/environments/local.py

#### New WSL Bash Detection Function

**File location:** `tools/environments/local.py:171-195`

**New code:**
```python
def _is_wsl_bash(path: str) -> bool:
    """Return True if *path* is the WSL bash launcher (C:\\Windows\\System32\\bash.exe).

    The WSL launcher reports Linux paths (``/mnt/d/...``) instead of Git Bash's
    ``/d/...`` format, which breaks Hermes' path normalization.  We detect it
    by path match since both share the name ``bash.exe``.
    """
    try:
        normalized = os.path.normcase(os.path.normpath(path))
        system32 = os.path.normcase(os.path.normpath(
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "bash.exe")
        ))
        sysnative = os.path.normcase(os.path.normpath(
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Sysnative", "bash.exe")
        ))
        return normalized in (system32, sysnative)
    except Exception:
        return False
```

#### Modified Bash Discovery Logic

**File location:** `tools/environments/local.py:153-169`

**Before:**
```python
def _find_bash() -> str:
    if custom and os.path.isfile(custom):
        return custom

    found = shutil.which("bash")
    if found:
        return found

    for candidate in (
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Git", "bin", "bash.exe"),
        ...
    ):
        if candidate and os.path.isfile(candidate):
            return candidate
```

**After:**
```python
def _find_bash() -> str:
    if custom and os.path.isfile(custom):
        return custom

    # Prefer Git Bash over shutil.which("bash") — on Windows with WSL
    # installed, which("bash") returns C:\Windows\System32\bash.exe
    # (the WSL launcher).  WSL uses /mnt/d/... path convention instead of
    # Git Bash's /d/..., which breaks all of Hermes' path normalization.
    for candidate in (
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Git", "bin", "bash.exe"),
        ...
    ):
        if candidate and os.path.isfile(candidate):
            return candidate

    # Fall back to PATH lookup, but skip the WSL launcher.
    found = shutil.which("bash")
    if found and not _is_wsl_bash(found):
        return found
```

**Reason:** Prioritize detecting Git Bash-specific paths to avoid WSL launcher interference.

#### Modified LocalEnvironment.__init__

**File location:** `tools/environments/local.py:249-275`

**Before:**
```python
def __init__(self, cwd: str = "", timeout: int = 60, env: dict = None):
    super().__init__(cwd=cwd or os.getcwd(), timeout=timeout, env=env)
    self.init_session()
```

**After:**
```python
def __init__(self, cwd: str = "", timeout: int = 60, env: dict = None):
    if _IS_WINDOWS:
        from tools.platform_compat import windows_path_to_msys
        # Convert Windows CWD to MSYS form so bash 'cd' works in Git Bash.
        init_cwd = windows_path_to_msys(cwd) if cwd else windows_path_to_msys(os.getcwd())
    else:
        init_cwd = cwd or os.getcwd()

    super().__init__(cwd=init_cwd, timeout=timeout, env=env)

    if _IS_WINDOWS:
        from tools.platform_compat import msys_path_to_windows
        self._snapshot_path_win = msys_path_to_windows(self._snapshot_path)
        self._cwd_file_win = msys_path_to_windows(self._cwd_file)
    else:
        self._snapshot_path_win = self._snapshot_path
        self._cwd_file_win = self._cwd_file

    self.init_session()
```

**Reason:**
1. Converting Windows CWD to MSYS format ensures bash `cd` works reliably
2. Saving Windows-format paths for Python file operations

#### Modified get_temp_dir()

**File location:** `tools/environments/local.py:277-297`

**Before:**
```python
def get_temp_dir(self) -> str:
    """Return a shell-safe writable temp dir for local execution.

    Termux does not provide /tmp by default, but exposes a POSIX TMPDIR.
    Prefer POSIX-style env vars when available...
    """
    for env_var in ("TMPDIR", "TMP", "TEMP"):
        candidate = self.env.get(env_var) or os.environ.get(env_var)
        if candidate and candidate.startswith("/"):
            return candidate
    return "/tmp"
```

**After:**
```python
def get_temp_dir(self) -> str:
    """Return a shell-safe writable temp dir for local execution.

    On Windows: returns the MSYS form of the Windows temp dir so that
    bash scripts can write snapshot/cwd files there...
    """
    if _IS_WINDOWS:
        from tools.platform_compat import get_host_temp_dir, windows_path_to_msys
        win_path = str(get_host_temp_dir("hermes"))
        return windows_path_to_msys(win_path)

    for env_var in ("TMPDIR", "TMP", "TEMP"):
        candidate = self.env.get(env_var) or os.environ.get(env_var)
        if candidate and candidate.startswith("/"):
            return candidate
    return "/tmp"
```

**Reason:** On Windows, returns the temp directory in MSYS format so bash scripts can write to it.

#### Modified _update_cwd()

**File location:** `tools/environments/local.py:350-357`

**Before:**
```python
def _update_cwd(self, result: dict):
    """Read CWD from temp file (local-only, no round-trip needed)."""
    try:
        cwd_path = open(self._cwd_file).read().strip()
        if cwd_path:
            self.cwd = cwd_path
    except (OSError, FileNotFoundError):
        pass
```

**After:**
```python
def _update_cwd(self, result: dict):
    """Read CWD from temp file (local-only, no round-trip needed)."""
    try:
        # Use the Windows-form path so Python's open() finds the file.
        cwd_path = open(self._cwd_file_win).read().strip()
        if cwd_path:
            self.cwd = cwd_path
    except (OSError, FileNotFoundError):
        pass
```

**Reason:** Uses Windows-format path so Python's `open()` can find the file.

#### Modified cleanup()

**File location:** `tools/environments/local.py:359-365`

**Before:**
```python
def cleanup(self):
    """Clean up temp files."""
    for f in (self._snapshot_path, self._cwd_file):
        try:
            os.unlink(f)
        except OSError:
            pass
```

**After:**
```python
def cleanup(self):
    """Clean up temp files."""
    # Use Windows-form paths so os.unlink() can find the files on Windows.
    for f in (self._snapshot_path_win, self._cwd_file_win):
        try:
            os.unlink(f)
        except OSError:
            pass
```

**Reason:** Uses Windows-format paths so `os.unlink()` can find the files.

---

### 4. docs/winodws_support/Windows路径测试经验.md

**New file, 106 lines**, recording Windows path testing experience:
- Chinese directory and filename testing
- Path with spaces testing
- Multi-level nested directory testing
- Overwrite write and delete testing

### 5. docs/winodws_support/rg-terminal-path-tips.md

**New file, 197 lines**, recording rg and terminal path tips in the Windows environment:
- Core issue: path format comparison table
- Dangerous command list
- search_files / terminal tool usage
- Source code modification suggestions
- Common error reference table

---

## Summary of Changes

### Problem Background

1. **WSL Bash Interference**: After installing WSL, `shutil.which("bash")` returns the WSL launcher, resulting in paths in `/mnt/d/...` format instead of Git Bash's `/d/...`
2. **Path Conversion Failure**: CWD and temp file paths were not correctly converted, preventing Python from reading files written by bash
3. **Dangerous Commands**: Commands like `find /` traverse the entire Windows file system under Git Bash, causing hangs

### Solutions

1. **Adjusted Bash Detection Order**: Prioritize Git Bash-specific paths, falling back to PATH lookup with WSL launcher filtering only as a last resort
2. **Dual-path Storage**: Save both MSYS format (for bash) and Windows format (for Python)
3. **Dangerous Command Interception**: Added dangerous command patterns in `tools/approval.py`

### Verification Results

- ✅ Chinese directories and filenames work correctly
- ✅ Paths with spaces work correctly
- ✅ Multi-level nested directories work correctly
- ✅ Write/Read/Overwrite/Rename/Delete work correctly
- ✅ WSL bash is correctly filtered
- ✅ Dangerous commands are correctly intercepted

---

> Change statistics based on changes after commit 032d0e7, covering 3 commits:
> - 92acdc3: refactor(platform): implement MSYS path conversion
> - c50838d: fix(tools): prevent Windows path collapse
> - dd031e0: feat(tools): add cross-platform process management
> - 032d0e7: docs(windows): add Windows compatibility guide
> - cb89e64: docs(windows): add terminal path tips
> - e90d89e: fix(env): resolve Windows path compatibility and WSL interference
