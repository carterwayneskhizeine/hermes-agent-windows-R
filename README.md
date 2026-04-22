# Hermes Agent — Windows 开发版安装指南

本文档面向在 **Windows 原生环境**（无需 WSL）下运行 Hermes Agent 开发版的用户。

> 原始英文 README 已备份至 `README_hermes.md`。

---

> **特别感谢**
>
> 本 Windows 适配工作大量参考了 [**pengchengxia75-arch**](https://github.com/pengchengxia75-arch) 的 Windows fork：
> [github.com/pengchengxia75-arch/hermes-agent-windows](https://github.com/pengchengxia75-arch/hermes-agent-windows)
>
> 感谢作者在 Windows 兼容性上所做的先行探索，本项目的适配补丁正是在其工作基础上整理而来。

---

## 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [首次配置](#首次配置)
- [常用命令](#常用命令)
- [故障排查](#故障排查)
- [清理卸载](#清理卸载)

---

## 环境要求

在开始之前，请确保以下工具已安装并添加到 PATH：

| 工具 | 用途 | 下载地址 |
|------|------|----------|
| **Python 3.12** | 运行时 | [python.org](https://www.python.org/downloads/) |
| **Git for Windows** | 提供 `bash.exe`，Hermes 本地 shell 后端 | [git-scm.com](https://git-scm.com/download/win) |
| **uv** | 虚拟环境 + 包管理器 | PowerShell 执行 `irm https://astral.sh/uv/install.ps1 \| iex` |
| **ripgrep** (`rg.exe`) | 快速文件搜索（可选但推荐） | `winget install BurntSushi.ripgrep.MSVC` |

---

## 安装步骤

以下所有命令在 **PowerShell** 中执行（建议使用 PowerShell 7+）。

### 1. 克隆仓库

```powershell
git clone https://github.com/carterwayneskhizeine/hermes-agent-windows-R.git
cd hermes-agent-windows-R
```

### 2. 创建虚拟环境

```powershell
uv venv venv --python 3.12
```

### 3. 激活虚拟环境

```powershell
.\venv\Scripts\Activate.ps1
```

> 若提示执行策略报错，先执行：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 4. 安装依赖

```powershell
uv pip install -e ".[all]"
```

### 5. 启动 Gateway

```powershell
hermes gateway run
```

---

## 首次配置

### 配置 LLM 模型

```powershell
hermes model
```

按提示选择 provider（OpenRouter、OpenAI、Nous Portal 等）和模型。

### 配置消息平台（可选）

```powershell
hermes gateway setup
```

支持 Telegram、Discord、Slack、WhatsApp、Signal。

### Git Bash 路径

Hermes 自动按以下顺序探测 `bash.exe`：

1. 环境变量 `HERMES_GIT_BASH_PATH`
2. `shutil.which("bash")`
3. `%ProgramFiles%\Git\bin\bash.exe`
4. `%ProgramFiles(x86)%\Git\bin\bash.exe`
5. `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`

若自动探测失败，手动指定：

```powershell
$env:HERMES_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"
```

---

## 常用命令

```powershell
hermes                  # 启动交互式 CLI
hermes gateway run      # 启动消息 gateway（Telegram/Discord 等）
hermes gateway stop     # 停止 gateway
hermes model            # 切换 LLM 模型
hermes tools            # 管理工具开关
hermes config set       # 修改单项配置
hermes doctor           # 诊断环境问题
```

### 运行测试

```powershell
# Windows 兼容性测试
.\venv\Scripts\python.exe -m pytest tests/tools/test_windows_compat.py -v

# 核心模块测试
.\venv\Scripts\python.exe -m pytest tests/tools/test_windows_compat.py `
    tests/gateway/test_status.py tests/hermes_cli/test_profiles.py -v
```

---

## Windows 特有说明

### 文件写入路径

Hermes 的文件操作通过 Git Bash 执行。路径会自动转换为 MSYS 格式：

```
D:\Doc\foo\bar.md  →  /d/Doc/foo/bar.md
```

此转换在 `tools/platform_compat.py` 的 `windows_path_to_msys()` 中完成，对所有 `write_file` / `read_file` 等操作透明生效。

### 进程管理

Windows 不支持 `os.kill(pid, 0)` 和 `signal.SIGKILL`，Hermes 已使用以下替代：

- 进程存活检查：`psutil.pid_exists()` 或 `tasklist`
- 强制终止：`taskkill /PID <pid> /T /F`

### 已知限制

以下功能在 Windows 上未经充分测试：

- Discord 语音频道
- WhatsApp bridge
- Docker / SSH / Modal / Daytona terminal 后端
- RL 训练（`tinker-atropos`）

---

## 故障排查

**Q: `hermes` 命令找不到？**

确认虚拟环境已激活（提示符前有 `(venv)`），或直接用完整路径：
```powershell
.\venv\Scripts\hermes.exe gateway run
```

**Q: Git Bash 找不到？**

安装 [Git for Windows](https://git-scm.com/download/win)，或手动设置：
```powershell
$env:HERMES_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"
```

**Q: `uv pip install` 失败？**

先检查 Python 版本：
```powershell
python --version   # 需要 3.12.x
uv --version
```

**Q: 运行 `hermes doctor` 提示缺少依赖？**

按提示安装缺失工具，`ripgrep` 可通过以下方式安装：
```powershell
winget install BurntSushi.ripgrep.MSVC
```

---

## 清理卸载

`clear.ps1` 脚本会清除本地安装产物：

- 停止 Hermes 进程
- 删除 `%LOCALAPPDATA%\hermes`
- 清除 `HERMES_HOME` / `HERMES_GIT_BASH_PATH` 用户环境变量
- 从用户 PATH 中移除旧的 Hermes 路径

```powershell
powershell -ExecutionPolicy Bypass -File .\clear.ps1
```

---

## 相关文档

- `WINDOWS_SUPPORT.md` — Windows 运行模型与跨平台 helper 技术细节
- `docs/winodws_support/PORTING_SUMMARY_2026-04-23.md` — Windows 适配移植记录
- `README_hermes.md` — 原始英文 README（完整功能说明）
