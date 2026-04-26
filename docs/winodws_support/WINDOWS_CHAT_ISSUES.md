# Windows Dashboard Chat 功能修复记录

> 环境信息：Windows 11 Pro, Python 3.12 (native win32), 系统区域编码 cp936 (GBK)
>
> 日期：2026-04-26

## 背景

`hermes dashboard --tui` 的 `/chat` 页面在 Windows 上完全不可用。原始代码仅支持 POSIX（通过 WSL），存在 PTY 不可用、GBK 编码崩溃、信号缺失等多个问题。

## 修复概览

共修改 **8 个文件**，涉及 PTY 后端替换、编码修复、信号兼容、Python 路径解析 4 类问题。

---

## 1. PTY 后端：pywinpty 替代 ptyprocess（核心改动）

**文件：** `hermes_cli/pty_bridge.py`

**问题：** 原代码在 `sys.platform == "win32"` 时直接抛出 `PtyUnavailableError`，Windows 无法创建伪终端。

**修复：** 引入 `pywinpty`（Windows ConPTY 的 Python 绑定），通过 `_PTY_BACKEND` 标志在导入时选择后端：

```
win32  → pywinpty (ConPTY)
posix  → ptyprocess (openpty)
```

`PtyBridge` 类保持公开 API 不变，内部按平台分支：

| 方法 | POSIX (ptyprocess) | Windows (pywinpty) |
|------|-------------------|-------------------|
| `spawn()` | `ptyprocess.PtyProcess.spawn()` | `winpty.ptyprocess.PtyProcess.spawn()` |
| `read()` | `select.select()` + `os.read()` | `socket.settimeout()` + `proc.read()`，str→bytes |
| `write()` | `os.write()` 循环处理 short write | `proc.write(str)`，bytes→str |
| `resize()` | `fcntl.ioctl(TIOCSWINSZ)` | `proc.setwinsize(rows, cols)` |
| `close()` | SIGHUP → SIGTERM → SIGKILL 升级 | `proc.terminate(force=True)` |

pywinpty 的 `read()` 返回 str，通过 `.encode("utf-8")` 转回 bytes 以匹配 web_server 的 `ws.send_bytes()` 契约。read 的超时通过内部 socket 的 `settimeout()` 实现。

---

## 2. GBK 编码修复（6 处）

Windows 中文系统的 `locale.getpreferredencoding()` 返回 `cp936` (GBK)，Python 在以下场景默认使用 GBK，遇到 UTF-8 内容时崩溃。

### 2a. gateway 子进程的 stdin/stdout

**文件：** `tui_gateway/server.py` — `_SlashWorker.__init__`

```python
# 修复前
subprocess.Popen(argv, text=True, ...)

# 修复后
subprocess.Popen(argv, text=True, encoding="utf-8", errors="replace", ...)
```

### 2b. npm install / npm run build 子进程

**文件：** `hermes_cli/main.py` — `_make_tui_argv()`

两处 `subprocess.run(text=True)` 均添加 `encoding="utf-8", errors="replace"`。

### 2c. plugin.yaml 解析

**文件：** `hermes_cli/plugins.py` — `_parse_manifest()`

```python
manifest_file.read_text()  →  manifest_file.read_text(encoding="utf-8")
```

报错信息：`Failed to parse plugins/disk-cleanup/plugin.yaml: 'gbk' codec can't decode byte 0x94`

### 2d. PID 文件读取

**文件：** `gateway/status.py` — `_read_pid_record()`

```python
pid_path.read_text()  →  pid_path.read_text(encoding="utf-8")
```

同时包裹 `try/except PermissionError`，修复 Windows 文件锁导致的权限错误。

### 2e. print() 输出到终端

**文件：** `hermes_cli/main.py` — `main()` 入口

```python
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding="utf-8", errors="replace")
```

解决 `print("  ✓ Web UI built")` 中 `✓` (U+2713) 在 GBK 终端的 `UnicodeEncodeError`。

### 2f. gateway JSON-RPC 输出（最深层）

**文件：** `tui_gateway/transport.py` — `StdioTransport.write()`

```python
# 修复前
stream.write(line)          # TextIOWrapper 用 GBK 编码，遇到 ⚕ (U+2695) 崩溃

# 修复后
buf = stream.buffer         # 直接写底层 buffer
buf.write(line.encode("utf-8"))
```

`reconfigure()` 在 pipe 环境下不生效（`server.py` 在 import 时已将 `sys.stdout` 重定向为 `sys.stderr`），因此改为直接操作 `stream.buffer` 写入 bytes。

**文件：** `tui_gateway/entry.py` — `main()`

对 `_real_stdout`（`server.py` 在 stdout 重定向前保存的引用）执行 `reconfigure(encoding="utf-8")`，作为额外保障。

---

## 3. POSIX 信号缺失

**文件：** `tui_gateway/entry.py`

**问题：** `signal.SIGPIPE` 和 `signal.SIGHUP` 在 Windows 上不存在，导致 `AttributeError`，gateway 启动即崩溃。

```python
# 修复前
signal.signal(signal.SIGPIPE, signal.SIG_IGN)   # AttributeError on Windows
signal.signal(signal.SIGHUP, _log_signal)        # AttributeError on Windows

# 修复后
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
signal.signal(signal.SIGTERM, _log_signal)       # SIGTERM 在 Windows 上存在
if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, _log_signal)
```

---

## 4. Python 路径解析

**文件：** `hermes_cli/web_server.py` — `_resolve_chat_argv()`

**问题：** TUI Node 进程通过 `child_process.spawn` 启动 `python -m tui_gateway.entry`，用 `VIRTUAL_ENV` 环境变量解析 Python 路径。当 `VIRTUAL_ENV` 指向 conda base 环境而非项目 venv 时，Node 找到的 Python 没有 `tui_gateway` 模块，gateway 启动失败。

```python
# 修复：始终构建 env dict 并指定 HERMES_PYTHON
env = os.environ.copy()
env["HERMES_PYTHON"] = sys.executable  # Node 的 resolvePython() 优先使用此变量
```

---

## 修改文件索引

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `hermes_cli/pty_bridge.py` | 核心改动 | 添加 pywinpty (ConPTY) Windows 后端 |
| `hermes_cli/web_server.py` | 功能修复 | 设置 `HERMES_PYTHON` 确保子进程找到正确 Python |
| `hermes_cli/main.py` | 编码修复 | stdout UTF-8 reconfigure + npm subprocess encoding |
| `hermes_cli/plugins.py` | 编码修复 | plugin.yaml `read_text(encoding="utf-8")` |
| `tui_gateway/entry.py` | 兼容性修复 | SIGPIPE/SIGHUP 平台判断 + stdout reconfigure |
| `tui_gateway/server.py` | 编码修复 | subprocess `encoding="utf-8"` |
| `tui_gateway/transport.py` | 编码修复 | StdioTransport 通过 buffer 直接写 UTF-8 bytes |
| `gateway/status.py` | 编码修复 + 容错 | PID 文件 encoding + PermissionError 捕获 |

## 验证

```bash
# 安装依赖
pip install pywinpty

# 启动 dashboard
python -m hermes_cli.main dashboard --tui --no-open

# 访问 http://127.0.0.1:9119/chat — 聊天界面正常可用
```
