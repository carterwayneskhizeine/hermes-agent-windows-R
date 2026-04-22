# Windows Patch Porting TODO

这份文档面向开发者，目标是帮助把 `D:\Code\hermes-agent-windows` 里的 Windows 适配经验，迁移到 `D:\Code\hermes-agent-2026.4.16`（Hermes Agent v0.10.0）或更新版本。

---

## 目标

优先恢复并增强以下能力：

1. **Windows 原生命令执行可用**
2. **PowerShell / Git Bash / Python / Windows 路径之间的桥接稳定**
3. **安装、升级、排障流程对普通 Windows 用户友好**
4. **避免当前这种 WSL/bash 语义与 Windows 原生命令混杂导致的问题**

---

## 背景问题

当前新版本运行时，已经观察到以下问题：

- 会话执行环境偏向 bash / WSL 语义
- 用户实际工作目录和文件都在 Windows 盘符下，例如 `D:\Code\...`
- `rg.exe` 等工具在 Windows 侧可用，但在当前 shell 里不一定直接可用
- 从 bash 调 `powershell.exe` 时，容易出现引号、变量展开、参数转义错误
- Linux 路径（如 `/mnt/d/...`）与 Windows 路径（如 `D:\...`）之间的桥接不稳定

这说明旧版 Windows fork 里的一些“命令路由层”和“安装层”补丁，在新版本中没有完整继承。

---

## Porting 优先级

## P0 — 必须优先迁移

### 1. Shell 检测与命令路由

**目标：** 根据当前平台/环境，决定应使用哪种命令执行后端，而不是默认把一切都按 bash 语义处理。

**要检查的点：**
- 当前终端后端是否假定 Unix shell
- Windows 上是否优先走 PowerShell、CMD，还是 Git Bash
- 当命令明显是 Windows 原生命令时，是否应强制走 Windows shell
- 当命令明显是 Unix 风格命令时，是否应走 Git Bash

**建议动作：**
- 对比新旧版本中 terminal/environment 相关代码
- 找出旧版里 Git Bash 路由逻辑落在哪些模块
- 为 Windows 平台建立明确的 command dispatch policy

**验收标准：**
- `rg`, `dir`, `powershell`, `python`, `git` 等命令在 Windows 上有确定的执行策略
- 不再出现 bash 抢先错误解释 PowerShell one-liner 的情况

---

### 2. Git Bash 桥接逻辑

**目标：** 保留 Git Bash 作为 Windows 上的 Unix 兼容层，但不要让它误伤 Windows 原生命令调用。

**旧版已知机制：**
- 安装时设置 `HERMES_GIT_BASH_PATH`
- 自动探测 `bash.exe`
- 文档明确声明本地 shell 执行通过 Git Bash 路由

**要迁移的点：**
- `HERMES_GIT_BASH_PATH` 的探测
- `bash.exe` 常见路径候选
- Windows 下 Git Bash 的优先级规则
- fallback 行为

**验收标准：**
- Git Bash 能执行 Unix 风格命令
- 同时不会破坏 `powershell.exe -Command ...` 的正常调用

---

### 3. Windows 路径规范化

**目标：** 在所有关键入口都统一处理：
- `D:\Code\x`
- `/mnt/d/Code/x`
- 混合转义路径

**要检查的点：**
- 用户输入路径后，在哪里被解析
- tool 层是否默认认为都是 POSIX path
- Windows 路径是否被错误拼接、错误转义或错误传进 bash

**建议动作：**
- 增加统一路径转换函数
- 明确何时保留原始 Windows 路径，何时转成 `/mnt/...`
- 区分“给 Windows 进程用的路径”和“给 bash 用的路径”

**验收标准：**
- 同一文件路径在 PowerShell、Git Bash、Python 内部都能稳定使用
- 避免同一轮执行中混用错误路径格式

---

### 4. PowerShell 调用的引号/转义修复

**目标：** 解决从 bash/WSL 层调用 `powershell.exe` 时的 quoting 问题。

**症状：**
- 命令被 shell 提前展开
- `$var` 被错误解释
- 管道、引号、正则表达式被破坏

**建议动作：**
- 避免在 bash 中拼长 PowerShell one-liner
- 尽量改为：
  - 写临时 `.ps1` 文件再调用
  - 或使用结构化参数而不是字符串拼接
- 为 Windows shell 调用建立独立 helper

**验收标准：**
- PowerShell one-liner / 脚本调用能稳定处理引号、变量和管道
- 避免出现 `/bin/bash` 抢先展开命令的情况

---

### 5. Windows 原生命令可用性策略

**目标：** 对 `rg.exe`、`python.exe`、`git.exe`、`node.exe` 等 Windows 工具建立一致策略。

**建议动作：**
- `shutil.which()` 之外，增加 Windows 常见安装路径探测
- 对 `.exe` 命令做专门解析
- 必要时增加“优先 Windows native binary”的选项

**验收标准：**
- 已安装在 Windows 上的命令，不会因为当前是 bash 层就被误判为不存在

---

## P1 — 很重要，建议尽快迁移

### 6. 安装脚本中的环境变量与 PATH 逻辑

**旧版明确做过：**
- 设置 `HERMES_HOME`
- 设置 `HERMES_GIT_BASH_PATH`
- 把 venv 的 `Scripts` 加到用户 PATH

**建议动作：**
- 对比 `scripts/install.ps1`
- 检查 v0.10.0 当前安装流程是否仍保留这些逻辑
- 把这部分抽成稳定的 Windows install/runtime bootstrap

---

### 7. 依赖预检和自动修复

**旧版已做：**
- PowerShell / uv / Git / Node / Python / Git Bash 的预检
- 缺依赖给中文说明、推荐版本、下载链接

**建议动作：**
- 将预检逻辑从安装器层抽离，复用到 `hermes doctor` 或首次启动流程
- 增加 Windows 专项 doctor 模式

**验收标准：**
- 用户在安装前就能看出缺什么
- 安装失败时不会只得到模糊错误

---

### 8. Windows 进程管理兼容

**旧版 README 明确提到：**
- 修复 Windows 下 `os.kill` WinError 11 问题

**建议动作：**
- 搜索新旧版本中：
  - `os.kill`
  - `os.killpg`
  - `signal`
  - `terminate`
  - `SIGTERM` / `SIGKILL`
- 审核哪些逻辑在 Windows 上不成立
- 为 Windows 提供单独分支

**验收标准：**
- 终止后台任务、停止 gateway、清理子进程时不再触发 Windows 特有错误

---

## P2 — 体验增强 / 可选迁移

### 9. Windows 安装器（GUI / Console）

如果新版本希望面向普通 Windows 用户分发，建议保留：

- EXE GUI 安装器
- Console 安装器
- `--check-only`
- 中文预检输出
- `%TEMP%\hermes-installer.log`

这部分不一定影响核心运行，但会显著提高安装成功率和排障效率。

---

### 10. 中文界面与 Windows 文档

可继续保留：
- Windows 专用 README
- 中文安装说明
- 常见故障排查指南

---

## 建议的代码审查路径

建议优先 diff 以下区域：

### 旧版 Windows fork
- `scripts/install.ps1`
- `scripts/install.cmd`
- `WINDOWS_SUPPORT.md`
- `packaging/windows-installer/bootstrap.py`
- `clear.ps1`
- 与进程管理 / shell / 终端后端相关的 Python 模块

### 新版主线 / 当前运行版本
- `tools/terminal_tool.py`
- `tools/environments/*`
- `cli.py`
- `hermes_cli/*`
- 所有 shell / subprocess / process registry / path handling 相关模块

---

## 建议的排查顺序

1. **先看命令执行链**
   - 用户输入命令
   - 工具层如何决定 shell
   - 最终 subprocess 怎样启动

2. **再看路径转换链**
   - Windows path 进入系统后如何被处理
   - `/mnt/...` 与 `D:\...` 之间谁负责转换

3. **再看 PowerShell 调用链**
   - 是否在 bash 中直接拼接 one-liner
   - 是否存在安全/稳定的独立 helper

4. **最后看安装器和 doctor**
   - 把“运行前就能发现的问题”尽量前置

---

## 推荐新增的测试

### 单元测试
- Windows path → shell path 转换
- shell 路由选择
- PowerShell 参数转义
- `rg.exe` / `python.exe` / `git.exe` 查找

### 集成测试
- 在 Windows 上执行简单命令：
  - `rg --version`
  - `powershell.exe -Command "Write-Output ok"`
  - `git --version`
  - `python -V`
- 在 Git Bash 中执行 Unix 风格命令
- 在 PowerShell 中执行 Windows 风格命令
- 混合路径读写测试

---

## 当前建议结论

如果只能先做一小部分，优先顺序建议是：

1. **恢复 Windows shell 路由策略**
2. **恢复 Git Bash 桥接与 `HERMES_GIT_BASH_PATH` 逻辑**
3. **修复 PowerShell 调用转义**
4. **补齐 Windows 路径规范化**
5. **回补 `os.kill` / 进程管理兼容修复**

这 5 项最可能直接解决当前“Windows 工具明明装了，但运行时行为混乱”的核心问题。
