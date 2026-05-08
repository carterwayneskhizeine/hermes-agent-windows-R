# Hermes Windows Adaptation Code Changes Summary

> Updated: 2026-04-29
> Baseline: Branch hermes/2026-04-27 (commit 4237f325)
> Scope: Sync 266 upstream commits, resolve 2 merge conflicts, retain all Windows optimizations

---

## Operation Overview

Created `hermes/2026-04-29` from `hermes/2026-04-27`, executed `git merge upstream/main` to bring in 266 new upstream NousResearch/hermes-agent commits (up to `1d4218be`), resolved 2 conflicts, all Windows adaptation patches fully retained.

Additionally, after the merge, `npm run build` produced 112 TypeScript errors (because `@nous-research/ui` 0.4.0 was a transitional breaking version that deleted many APIs). After running `npm install`, `package-lock.json` was locked to the latest stable version **0.10.0**, which restored all APIs and is fully compatible with existing code, restoring the build to normal.

---

## Merge Statistics

| Item | Count |
|------|-------|
| Upstream commits merged | 266 |
| Files auto-merged successfully | All except 2 |
| Files with manually resolved conflicts | 2 |
| Windows optimizations lost | 0 |

---

## Conflict Resolution Details

### 1. .gitignore

#### Conflict Cause

Upstream added a `models-dev-upstream/` ignore entry; we added `.claude/settings.local.json` and `.claude/skills/sync-repos/SKILL.md` ignore entries in 04-27. Both were at the same location at the end of the file.

#### Resolution

Both sides have independent value and are both retained:

```gitignore
# Final result (both changes merged)
.claude/settings.local.json
.claude/skills/sync-repos/SKILL.md
models-dev-upstream/
```

---

### 2. tui_gateway/transport.py

#### Conflict Cause

Upstream in commit `1e326c68` (`fix(tui-gateway): harden stdio transport against half-closed pipes + SIGTERM races`) substantially refactored `StdioTransport.write()`:

- Added `_PEER_GONE_ERRNOS` constant, subdividing `OSError` errno
- Added `_DISABLE_FLUSH` switch to prevent flush hanging on half-closed pipes
- Split `BrokenPipeError` into three handling cases: `BrokenPipeError` / `ValueError("closed file")` / `OSError`
- Write and flush each handle exceptions independently

Our 04-26 changes bypassed `TextIOWrapper` and wrote UTF-8 bytes directly to the underlying `buffer` to fix GBK encoding misconversion on CJK Windows. Both changes conflicted inside the same function body.

#### Resolution

Merged upstream's robust error handling framework with our Windows UTF-8 buffer bypass:

**Modified location:** `tui_gateway/transport.py` (`StdioTransport.write()` method)

```python
# Final result (both changes merged)
with self._lock:
    stream = self._stream_getter()
    # On CJK Windows the TextIOWrapper may use GBK; bypass it by
    # writing UTF-8 bytes directly to the underlying buffer so
    # Chinese characters are never mis-encoded.
    buf = getattr(stream, "buffer", None)
    try:
        if buf is not None:
            buf.write(line.encode("utf-8"))
        else:
            stream.write(line)
    except BrokenPipeError:
        return False
    except ValueError as e:
        if isinstance(e, UnicodeEncodeError) or "closed file" not in str(e):
            raise
        return False
    except OSError as e:
        if e.errno not in _PEER_GONE_ERRNOS:
            raise
        logger.debug("StdioTransport write peer gone: %s", e)
        return False

    if not _DISABLE_FLUSH:
        flush_target = buf if buf is not None else stream
        try:
            flush_target.flush()
        except BrokenPipeError:
            return False
        except ValueError as e:
            if isinstance(e, UnicodeEncodeError) or "closed file" not in str(e):
                raise
            return False
        except OSError as e:
            if e.errno not in _PEER_GONE_ERRNOS:
                raise
            logger.debug("StdioTransport flush peer gone: %s", e)
            return False

return True
```

**Strategy:** The flush also preferentially uses the underlying `buf` (`flush_target = buf if buf is not None else stream`), ensuring the Windows UTF-8 bypass takes effect on the flush path as well.

---

## Build Fix: @nous-research/ui Upgraded to 0.10.0

#### Problem

After merging, `npm run build` reported 112 TypeScript errors, because the lock file pointed to the transitional breaking version 0.4.0, which deleted many APIs:

- **Missing exports**: `ListItem`, `Spinner`, `Select`, `SelectOption`, `Switch`, `FilterGroup`, `Segmented`, `Tabs`, `TabsList`, `TabsTrigger`
- **Button props removed**: `ghost`, `size`, `destructive`, `outlined`
- **Badge props removed**: `tone`

#### Root Cause

0.4.0 was an intermediate transitional version of the upstream UI library that broke backward compatibility. The latest stable version **0.10.0** has restored all the above APIs.

#### Resolution

Ran `npm install` in the `web/` directory; `package-lock.json` was re-resolved and locked to the latest stable version **0.10.0**. No TypeScript source code changes needed; build restored to normal (`✓ built in 8.50s`, 0 TS errors).

---

## Upstream Important Changes (Windows-Related)

| Commit | Description | Impact |
|--------|-------------|--------|
| `1e326c68` | fix(tui-gateway): harden stdio transport against half-closed pipes + SIGTERM races | Conflicted with our GBK bypass; manually merged retaining both sides |
| `8c892c14` | refactor(redact): canonical mask_secret helper; fix status.py DIM drift | `gateway/status.py` changed; auto-merged, our PID/taskkill encoding fixes retained |
| `cd7150a1` | perf(approval): precompile DANGEROUS_PATTERNS and HARDLINE_PATTERNS | `tools/approval.py` performance optimization; auto-merged, our Windows `find /` patterns retained |
| `413ee1a2` | feat(computer-use): background focus-safe backend | New computer-use feature; does not affect Windows patches |

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
| StdioTransport bypasses TextIOWrapper | `tui_gateway/transport.py` | ✅ Manually resolved conflict, retained (merged with upstream new error handling) |
| slash_worker full UTF-8 reconfiguration | `tui_gateway/slash_worker.py` | ✅ Auto-merged, retained |
| ephemeral session support | `tui_gateway/server.py` | ✅ Auto-merged, retained |
| PID file encoding + taskkill encoding | `gateway/status.py` | ✅ Auto-merged, retained |
| ConPTY Windows backend | `hermes_cli/pty_bridge.py` | ✅ Auto-merged, retained |
| HERMES_PYTHON environment variable passing | `hermes_cli/web_server.py` | ✅ Auto-merged, retained |
| npm subprocess UTF-8 encoding | `hermes_cli/main.py` | ✅ Auto-merged, retained |
| 146 subprocess encoding fixes | 41 files | ✅ Auto-merged, retained |

---

## Commit History

| Commit | Description |
|--------|-------------|
| `d9443ccc` | Merge upstream/main into hermes/2026-04-29, preserve Windows compat patches |

---

## Operation Summary

The 04-29 work was a pure sync operation with no new Windows adaptation code. The core work was:

1. **Losslessly merged 266 upstream commits**: Feature updates include TUI paste watchdog stability fix, stdio transport half-closed pipe hardening, review proactive update bias, approval precompilation performance optimization, light-terminal auto-detection, pluggable busy-indicator styles, etc.
2. **Resolved 2 conflicts**: `.gitignore` retained both sides' ignore entries; `tui_gateway/transport.py` fully merged upstream's robust error handling with Windows UTF-8 buffer bypass
3. **Fixed npm build**: Upgraded `@nous-research/ui` from transitional version 0.4.0 to latest stable 0.10.0, eliminated 112 TypeScript compile errors without any source code changes
4. **All Windows optimizations fully retained**: All 15 Windows patches (including all 04-24, 04-26, 04-27 changes) lost none

---

> Merge baseline: hermes/2026-04-27 (4237f325) merged upstream/main (1d4218be)
> Merge commit: d9443ccc
