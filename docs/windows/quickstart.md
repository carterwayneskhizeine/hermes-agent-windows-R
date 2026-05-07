# Windows 快速安装

本文档面向在 Windows 原生环境（无需 WSL）运行 Hermes Agent 开发版的用户。所有命令默认在 PowerShell 7+ 中执行。

## 环境要求

请确保以下工具已安装并加入 `PATH`：

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| Python 3.12 | Hermes 运行时 | [python.org](https://www.python.org/downloads/) |
| Git for Windows | 提供 `bash.exe`，Hermes 本地 shell 后端 | [git-scm.com](https://git-scm.com/download/win) |
| uv | 虚拟环境和包管理器 | `irm https://astral.sh/uv/install.ps1 \| iex` |
| ripgrep (`rg.exe`) | 快速文件搜索，可选但推荐 | `winget install BurntSushi.ripgrep.MSVC` |
| psmux | 多 session 管理，用于一键启动脚本，可选 | `winget install psmux` |

## 安装步骤

```powershell
git clone https://github.com/carterwayneskhizeine/hermes-agent-windows-R.git
cd hermes-agent-windows-R
uv venv venv --python 3.12
.\venv\Scripts\Activate.ps1
uv pip install -e ".[all,dev]"
```

如果 PowerShell 阻止激活脚本：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 首次配置

配置模型：

```powershell
hermes model
```

配置 Telegram、Discord、Slack、WhatsApp、Signal 等消息平台：

```powershell
hermes gateway setup
```

启动 Gateway：

```powershell
hermes gateway run
```

启动交互式 CLI：

```powershell
hermes
```

## Git Bash 路径

Hermes 在 Windows 上需要 Git for Windows 提供的 `bash.exe`。自动探测顺序：

1. 环境变量 `HERMES_GIT_BASH_PATH`
2. `%ProgramFiles%\Git\bin\bash.exe`
3. `%ProgramFiles(x86)%\Git\bin\bash.exe`
4. `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`
5. `shutil.which("bash")`，但会跳过 `C:\Windows\System32\bash.exe`

如果自动探测失败，可手动指定：

```powershell
$env:HERMES_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"
```

不要使用 WSL bash。WSL 的 `/mnt/d/...` 路径和 Git Bash 的 `/d/...` 路径不兼容，可能导致工具把文件写到 WSL 内部文件系统。

## 常用命令

```powershell
hermes                  # 启动交互式 CLI
hermes gateway run      # 启动消息 gateway
hermes gateway stop     # 停止 gateway
hermes model            # 切换 LLM 模型
hermes tools            # 管理工具开关
hermes config set       # 修改单项配置
hermes doctor           # 诊断环境问题
```

## 运行测试

```powershell
.\venv\Scripts\python.exe -m pytest tests/tools/test_windows_compat.py -v

.\venv\Scripts\python.exe -m pytest tests/tools/test_windows_compat.py `
    tests/gateway/test_status.py tests/hermes_cli/test_profiles.py -v
```
