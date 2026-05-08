# Hermes Windows Environment: rg and Terminal Path Tips

> Updated: 2026-04-23
> Applicable environment: Windows + Git Bash / WSL

---

## Core Issue: Path Formats

| Tool | Path Format | Example |
|------|-------------|---------|
| Windows Native | `D:\Doc\Folder` | ❌ Incompatible |
| search_files / rg | `D:/Doc/Folder` (forward slashes) | ✅ Works |
| terminal bash | `/d/Doc/Folder` (Git Bash style) | ✅ Works |
| Python | `D:/Doc/Folder` or `D:\\Doc\\Folder` | ✅ Works |

**Rules:**
- `search_files` (underlying rg) uses the `D:/Doc` format
- `terminal` bash commands use the `/d/Doc` format
- `write_file` / `patch` tools use the `/d/Doc` format (actual path conversion is handled internally by the tools)
- ⚠️ Never use Windows native backslashes `D:\Doc`

---

## Dangerous Commands (will hang when executed in terminal)

| Command | Reason | Alternative |
|---------|--------|-------------|
| `find /` | Traverses the entire Linux root directory | Specify a concrete path |
| `find /home` | Traverses /home, may hang | Specify a concrete path |
| `ls -R /` | Recursively lists root directory | Specify a concrete path |

**General rule:** `find` must specify a target path; starting from the root directory is prohibited.

---

## Complete search_files Tool Usage

```bash
# Search file content
search_files(pattern="keyword", target="content", path="D:/Doc")

# Search filenames
search_files(pattern="*.py", target="files", path="D:/Doc")

# Limit result count
search_files(pattern="keyword", limit=20, path="D:/Doc")

# Output modes
search_files(pattern="keyword", output_mode="content")    # Show matching lines + line numbers
search_files(pattern="keyword", output_mode="files_only") # Show only filenames
search_files(pattern="keyword", output_mode="count")      # Match count per file
```

---

## Complete terminal Tool Usage

```bash
# Basic commands (note path format)
terminal(command="ls /d/Doc", workdir="/tmp")

# Search files (never start from root!)
terminal(command="find /d/Doc -name '*.md'")

# Get current working directory
terminal(command="pwd")

# Check if file exists
terminal(command="test -f /d/Doc/test.txt && echo 'exists' || echo 'not found'")

# Commands to avoid
terminal(command="find / -name '*.txt'")  # ❌ will hang
terminal(command="ls -R /")               # ❌ recursive list from root
```

---

## Source Code Modification Suggestions (hermes-agent-windows-R)

### 1. Add Path Auto-Conversion Function

```python
import re

def windows_to_bash_path(path: str) -> str:
    """Convert Windows path to Git Bash style path"""
    if not path:
        return path
    
    # Already Git Bash style
    if path.startswith('/'):
        return path
    
    # Windows absolute path: D:\Doc\Folder or D:/Doc/Folder
    match = re.match(r'^([A-Za-z]):[/\\](.*)$', path)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace('\\', '/')
        return f"/{drive}/{rest}"
    
    # Relative path or other format
    return path.replace('\\', '/')
```

### 2. Dangerous Command Interceptor

```python
import re

def is_dangerous_command(command: str) -> bool:
    """Check if a command is dangerous"""
    # Block find commands starting from root directory
    if re.search(r'\bfind\s+(/|[/$])\b', command):
        return True
    
    # Block recursive listing of root directory
    if re.search(r'ls\s+-R\s+/', command):
        return True
    
    return False

def sanitize_and_execute(command: str, workdir: str = None) -> str:
    """Execute command safely"""
    if is_dangerous_command(command):
        raise ValueError(f"Dangerous command blocked: {command}")
    
    # Path conversion
    if workdir:
        workdir = windows_to_bash_path(workdir)
    
    # Execute...
```

### 3. Path Preprocessing for rg Calls

```python
def rg_safe_path(path: str) -> str:
    """Ensure rg uses forward-slash paths"""
    if not path:
        return path
    # Convert to forward slashes
    return path.replace('\\', '/')
```

---

## Verification Methods

```bash
# Verify path conversion
python -c "print(windows_to_bash_path('D:\\Doc\\Folder'))"
# Output: /d/Doc/Folder

# Verify file exists
test -f /d/Doc/20260423/test.txt && echo "OK" || echo "FAIL"

# Verify rg search
rg "keyword" /d/Doc --files | head -5
```

---

## Common Error Reference Table

| Error Symptom | Cause | Solution |
|---------------|-------|----------|
| `find /` hangs | Searching from root directory | Specify a concrete path |
| `rg "keyword" D:\Doc` fails | Backslash path | Change to `D:/Doc` |
| `terminal` path error | Windows path not converted | Use `/d/Doc` format |
| File write failed | Path format issue | Verify tool's path format |
| `ls /home` hangs | Directory doesn't exist or no permission | Specify an existing path |

---

## Additional Issue Record (2026-04-23)

### write_file / patch Tools Cannot Create Files Under Windows Paths

**Symptom:** Using `write_file(path="D:/Doc/20260423/test.md")` or `patch` tool, the file cannot be created — no error is shown but the file does not exist.

**Root Cause (analyzed):**
Three issues chained together to cause write failure:
1. `LocalEnvironment.get_temp_dir()` falls back to `/tmp`; Python's `open("/tmp/...")` uses Windows path semantics and cannot find Git Bash's `/tmp`, so the session cwd file cannot be read
2. `self.cwd` is always in Windows format returned by `os.getcwd()` (`D:\Code\...`); bash's `cd 'D:\Code\...'` in Git Bash single quotes preserves backslashes literally, which is unreliable
3. `_wrap_command` embeds Windows paths directly into bash scripts without converting to MSYS format

**Fixed (2026-04-23):** Modified `LocalEnvironment` in `tools/environments/local.py`:
- `__init__`: Converts the initial CWD to MSYS format (`/d/Code/...`) so bash `cd` commands work reliably
- `get_temp_dir()`: On Windows, returns the Windows temp directory in MSYS format (`/c/Users/.../AppData/Local/Temp/hermes`) so bash scripts can write to it
- Added `_snapshot_path_win` / `_cwd_file_win`: Windows-format paths for use by Python `open()` / `os.unlink()`
- `_update_cwd`: Uses `_cwd_file_win` to read the cwd file (accessible by Python)
- `cleanup`: Uses Windows-format paths to delete temporary files

---

> 💡 **Tip:** The `write_file` path issue has been fixed in `tools/environments/local.py`.
