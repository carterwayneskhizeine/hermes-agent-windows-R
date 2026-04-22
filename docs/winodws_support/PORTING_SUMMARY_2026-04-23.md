# Windows 适配移植总结 — 2026-04-23

把 `D:\Code\hermes-agent-windows`（旧 fork）里有但新版 `2026.4.16` 缺失的 Windows 适配补齐的一次实施记录。下次复盘时从这份文档开始。

---

## 1. 背景

新版 `hermes-agent-2026.4.16` 从上游合并过来时，已经继承了大部分关键的 Windows 兼容代码（`_IS_WINDOWS` 守卫、`_find_bash` / `HERMES_GIT_BASH_PATH` 探测、preexec_fn 守卫、PTY 双分支等）。

但仍有两类缺口：

1. **多处未守卫的 `os.kill(pid, 0)` 存活检查** —— 在 Windows 上会抛 `WinError 11/87`。
2. **未守卫的 `signal.SIGKILL`** —— Windows 上 `SIGKILL` 不存在，`hermes gateway stop` 强杀路径会直接 AttributeError。
3. **没有集中式跨平台 helper 模块**，每个文件自己判断，代码重复且容易漏。

---

## 2. 实际做了什么

### 2.1 新增文件

| 文件 | 作用 |
|------|------|
| `tools/platform_compat.py` | 跨平台 helper 单一入口（`pid_alive` / `terminate_pid` / `get_detached_popen_kwargs` / `shell_join` / `file_lock` / `get_host_temp_dir`） |
| `clear.ps1` | Windows 清理脚本（移除 `%LOCALAPPDATA%\hermes`、`HERMES_*` 环境变量、PATH 条目）。已从旧 fork 移植并改用 `$env:LOCALAPPDATA`，去掉硬编码用户名 |
| `WINDOWS_SUPPORT.md` | Windows 运行模型、Git Bash 探测顺序、依赖清单、已知限制 |
| `docs/winodws_support/PORTING_SUMMARY_2026-04-23.md` | 本文档 |

### 2.2 修改文件

| 文件 | 修改内容 | 原因 |
|------|----------|------|
| `gateway/status.py` | `_pid_alive` 和 `terminate_pid` 改为委托给 `tools.platform_compat` | 去重，单一数据源 |
| `hermes_cli/gateway.py` | 2 处 `os.kill(pid, 0)` → `pid_alive()` | Windows 存活检查 |
| `hermes_cli/profiles.py` | 2 处 `os.kill(pid, 0)` → `pid_alive()`；1 处 `os.kill(pid, SIGKILL)` → `terminate_pid(force=True)` | 修 Windows `SIGKILL` 不存在的 bug |
| `tools/browser_tool.py` | 1 处 `os.kill(daemon_pid, 0)` → `pid_alive()` | 浏览器守护进程存活检查 |
| `tools/process_registry.py` | 1 处 `os.kill(pid, 0)` → `pid_alive()` | 后台进程存活检查 |
| `gateway/run.py` | 1 处 `os.kill(existing_pid, 0)` → `pid_alive()` | gateway 替换旧实例时的存活检查 |
| `tests/gateway/test_status.py` | 把 `monkeypatch.setattr(status.os, "kill", …)` 迁到 `tools.platform_compat.pid_alive` / 内部 `subprocess.run` | mock 点跟着实现走 |
| `tests/hermes_cli/test_profiles.py` | 同上 | 同上 |

### 2.3 `platform_compat.py` API 速查

```python
from tools.platform_compat import (
    pid_alive,                  # bool — 替代 os.kill(pid, 0)，Windows 用 psutil/tasklist
    terminate_pid,              # None — force=True 时 POSIX 用 SIGKILL，Windows 用 taskkill /T /F
    get_detached_popen_kwargs,  # dict — POSIX: {start_new_session}; Windows: {creationflags}
    shell_join,                 # str  — list2cmdline on Windows, shlex.quote on POSIX
    file_lock,                  # ctx  — fcntl.flock 或 msvcrt.locking
    get_host_temp_dir,          # Path — $TEMP/hermes
    get_host_temp_path,         # Path — $TEMP/hermes/<name>
    _IS_WINDOWS,                # bool
)
```

---

## 3. 新版中**已经存在、无需改**的部分

避免下次重复检查：

- `_IS_WINDOWS` 平台守卫：`tools/environments/local.py`、`tools/process_registry.py`、`tools/code_execution_tool.py`、`gateway/platforms/whatsapp.py` 全部已有
- `_find_bash` + `HERMES_GIT_BASH_PATH` 探测：`tools/environments/local.py:141`
- `preexec_fn=None if _IS_WINDOWS else os.setsid`：所有 Popen 调用
- PTY 双分支（`winpty` / `ptyprocess`）：`tools/process_registry.py:317`
- Windows 兼容测试：`tests/tools/test_windows_compat.py`（12 个守卫检查全部通过）
- `signal.SIGUSR1` 守卫：`hermes_cli/gateway.py:149` 已经用 `hasattr(signal, "SIGUSR1")` 提前返回

---

## 4. 验证方式

```powershell
# 1. 单元测试
.\venv\Scripts\python.exe -m pytest tests/tools/test_windows_compat.py `
    tests/gateway/test_status.py tests/hermes_cli/test_profiles.py -v
# 预期：113 passed

# 2. platform_compat 冒烟测试
.\venv\Scripts\python.exe -c "from tools.platform_compat import pid_alive, get_detached_popen_kwargs; import os; print(pid_alive(os.getpid()), get_detached_popen_kwargs())"
# 预期：True {'creationflags': 520}

# 3. 端到端
hermes gateway run
# 预期：正常启动，Ctrl+C 可优雅退出
```

---

## 5. **没做**的部分（明确边界）

以下项在旧 fork 里有，本次**主动跳过**，下次要不要做参考这里的判断：

| 跳过项 | 理由 |
|--------|------|
| `scripts/install.ps1` 一键安装脚本 | 用户用 venv 开发模式，不走 `%LOCALAPPDATA%\hermes` 安装 |
| `packaging/windows-installer/`（GUI/Console EXE） | 面向普通用户分发才需要，开发阶段不用 |
| Windows 路径规范化 helper（`D:\…` ↔ `/d/…`） | 新版代码没有实际路径混用现场；`hermes gateway run` 已跑通 |
| PowerShell 调用 helper | Hermes 自身代码不从 bash 拼 PowerShell one-liner；旧 fork 报告的痛点主要发生在**调用方 AI 会话**的 shell bridge，那不是 Hermes 的问题 |
| `hermes web` + ChatPage + 中文界面 | 用户明确表示 UI 增量不做 |
| `hermes doctor` Windows 预检加强 | 当前机器依赖齐全；换机器再补 |

---

## 6. 如果下次要继续改

**优先级排序（从高到低）：**

1. 真遇到 Windows 特定运行时 bug 时，**先看 `tools/platform_compat.py` 是否需要新加 helper**，再改业务代码
2. 有用户反馈 `hermes doctor` 在 Windows 上不够清晰时，才补 Windows 预检
3. 要正式对外分发 Windows 版时，再考虑回迁 `install.ps1` 和 installer

**不要做的：**

- 不要直接复制旧 fork 的整个文件。文件整体 diff 巨大（`cli.py` 20k 行差异、`terminal_tool.py` 3.5k 行差异），**上游已大量演进**，照搬会破坏新版本。永远做**定向小补丁**。
- 不要在业务模块里新增 `_IS_WINDOWS` 分支，优先用 `platform_compat`。

---

## 7. 相关文档索引

- `docs/winodws_/HERMES_WINDOWS_ISSUE_REPORT.md` — 上一次会话踩到的环境问题（注：根因不是 Hermes 代码，是调用方 AI 会话的 shell bridge）
- `docs/winodws_/WINDOWS_OPTIMIZATIONS_CHECKLIST.md` — 旧 fork 完整适配清单
- `docs/winodws_/WINDOWS_PATCH_PORTING_TODO.md` — 原始 TODO（本次实施后很多项已废弃或降级）
- `WINDOWS_SUPPORT.md`（repo 根） — 面向使用者的 Windows 运行说明
