# Hermes Windows Adaptation Code Changes Summary

> Updated: 2026-04-27
> Baseline: Branch hermes/2026-04-26 (commit 9438c914)
> Scope: Sync 251 upstream commits, resolve 2 merge conflicts, retain all Windows optimizations

---

## Operation Overview

Created `hermes/2026-04-27` from `hermes/2026-04-26`, executed `git merge upstream/main` to bring in 251 new upstream NousResearch/hermes-agent commits (up to `ee1a07f9`), resolved 2 conflicts, all Windows adaptation patches fully retained.

---

## Merge Statistics

| Item | Count |
|------|-------|
| Upstream commits merged | 251 |
| Files auto-merged successfully | All except 2 |
| Files with manually resolved conflicts | 2 |
| Windows optimizations lost | 0 |

---

## Conflict Resolution Details

### 1. hermes_cli/main.py

#### Conflict Cause

Upstream in commit `34eb1aaa` (`fix(update): use npm ci to stop rewriting package-lock on every update`) extracted the npm install logic into a new function `_run_npm_install_deterministic`, replacing the original inline `subprocess.run(["npm", "install", ...])` with a function call.

Our 04-26 changes added `encoding="utf-8", errors="replace"` to the original inline call, conflicting with upstream's refactoring.

#### Resolution

Adopted upstream's `_run_npm_install_deterministic` refactoring (accepting the code improvement), while adding the Windows-required encoding parameters to both `subprocess.run` calls **inside the function definition**.

**Modified location:** `hermes_cli/main.py:5076-5094` (function `_run_npm_install_deterministic`)

```python
# Before (upstream original, missing encoding)
ci_result = subprocess.run(
    ci_cmd,
    cwd=cwd,
    capture_output=capture_output,
    text=True,
    check=False,
)
...
return subprocess.run(
    install_cmd,
    cwd=cwd,
    capture_output=capture_output,
    text=True,
    check=False,
)

# After (added Windows encoding parameters)
ci_result = subprocess.run(
    ci_cmd,
    cwd=cwd,
    capture_output=capture_output,
    text=True,
    encoding="utf-8", errors="replace",
    check=False,
)
...
return subprocess.run(
    install_cmd,
    cwd=cwd,
    capture_output=capture_output,
    text=True,
    encoding="utf-8", errors="replace",
    check=False,
)
```

**Call site conflict (`main.py:5843`):** Used upstream version (function call), discarding old inline code.

```python
# Final result (conflict location)
result = _run_npm_install_deterministic(
    npm,
    path,
    extra_args=("--silent", "--no-fund", "--no-audit", "--progress=false"),
)
```

---

### 2. hermes_cli/web_server.py

#### Conflict Cause

Upstream in commit `625c31fc` (`fix(tui): run built TUI with production React by default`) added `env.setdefault("NODE_ENV", "production")` to ensure the TUI runs with production-mode React.

Our 04-26 changes added `env["HERMES_PYTHON"] = sys.executable` to ensure the TUI's Node subprocess uses the same Python. Both changes were adjacent in the same function, causing a conflict.

#### Resolution

Both changes have independent value and are both retained, merged as:

**Modified location:** `hermes_cli/web_server.py:2331`

```python
# Final result (both changes merged)
env.setdefault("NODE_ENV", "production")

# Ensure the TUI's Node child_process spawns the *same* Python that
# runs the dashboard.  Without this, the TUI may pick up a different
# Python from PATH or VIRTUAL_ENV (e.g. conda base) that lacks the
# tui_gateway module.
env["HERMES_PYTHON"] = sys.executable

if resume:
    env["HERMES_TUI_RESUME"] = resume
```

---

## Upstream Important Changes (Windows-Related)

The following upstream commits from this merge are closely related to Windows adaptation or worth noting:

| Commit | Description | Impact |
|--------|-------------|--------|
| `34eb1aaa` | fix(update): use npm ci to stop rewriting package-lock | Introduced `_run_npm_install_deterministic`; we added encoding parameters inside it |
| `625c31fc` | fix(tui): run built TUI with production React by default | Added `NODE_ENV=production`, coexists with our `HERMES_PYTHON` |
| `eb28145f` | feat(approval): hardline blocklist for unrecoverable commands | `tools/approval.py` gained more dangerous command interceptions; auto-merged, our Windows patterns retained |
| `2e6699b3` | fix: strip leaked declare-x env dump from terminal output on macOS | `tools/environments/base.py` fixed terminal output leakage; auto-merged, our `_drain_windows` retained |
| `e63929d4` | Merge PR #15926: bb/tui-long-session-perf | TUI long session performance optimization; `tui_gateway/server.py` auto-merged, ephemeral session support retained |
| `a0fe73ba` | fix(cli): strip leaked bracketed-paste wrappers | `cli.py` fix; auto-merged |

---

## Windows Optimization Retention Confirmation

| Windows Patch | File | Status |
|---------------|------|--------|
| WSL bash detection (`_is_wsl_bash`) | `tools/environments/local.py` | ✅ Auto-merged, retained |
| Git Bash path detection priority | `tools/environments/local.py` | ✅ Auto-merged, retained |
| MSYS path conversion + dual-path storage | `tools/environments/local.py` | ✅ Auto-merged, retained |
| Windows pipe reading (`_drain_windows`) | `tools/environments/base.py` | ✅ Auto-merged, retained |
| Cross-platform helper library | `tools/platform_compat.py` | ✅ Auto-merged, retained |
| Dangerous command interception (`find /` etc.) | `tools/approval.py` | ✅ Auto-merged, retained |
| stdin/stdout/stderr UTF-8 reconfiguration | `tui_gateway/entry.py` | ✅ Auto-merged, retained |
| StdioTransport bypasses TextIOWrapper | `tui_gateway/transport.py` | ✅ Auto-merged, retained |
| slash_worker full UTF-8 reconfiguration | `tui_gateway/slash_worker.py` | ✅ Auto-merged, retained |
| ephemeral session support | `tui_gateway/server.py` | ✅ Auto-merged, retained |
| PID file encoding + taskkill encoding | `gateway/status.py` | ✅ Auto-merged, retained |
| ConPTY Windows backend | `hermes_cli/pty_bridge.py` | ✅ Auto-merged, retained |
| HERMES_PYTHON environment variable passing | `hermes_cli/web_server.py` | ✅ Manually resolved conflict, retained |
| npm subprocess UTF-8 encoding | `hermes_cli/main.py` | ✅ Manually resolved conflict, retained (moved into function definition) |
| 146 subprocess encoding fixes | 41 files | ✅ Auto-merged, retained |

---

## Commit History

| Commit | Description |
|--------|-------------|
| `4ec3fb7e` | Merge upstream/main into hermes/2026-04-27, preserve Windows compat patches |

---

## Operation Summary

The 04-27 work was a pure sync operation with no new Windows adaptation code. The core work was:

1. **Losslessly merged 251 upstream commits**: Feature updates include TUI long session performance optimization, npm ci deterministic install, kanban board, Slack slash commands, model directory remote manifests, etc.
2. **Resolved 2 conflicts**: Both were caused by upstream refactoring and our encoding fixes at the same location; resolved by retaining both sides' changes or migrating encoding parameters into the refactored functions
3. **All Windows optimizations fully retained**: All 15 Windows patches (including all 04-24 and 04-26 changes) lost none

---

> Merge baseline: hermes/2026-04-26 (9438c914) merged upstream/main (ee1a07f9)
> Merge commit: 4ec3fb7e
