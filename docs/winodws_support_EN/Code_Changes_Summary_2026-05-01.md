# Hermes Windows Adaptation Code Changes Summary

> Updated: 2026-05-01
> Baseline: Branch hermes/2026-04-30 (commit a164f2b85)
> Scope: Sync upstream main (c5b4c4816), resolve 3 merge conflicts in 2 files, retain all Windows optimizations

---

## Operation Overview

Merged the latest upstream `main` commits (146 commits, 137 non-merge commits) into the existing `hermes/2026-04-30` branch state, covering 250 files and +36,650 / -1,900 line changes. Resolved 3 conflicts in 2 files, all Windows adaptation patches fully retained.

---

## Merge Statistics

| Item | Count |
|------|-------|
| Upstream commits merged | 146 (including 9 merge commits) |
| Non-merge upstream commits | 137 |
| Changed files | 250 |
| Files with manually resolved conflicts | 2 (3 conflicts) |
| Windows optimizations lost | 0 |

---

## Conflict Resolution Details

### 1. hermes_cli/plugins_cmd.py (2 conflicts)

#### Conflict 1: `cmd_install` Function

**Conflict cause:**
Upstream extracted git clone install logic (including manifest reading, path sanitization, manifest_version checking, existing plugin overwrite) into a standalone function `_install_plugin_core()`, and added `plugin.yml` format support. Our version added `encoding="utf-8", errors="replace"` to `subprocess.run` (Windows UTF-8 encoding fix).

**Resolution:**
Adopted upstream's refactoring (`_install_plugin_core` function + `PluginOperationError` exception system), adding Windows UTF-8 encoding fix inside the upstream shared function:

```python
# subprocess call in _install_plugin_core
result = subprocess.run(
    ["git", "clone", "--depth", "1", git_url, str(tmp_target)],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=60,
)
```

Also accepted upstream's new `plugin.yml` format support:

```python
has_yaml = (target / "plugin.yaml").exists() or (target / "plugin.yml").exists()
```

#### Conflict 2: `cmd_update` Function

**Conflict cause:**
Upstream extracted git pull logic into a shared function `_git_pull_plugin_dir(target)`. Our version added `encoding="utf-8", errors="replace"` to `subprocess.run`.

**Resolution:**
Adopted upstream's shared function call, adding Windows UTF-8 encoding fix inside `_git_pull_plugin_dir`:

```python
def _git_pull_plugin_dir(target: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(target),
        )
```

---

### 2. tui_gateway/server.py (1 conflict)

**Conflict cause:**
Our 04-26/04-30 changes added an `ephemeral` check inside `_build()` of `_start_agent_build` (`if db is not None and not current.get("ephemeral"):`) and `pending_title` handling logic. Upstream introduced a complete lazy session creation mechanism (`c5b4c4816` — defer DB row until first message), replacing DB creation logic in `_build()` with a comment:

```python
# Session DB row deferred to first run_conversation() call.
# pending_title applied post-first-message (see cli.exec handler).
```

**Resolution:**
Adopted upstream's approach. Upstream's lazy session creation returns `"lazy": True` on `session.create`, deferring the DB row to `run_conversation()` (first message). This is more general than our `ephemeral` check — all sessions delay DB row creation, and ephemeral sessions that never send a message naturally won't be written to the DB.

Our `ephemeral` check and `pending_title` handling logic have been superseded by upstream's more complete approach, requiring no additional patches.

---

## Upstream Important Changes

| Direction | Description |
|-----------|-------------|
| Lazy session creation | `session.create` returns lightweight session, DB row deferred to first message (`c5b4c4816`) |
| /goal persistent objectives | Cross-turn persistent goals (Ralph loop) (`265bd59c1`) |
| Kanban collaborative board | Multi-profile persistent board + dashboard plugin (`c86842546`) |
| Tool loop guardrails | Tool call loop detection and warning (`58b89965c`, `0704589ce`) |
| TUI model picker refactoring | Shows all providers, inline API key config, `d` key disconnect (`26f7f6850`) |
| ACP /steer + /queue | Idle session steering and queue slash commands (`e27b0b765`) |
| ACP Windows cwd normalization | Auto-convert Windows drive paths under WSL (`ec1443b9f`) |
| Feishu bot admission policy | Operator-configurable bot join and @ mention policy (`b94cb8e2c`) |
| hermes update --yes | Update command skipping interactive prompts (`50c046331`) |
| Gateway busy confirmation configurable | `busy_ack_enabled` config option (`2b512cbca`) |
| Dashboard analytics sorting | Interactive column sorting (`226fd79c8`) |
| Here-now + Shopify skills | New productivity skills |
| Atomic write + Windows lock fix | Gateway restart marker atomic write, fixes Windows lock conflicts (`1ef9e8854`) |
| Moonshot schema fix | anyOf branch nullable/enum cleanup (`9ca72a69a`, `2af8b8ff3`) |
| DeepSeek V4 Pro thinking | Non-empty reasoning_content placeholder (`bfb704684`) |

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
| ephemeral session → lazy session | `tui_gateway/server.py` | ✅ Upstream approach replaces (more general) |
| PID file encoding + taskkill encoding | `gateway/status.py` | ✅ Auto-merged, retained |
| ConPTY Windows backend | `hermes_cli/pty_bridge.py` | ✅ Auto-merged, retained |
| HERMES_PYTHON environment variable passing | `hermes_cli/web_server.py` | ✅ Auto-merged, retained |
| npm subprocess UTF-8 encoding | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| main() UTF-8 reconfiguration | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| 146 subprocess encoding fixes | 41 files | ✅ Auto-merged, retained |
| plugins install/pull UTF-8 encoding | `hermes_cli/plugins_cmd.py` | ✅ Manually resolved conflict, retained (moved into shared functions) |

### Upstream New Windows-Related Fixes

| Patch | File | Description |
|-------|------|-------------|
| ACP WSL cwd normalization | `acp_adapter/session.py` | `_win_path_to_wsl()` + `_translate_acp_cwd()`, auto-merged |
| Gateway atomic write + Windows lock fix | `gateway/run.py` | Restart marker atomic write, avoids Windows file lock conflicts, auto-merged |

---

## Commit History

| Commit | Description |
|--------|-------------|
| `ea7ca5aa9` | Merge upstream/main into hermes/2026-04-30, preserve Windows compat patches |

---

## Operation Summary

The 05-01 work was a pure sync operation with no new Windows adaptation code. The core work was:

1. **Losslessly merged 146 upstream commits**: Feature updates include lazy session creation, /goal persistent objectives, Kanban collaborative board, tool loop guardrails, TUI model picker refactoring, ACP /steer + /queue, ACP Windows cwd normalization, etc.
2. **Resolved 3 conflicts in 2 files**: `plugins_cmd.py` adopted upstream `_install_plugin_core` / `_git_pull_plugin_dir` refactoring and added UTF-8 encoding fix; `server.py` adopted upstream lazy session creation replacing our `ephemeral` check
3. **All Windows optimizations fully retained**: All 17 Windows patches (including all 04-24, 04-26, 04-27, 04-29, 04-30 changes) lost none; additionally 2 new upstream Windows fixes (ACP WSL cwd normalization, Gateway atomic write)

---

> Merge baseline: hermes/2026-04-30 (a164f2b85) merged upstream main (c5b4c4816)
> Merge commit: ea7ca5aa9
