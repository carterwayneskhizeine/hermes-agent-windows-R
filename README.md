<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# Hermes Agent ☤

<p align="center">
  <img src="docs/chat.jpg" alt="Hermes Chat 界面" width="100%">
</p>

# Hermes Agent — Windows 开发版安装指南

本文档面向在 **Windows 原生环境**（无需 WSL）下运行 Hermes Agent 开发版的用户。

> 原始英文 README 已备份至 `README_hermes.md`。

---

## 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [首次配置](#首次配置)
- [常用命令](#常用命令)
- [Profile 多实例](#profile-多实例)
- [Windows 特有说明](#windows-特有说明)
- [故障排查](#故障排查)
- [相关文档](#相关文档)
- [Windows 适配变更摘要](#windows-适配变更摘要)
- [Windows PowerShell 双 Agent 启动与管理指南](#windows-powershell-双-agent-启动与管理指南)

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
uv pip install -e ".[all,dev]"
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

Hermes 自动按以下顺序探测 `bash.exe`（已过滤 WSL 启动器）：

1. 环境变量 `HERMES_GIT_BASH_PATH`
2. `%ProgramFiles%\Git\bin\bash.exe`
3. `%ProgramFiles(x86)%\Git\bin\bash.exe`
4. `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`
5. `shutil.which("bash")`（跳过 `C:\Windows\System32\bash.exe` 的 WSL 启动器）

> ⚠️ **不支持 WSL bash**：WSL 使用 `/mnt/d/...` 路径约定，和 Git Bash 的 `/d/...` 不兼容，会导致 `write_file` 把文件写到 WSL 内部文件系统。装了 WSL 的系统上 `shutil.which("bash")` 会优先返回 WSL 启动器，Hermes 在 Git Bash 专用路径探测之后才回退到 PATH 查找，并显式过滤掉 `System32\bash.exe`。

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

## Profile 多实例

Hermes 支持 profile 隔离，每个 profile 拥有独立的配置、记忆、会话和技能。

### 创建 Profile

```powershell
hermes profile create turing --clone   # 克隆 default 配置
```

### 在 Windows 上使用 Profile

`hermes profile create` 会在 `~/.local/bin/` 生成一个 bash wrapper 脚本，**该脚本在 PowerShell 中无法执行**。Windows 用户请使用以下三种方式之一：

#### 方式一：`-p` 参数（推荐）

```powershell
hermes -p turing setup          # 配置 API 密钥和模型
hermes -p turing chat           # 启动聊天
hermes -p turing gateway run    # 启动 gateway
hermes -p turing doctor         # 诊断
```

#### 方式二：`--profile` 长参数

```powershell
hermes --profile=turing setup
hermes --profile=turing chat
```

#### 方式三：设为默认 profile

```powershell
hermes profile use turing       # 设为当前默认
hermes setup                    # 等同于 hermes -p turing setup
hermes chat                     # 等同于 hermes -p turing chat
hermes profile use default      # 切回默认
```

### Profile 管理命令

```powershell
hermes profile list             # 列出所有 profile
hermes profile info turing      # 查看 profile 详情
hermes profile rename turing ada  # 重命名
hermes profile delete turing    # 删除
```

每个 profile 的数据位于 `~/.hermes/profiles/<name>/`，包含独立的 `config.yaml`、`.env`、`SOUL.md` 等文件。

---

## Windows 特有说明

### 文件写入路径

Hermes 的文件操作通过 Git Bash 执行。路径会自动转换为 MSYS 格式：

```
D:\Doc\foo\bar.md  →  /d/Doc/foo/bar.md
```

此转换在 `tools/platform_compat.py` 的 `windows_path_to_msys()` 中完成，对所有 `write_file` / `read_file` 等操作透明生效。

### 会话 CWD 和临时文件

`LocalEnvironment`（`tools/environments/local.py`）在 Windows 上额外处理：

- 初始 CWD 经 `windows_path_to_msys()` 转为 `/d/Code/...`，确保 bash 的 `cd` 可靠
- 会话快照 / CWD 临时文件放在 `%LOCALAPPDATA%\Temp\hermes\`（MSYS 形式 `/c/Users/.../Temp/hermes/`），bash 和 Python 都能访问
- 同时保存 `_snapshot_path_win` / `_cwd_file_win`（Windows 形式），供 Python `open()` / `os.unlink()` 使用

### 危险命令拦截

`tools/approval.py` 会拦截会在 Git Bash 下卡死或误伤整个驱动器的命令：

- `find /` — MSYS 把 `/` 映射到整个 Windows 根，会遍历所有驱动器
- `find /home` — 类似问题
- `ls -R /` — 递归列出根目录

这些命令需改为指定具体路径（如 `find /d/Doc -name '*.md'`）。

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

**Q: `write_file` 返回成功但文件没创建？**

通常是 WSL bash 抢占了 Git Bash。让 AI 运行 `terminal: command="pwd"`：

- 返回 `/d/Code/...` → Git Bash（正确）
- 返回 `/mnt/d/Code/...` → WSL bash（错误，文件会写到 WSL 内部）

如果是 WSL bash，装 Git for Windows 或设 `HERMES_GIT_BASH_PATH` 指向 Git Bash，重启 `hermes gateway run`。

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

## 相关文档

- `docs/winodws_support/代码修改总结_2026-04-26.md` — Windows 适配代码修改详细记录
- `docs/winodws_support/PORTING_SUMMARY_2026-04-23.md` — Windows 适配移植记录
- `README_hermes.md` — 原始英文 README（完整功能说明）

---

## Windows 适配变更摘要

基于上游 `093bf90b` 之后的变更（5 个提交）：

| 提交 | 说明 |
|------|------|
| `49a73677` | fix(windows): resolve encoding crashes and add ConPTY support |
| `a6f3ac4e` | fix(windows): improve Git Bash compatibility and path handling |
| `62ae82a8` | refactor(subprocess): standardize encoding and error handling for subprocess calls |
| `a7100fe1` | fix(windows): force utf-8 encoding for stdio streams |
| `f73c6dcd` | feat(tui): implement ephemeral sessions for web chat sidebar |

核心修复：
1. **编码修复（146 处）**：全局 `subprocess` 调用添加 `encoding="utf-8", errors="replace"`，解决中文 Windows GBK 崩溃
2. **终端输出捕获**：Windows 使用 `proc.stdout.buffer.read1()` 替代 `select.select()`，解决终端工具输出为空
3. **stdio UTF-8**：`entry.py` / `slash_worker.py` / `transport.py` 全量 UTF-8 重配置，解决 TUI 中文输入乱码
4. **ConPTY 支持**：`pywinpty` 实现 Windows 伪终端，Dashboard Chat 可嵌入 TUI
5. **Ephemeral session**：侧边栏 session 不再写入数据库，避免 Sessions 页出现空「无标题会话」

# Windows PowerShell 双 Agent 启动与管理指南

本文档面向在 Windows 原生环境（PowerShell 7+）同时运行两个 Hermes Agent 实例（`default` 和 `turing`）的用户，涵盖 Gateway、Web 仪表盘、Profile 管理以及常见告警处理。

---

## 目录

- [前置准备](#前置准备)
- [启动 default Agent](#启动-default-agent)
- [启动 turing Agent](#启动-turing-agent)
- [同时运行多个 Agent](#同时运行多个-agent)
- [Dashboard Web UI（含 TUI Chat）](#dashboard-web-ui含-tui-chat)
- [Agent / Profile 管理](#agent--profile-管理)
- [常见告警](#常见告警)
- [故障排查](#故障排查)
- [快速参考：完整启动流程](#快速参考完整启动流程)

---

## 前置准备

### 激活虚拟环境

每个新开的 PowerShell 窗口都需要先激活一次：

```powershell
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
```

激活成功后提示符前会出现 `(venv)`。

> 若提示脚本执行被禁止：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 确认前端已构建

Web 仪表盘默认由 Python 服务器托管构建后的静态文件，位于 `hermes_cli/web_dist/`。如果是首次运行或修改了前端，请先构建：

```powershell
cd web
npm install          # 首次安装依赖
npm run build
cd ..
```

此后只要不再改动前端，直接启动 Python 服务器即可，无需 `npm run dev`。

---

## 启动 default Agent

默认 profile 对应 `~/.hermes/`（即 `C:\Users\<用户名>\.hermes\`）。

### 1. 启动 Gateway（消息平台 + 定时任务）

```powershell
hermes gateway run
```

看到如下 banner 即代表成功：

```
┌─────────────────────────────────────────────────────────┐
│           ⚕ Hermes Gateway Starting...                 │
├─────────────────────────────────────────────────────────┤
│  Messaging platforms + cron scheduler                   │
│  Press Ctrl+C to stop                                   │
└─────────────────────────────────────────────────────────┘
```

> 只有在配置了 Telegram / Discord / Slack 等平台时才需要 Gateway。仅用 Web UI 聊天可以不启动。

### 2. 启动 Web 仪表盘（含 TUI Chat）

**新开一个 PowerShell 窗口**，激活虚拟环境后：

```powershell
python -m hermes_cli.main dashboard --no-open --tui
```

参数说明：

| 参数 | 说明 |
|------|------|
| `--no-open` | 不自动打开浏览器 |
| `--tui` | 启用 Chat 标签页（通过 ConPTY 嵌入完整 TUI 体验） |

输出：
```
→ Building web UI...
  ✓ Web UI built
  Hermes Web UI → http://127.0.0.1:9119
```

浏览器打开 `http://127.0.0.1:9119` 即可。

---

## 启动 turing Agent

turing profile 对应 `C:\Users\<用户名>\.hermes\profiles\turing\`。

### 方式一：`-p` 参数（推荐，不改默认 profile）

```powershell
hermes -p turing gateway run
```

### 方式二：通过 `HERMES_HOME` 环境变量

适合 Web 仪表盘场景，因为 `dashboard` 子命令本身不支持 `-p` 参数：

```powershell
$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\turing"
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

> **注意端口要改**（例如 9120），避免和默认 9119 冲突。

输出：
```
Hermes Web UI → http://127.0.0.1:9120
```

> ⚠️ `$env:HERMES_HOME` 只在当前 PowerShell 会话有效。关闭窗口后失效。

### 方式三：设为默认 profile

```powershell
hermes profile use turing   # 切换
hermes gateway run          # 此时等同于 -p turing
hermes profile use default  # 用完切回
```

---

## 同时运行多个 Agent

每个 Agent 实例需要**独立的 API Server 端口**和**独立的 Telegram Bot Token**，否则会出现端口冲突或 Telegram 轮询冲突。

### 配置 API Server 端口（必须）

> **注意**：`port` 必须放在 `extra` 下面，不能直接写在 `api_server` 下面。
> 这是因为 `PlatformConfig.from_dict()` 只从 `extra` 字典中读取自定义字段，
> 扁平写法的 `port` 不会被解析，会回退到默认端口 8642。

编辑各 profile 的 `config.yaml`，在文件末尾添加：

```yaml
platforms:
  api_server:
    extra:
      port: 8647   # ← 每个 profile 用不同的端口
```

当前端口分配：

| Profile | API Server 端口 | Dashboard 端口 | config 路径 |
|---------|----------------|----------------|-------------|
| default | 8647 | 9119 | `~/.hermes/config.yaml` |
| turing  | 8641 | 9120 | `~/.hermes/profiles/turing/config.yaml` |
| belbin  | 8645 | 9121 | `~/.hermes/profiles/belbin/config.yaml` |

### 配置 Telegram Bot Token

每个使用 Telegram 的 profile 必须使用**不同的 Bot Token**（通过 @BotFather 创建多个 bot）。
在各自的 `.env` 文件中设置：

```
TELEGRAM_BOT_TOKEN=<该 profile 专属的 token>
```

同一个 token 不能被两个实例同时轮询，否则会出现 `Conflict: terminated by other getUpdates request` 错误。

### 启动三个 Agent

典型场景：开 6 个 PowerShell 窗口，每个窗口跑一个进程。

| 窗口 | 任务 | 命令 |
|------|------|------|
| #1 | default Gateway | `hermes gateway run` |
| #2 | default Dashboard（端口 9119）| `python -m hermes_cli.main dashboard --no-open --tui` |
| #3 | turing Gateway | `hermes -p turing gateway run` |
| #4 | turing Dashboard（端口 9120）| 见下方 |
| #5 | belbin Gateway | `hermes -p belbin gateway run` |
| #6 | belbin Dashboard（端口 9121）| 见下方 |

**窗口 #4 的完整命令：**

```powershell
$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\turing"
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

**窗口 #6 的完整命令：**

```powershell
$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\belbin"
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
python -m hermes_cli.main dashboard --no-open --tui --port 9121
```

运行完成后：
- default Web UI → `http://127.0.0.1:9119`
- turing Web UI → `http://127.0.0.1:9120`
- belbin Web UI → `http://127.0.0.1:9121`

---

## Dashboard Web UI（含 TUI Chat）

构建好前端后，Web UI 的所有功能（Status / Sessions / Chat / Analytics / Logs / Cron / Skills / Config / Keys）直接通过 Python 服务器提供，**不需要 Vite 开发服务器**。

### 何时需要 `npm run dev`

只有在**修改前端源码并希望热更新**时才使用：

```powershell
cd D:\Code\goldie-fork\hermes-agent\web
npm run dev
```

开发服务器会在 `http://localhost:5188` 启动。它需要一个后端实例作为数据源（默认指向 `http://127.0.0.1:9119`）。指向 turing：

```powershell
$env:HERMES_DASHBOARD_URL = "http://127.0.0.1:9120"
npm run dev
```

### Chat 页面

Chat 页面通过 ConPTY 在浏览器中嵌入完整 TUI 体验。使用 `--tui` 参数启动 dashboard 后访问 `/chat` 即可。

功能：
- 流式助手输出、工具调用实时显示、中断正在运行的会话
- 斜杠命令：在输入框键入 `/` 会弹出命令列表
- **流式输出期间发送新消息**：AI 正在回复时，输入框和发送按钮始终保持可用。发送新消息会自动中断当前输出并处理新请求，无需手动点击停止按钮
- **模型切换斜杠语法**：使用 `/model provider/model-name` 格式快速切换模型，例如 `/model zai/glm-5.1`、`/model anthropic/claude-sonnet-4-6`，等同于 `/model model-name --provider provider`
- **状态栏（Status Bar）**：输入框下方显示模型名称、上下文窗口大小、Token 用量（输入/输出）、API 调用次数、预估费用和上下文使用率百分比。使用率按阈值颜色编码：绿色（<50%）、黄色（50-80%）、橙色（80-95%）、红色（>95%）。点击输入框左下方的图表图标可切换显示/隐藏，偏好自动保存到 localStorage
- **剪贴板**：支持 Ctrl+Shift+C/V 复制粘贴，点击右下角按钮复制最后一条回复

> **注意**：Chat 页面仅限从 `localhost` 访问，请通过 `hermes dashboard` 启动后打开，不要直接输入 URL。
>
> **已修复**：中文输入/显示正常（UTF-8 编码修复）；Sessions 页面不会出现空「无标题会话」（ephemeral session 机制）。

---

## Agent / Profile 管理

### 列出所有 Profile

```powershell
hermes profile list
```

输出示例：
```
 Profile      Model              Gateway      Alias
 ───────────    ───────────────    ───────────    ────────
 ◆default     gpt-5.4            stopped      —
  turing      MiniMax-M2.7       stopped      turing
```

### 创建 Profile

```powershell
hermes profile create <名字> --clone   # 克隆 default 配置
hermes profile create <名字>           # 从空白开始
```

Profile 目录位于 `C:\Users\<用户名>\.hermes\profiles\<名字>\`，包含独立的 `config.yaml`、`.env`、`SOUL.md`、`state.db` 等。

### 查看 Profile 详情

```powershell
hermes profile show turing
```

### 重命名 / 删除

```powershell
hermes profile rename turing ada
hermes profile delete turing
```

> 删除操作会要求确认。Profile 目录下的所有数据（会话历史、技能、配置）都会被清除。

### 配置模型 / API Key

针对指定 profile 配置：

```powershell
hermes -p turing model        # 切换 LLM 模型
hermes -p turing setup        # 交互式配置 API key
hermes -p turing tools        # 管理工具开关
hermes -p turing doctor       # 诊断环境问题
hermes -p turing config set terminal.cwd "D:\Code\your-project"
```

### 切换默认 Profile

```powershell
hermes profile use turing     # 设为默认
hermes profile use default    # 切回
```

---

## 常见告警

### ⚠ TERMINAL_CWD 在 .env 中已废弃

启动时可能看到：

```
⚠ Deprecated .env settings detected:
  ⚠ TERMINAL_CWD=D:\Code\goldie-fork\hermes-agent found in .env — this is deprecated.
  Move to config.yaml instead:  terminal:
    cwd: /your/project/path
  Then remove the old entries from C:\Users\gotmo\.hermes\profiles\turing/.env
```

**含义：** Hermes 早期版本用 `.env` 里的 `TERMINAL_CWD` 指定 Agent 执行命令的默认工作目录。新版本改为通过 `config.yaml` 的 `terminal.cwd` 字段来配置，更统一、更结构化。

**解决步骤（针对 turing profile）：**

#### 1. 写入 `config.yaml`

最简单的方式：

```powershell
hermes -p turing config set terminal.cwd "D:\Code\goldie-fork\hermes-agent"
```

或手动编辑 `C:\Users\gotmo\.hermes\profiles\turing\config.yaml`，新增：

```yaml
terminal:
  cwd: D:\Code\goldie-fork\hermes-agent
```

> 路径使用 Windows 绝对路径即可。`tools/platform_compat.py` 内部会自动转成 `/d/Code/...` 的 MSYS 形式传给 Git Bash。

#### 2. 从 `.env` 移除旧条目

用编辑器打开 `C:\Users\gotmo\.hermes\profiles\turing\.env`，删除这一行：

```
TERMINAL_CWD=D:\Code\goldie-fork\hermes-agent
```

#### 3. 重启 Agent

关闭正在运行的 dashboard / gateway 后重新启动，告警就会消失。

> 对 default profile 同理，只是路径是 `C:\Users\<用户名>\.hermes\.env` 和 `config.yaml`。

---

## 故障排查

Vite 开发服务器的 WebSocket 代理已在 `web/vite.config.ts` 中配置，启动前请确保对应的 dashboard 正在运行。

### Q: API Server 端口 8642 冲突 / `Port already in use`？

多 profile 同时运行时，每个 profile 的 API Server 必须用不同端口。在 `config.yaml` 中设置：

```yaml
platforms:
  api_server:
    extra:
      port: 8645   # 每个 profile 不同
```

> `port` **必须**放在 `extra` 下面。直接写 `api_server.port` 不会被解析，会始终回退到默认的 8642。

如果端口仍然被旧进程占用，先终止：

```powershell
# 查找占用端口的进程
netstat -ano | findstr 8642
taskkill /PID <pid> /F
```

### Q: Dashboard 端口 9119 已被占用？

```powershell
# 查找占用端口的进程
Get-NetTCPConnection -LocalPort 9119 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Get-Process -Id $_ }

# 终止
taskkill /PID <pid> /F
```

或直接换端口：`--port 9121`。

### Q: `HERMES_HOME` 设错了怎么办？

```powershell
$env:HERMES_HOME = $null     # 清除当前会话的环境变量
```

或直接关闭 PowerShell 窗口重开。全局设置（非临时）需在"系统属性 → 环境变量"中修改。

### Q: Web UI 显示 "Frontend not built"？

```powershell
cd D:\Code\goldie-fork\hermes-agent\web
npm run build
```

构建产物会输出到 `D:\Code\goldie-fork\hermes-agent\hermes_cli\web_dist\`。

### Q: `hermes` 命令找不到？

虚拟环境未激活。执行：

```powershell
.\venv\Scripts\Activate.ps1
```

提示符出现 `(venv)` 后再试。

---

## 快速参考：完整启动流程

```powershell
# ── 窗口 1：default Gateway ──
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
hermes gateway run

# ── 窗口 2：default Web UI（含 TUI Chat）──
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
python -m hermes_cli.main dashboard --no-open --tui
# → http://127.0.0.1:9119

# ── 窗口 3：turing Gateway ──
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
hermes -p turing gateway run

# ── 窗口 4：turing Web UI ──
$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\turing"
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
python -m hermes_cli.main dashboard --no-open --tui --port 9120
# → http://127.0.0.1:9120

# ── 窗口 5：belbin Gateway ──
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
hermes -p belbin gateway run

# ── 窗口 6：belbin Web UI ──
$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\belbin"
cd D:\Code\goldie-fork\hermes-agent
.\venv\Scripts\Activate.ps1
python -m hermes_cli.main dashboard --no-open --tui --port 9121
# → http://127.0.0.1:9121
```
