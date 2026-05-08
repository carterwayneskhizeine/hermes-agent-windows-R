# Hermes Windows Adaptation Code Changes Summary

> Updated: 2026-05-07
> Baseline: Branch hermes/2026-04-30 (commit 2b475b761)
> Scope: Sync upstream main (49c3c2e0d), resolve 8 merge conflicts in 5 files, retain all Windows optimizations

---

## Operation Overview

Created `hermes/2026-05-07` from `hermes/2026-04-30`, merged the latest upstream `main` commits (545 commits, 538 non-merge commits), covering 610 files and +65,356 / -7,717 line changes. Manually resolved 8 conflicts in 5 files, all Windows adaptation patches fully retained.

---

## Merge Statistics

| Item | Count |
|------|-------|
| Upstream commits merged | 545 (including 7 merge commits) |
| Non-merge upstream commits | 538 |
| Changed files | 610 |
| Files with manually resolved conflicts | 5 (8 conflicts) |
| Windows optimizations lost | 0 |

---

## Conflict Resolution Details

### 1. hermes_cli/main.py (3 conflicts)

**Conflict cause:**
We added `encoding="utf-8", errors="replace"` to multiple `subprocess.run` calls (`systemctl is-active`, `systemctl show ... RestartUSec`, `systemctl show ... MainPID`) (Windows UTF-8 encoding fix). Upstream only had `capture_output=True, text=True, timeout=5`.

**Resolution:**
All adopted HEAD version, retaining UTF-8 encoding fix:

```python
result = subprocess.run(
    scope_cmd_ + ["is-active", svc_name_],
    capture_output=True, text=True,
    encoding="utf-8", errors="replace", timeout=5,
)
```

Note: These systemctl calls have no impact on Linux (UTF-8 by default), but retaining encoding parameters prevents regressions in cross-platform testing or WSL environments.

---

### 2. hermes_cli/profiles.py (1 conflict)

**Conflict cause:**
Upstream changed `subprocess.run(["which", name], ...)` to `subprocess.run(["which", canon], ...)` (fixed variable name consistency). Our version still used `name` but added UTF-8 encoding parameters.

**Resolution:**
Both accepted — used upstream's `canon` while retaining UTF-8 encoding parameters:

```python
result = subprocess.run(
    ["which", canon], capture_output=True, text=True,
    encoding="utf-8", errors="replace", timeout=5,
)
```

---

### 3. hermes_cli/pty_bridge.py (1 conflict)

**Conflict cause:**
We added the Windows ConPTY backend in 04-26 (`_PTY_BACKEND == "win"` branch calling `_WinPtyProcess.spawn`, passing `backend="win"` / `backend="posix"` to `cls.__init__`). Upstream added a `TERM` environment variable fallback (defaulting to `xterm-256color` when CI environment has no `TERM`), and changed `spawn_env = (os.environ.copy() if env is None else env.copy())` to a local copy.

**Resolution:**
Merged both sides' logic — TERM default value is applied before both backend branches, and both Windows / POSIX branches use the same `spawn_env`:

```python
spawn_env = (os.environ.copy() if env is None else env.copy())
if not spawn_env.get("TERM"):
    spawn_env["TERM"] = "xterm-256color"

if _PTY_BACKEND == "win":
    proc = _WinPtyProcess.spawn(
        list(argv), cwd=cwd, env=spawn_env, dimensions=(rows, cols),
    )
    return cls(proc, backend="win")
else:
    proc = ptyprocess.PtyProcess.spawn(  # type: ignore[union-attr]
        list(argv), cwd=cwd, env=spawn_env, dimensions=(rows, cols),
    )
    return cls(proc, backend="posix")
```

---

### 4. tools/environments/local.py (1 conflict)

**Conflict cause:**
We added Windows MSYS → Windows path conversion in 04-24 (`_IS_WINDOWS` branch calling `msys_path_to_windows(self.cwd)` to get `popen_cwd`). Upstream introduced a cwd invalidation auto-recovery mechanism (`_resolve_safe_cwd(self.cwd)`, falling back to the most recent existing ancestor directory, issue #17558) — but `os.path.isdir` on Windows cannot resolve MSYS-form paths (`/d/...`), so directly calling `_resolve_safe_cwd(self.cwd)` would incorrectly judge it as non-existent and jump to tempdir, breaking Windows terminal commands.

**Resolution:**
Adjusted the order — first convert `self.cwd` to Windows form to get `popen_cwd`, then use `popen_cwd` for existence checking; after recovery, write `self.cwd` back in MSYS form to maintain consistency:

```python
if _IS_WINDOWS:
    from tools.platform_compat import msys_path_to_windows, windows_path_to_msys
    popen_cwd = msys_path_to_windows(self.cwd)
else:
    popen_cwd = self.cwd

safe_popen_cwd = _resolve_safe_cwd(popen_cwd)
if safe_popen_cwd != popen_cwd:
    logger.warning(
        "LocalEnvironment cwd %r is missing on disk; "
        "falling back to %r so terminal commands keep working.",
        self.cwd, safe_popen_cwd,
    )
    popen_cwd = safe_popen_cwd
    self.cwd = (
        windows_path_to_msys(safe_popen_cwd) if _IS_WINDOWS else safe_popen_cwd
    )
```

This allows cwd invalidation recovery to trigger correctly on Windows, while the Windows path conversion patch is fully retained.

---

### 5. ui-tui/package-lock.json (2 conflicts)

**Conflict cause:**
Local `npm install` replaced the `resolved` field for several dependencies from `registry.npmjs.org` to `registry.npmmirror.com` (npm mirror). Upstream lock file continues to use the official registry.

**Resolution:**
Adopted upstream version (`git checkout --theirs`). The `integrity` hashes are consistent and artifacts are identical; using the official registry is better for cross-developer collaboration. Local mirror acceleration can be configured via `~/.npmrc` as needed.

---

## Upstream Important Changes

| Direction | Description |
|-----------|-------------|
| Checkpoints v2 | Single storage rewrite + true pruning + disk capacity protection (`a0fedfbb1`) |
| SearXNG search backend | Native SearXNG integration, separated search / extract by capability (`5c906d702`, `cd2cbc73b`) |
| Lightpanda browser engine | New Lightpanda backend with automatic Chrome fallback (`395dbcc87`, `3ebdd2644`, `629d8b843`) |
| Voice push-to-talk fix | TUI voice walkie-talkie restored (`04cf4788c`) |
| Multi-language support | Added Turkish, Ukrainian, French locales (`985133852`, `c4b287ba5`, `0d41e94ca`) |
| Kanban scheduling enhancements | task_runs summary, dependency cascading, max concurrency limit, subtask dispatch guard (multiple commits) |
| Gateway restart strategy | Per-platform `gateway_restart_notification` config + systemd restart readiness wait (`b71f80e6c`, `d797755a1`, `7df611519`) |
| TUI startup banner collapsible | skills / system prompt / MCP sections collapsible and expandable (`d78c34928`) |
| TUI system message folding | Long system messages collapsed by default + expand button (`68162eb18`) |
| Auth fallback | Falls back to global `auth.json` when provider is missing (`33bf5f629`) |
| typecheck CI | ruff / ty enabled, typecheck warnings only (`63c51d896`, `9627ee70e`) |
| Open WebUI SSE optimization | api_server SSE token batching + error handling (`3188e63b0`) |
| Hindsight append adaptive | Detect `update_mode='append'` support + cross-process deduplication (`3082fa082`) |
| WSL2 documentation expansion | filesystem / networking / services / pitfalls comprehensive update (`90a7adcb2`) |
| Model directory | Added grok-4.3 / deepseek-v4-pro and other new models |
| Discord rate limiting | Narrowed catch scope + sync state migration to gateway/ (`5a3cadf6e`) |
| Feishu topic replies | Keep replies in original topic thread (`441ef75d1`) |
| Shop-app skill | New personal shopping assistant skill (optional) (`b045e7a2b`) |
| TUI multiple stability fixes | Scrollbar stability, virtual offset fix, FaceTicker drift fix, status bar jitter reduction |

---

## Windows Optimization Retention Confirmation

| Windows Patch | File | Status |
|---------------|------|--------|
| WSL bash detection (`_is_wsl_bash`) | `tools/environments/local.py` | ✅ Auto-merged, retained |
| Git Bash path detection priority | `tools/environments/local.py` | ✅ Auto-merged, retained |
| MSYS path conversion + dual-path storage + `_resolve_safe_cwd` integration | `tools/environments/local.py` | ✅ Manually resolved conflict, retained (merged with `_resolve_safe_cwd`) |
| Windows pipe reading (`_drain_windows`) | `tools/environments/base.py` | ✅ Auto-merged, retained |
| Cross-platform helper library | `tools/platform_compat.py` | ✅ Auto-merged, retained |
| Dangerous command interception (`find /` etc.) | `tools/approval.py` | ✅ Auto-merged, retained |
| stdin/stdout/stderr UTF-8 reconfiguration | `tui_gateway/entry.py` | ✅ Auto-merged, retained |
| StdioTransport bypasses TextIOWrapper | `tui_gateway/transport.py` | ✅ Auto-merged, retained |
| slash_worker full UTF-8 reconfiguration | `tui_gateway/slash_worker.py` | ✅ Auto-merged, retained |
| PID file encoding + taskkill encoding | `gateway/status.py` | ✅ Auto-merged, retained |
| ConPTY Windows backend | `hermes_cli/pty_bridge.py` | ✅ Manually resolved conflict, retained (merged TERM default value) |
| HERMES_PYTHON environment variable passing | `hermes_cli/web_server.py` / `main.py` | ✅ Auto-merged, retained |
| npm subprocess UTF-8 encoding | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| main() UTF-8 reconfiguration | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| systemctl subprocess UTF-8 encoding (3 locations) | `hermes_cli/main.py` | ✅ Manually resolved conflict, retained |
| profiles.py `which` UTF-8 encoding | `hermes_cli/profiles.py` | ✅ Manually resolved conflict, retained (adopted upstream `canon` variable) |
| plugins install/pull UTF-8 encoding | `hermes_cli/plugins_cmd.py` | ✅ Auto-merged, retained (still in shared functions) |
| 146 subprocess encoding fixes | 41 files | ✅ Auto-merged, retained |

---

## Commit History

| Commit | Description |
|--------|-------------|
| `c86d74075` | Merge upstream/main into hermes/2026-05-07, preserve Windows compat patches |

---

## Operation Summary

The 05-07 work was a pure sync operation with no new Windows adaptation code. The core work was:

1. **Losslessly merged 545 upstream commits**: Feature updates include Checkpoints v2, SearXNG search backend, Lightpanda browser engine, TUI startup banner folding, Kanban scheduling enhancements, multi-language support (tr/uk/fr), Open WebUI SSE optimization, etc.
2. **Resolved 8 conflicts in 5 files**:
   - `main.py` (3 locations) — retained UTF-8 encoding parameters for systemctl calls
   - `profiles.py` (1 location) — adopted upstream `canon` variable while retaining UTF-8 encoding
   - `pty_bridge.py` (1 location) — merged ConPTY backend dispatch with TERM default value fallback
   - `local.py` (1 location) — adjusted cwd conversion order so `_resolve_safe_cwd` works correctly on Windows
   - `package-lock.json` (2 locations) — adopted upstream official registry URLs
3. **All Windows optimizations fully retained**: All 18 Windows patches (including all 04-24, 04-26, 04-27, 04-29, 04-30, 05-01 changes) lost none

---

> Merge baseline: hermes/2026-04-30 (2b475b761) merged upstream main (49c3c2e0d)
> Merge commit: c86d74075 (on hermes/2026-05-07 branch)
