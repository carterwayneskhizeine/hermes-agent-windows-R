# Hermes Agent Windows 优化版清单

这个清单总结 `D:\Code\hermes-agent-windows` 相比上游/当前主线版本，已经明确做过的 Windows 适配与体验增强。

## 1. Windows 原生安装支持

- [x] 支持 **无需 WSL2** 的原生 Windows 安装与运行
- [x] 提供 PowerShell 一键安装入口：`scripts/install.ps1`
- [x] 提供 Windows 命令入口：`scripts/install.cmd`
- [x] 安装目标改为 `%LOCALAPPDATA%\hermes`
- [x] 为 Windows 用户单独编写安装说明和 README

**相关文件**
- `README.md`
- `WINDOWS_SUPPORT.md`
- `scripts/install.ps1`
- `scripts/install.cmd`

---

## 2. Windows 运行时环境适配

- [x] 设置 `HERMES_HOME`
- [x] 设置 `HERMES_GIT_BASH_PATH`
- [x] 将 Hermes 可执行路径加入用户 `PATH`
- [x] 为 Windows 安装目录和运行目录建立默认结构
- [x] 支持从 PowerShell / CMD 启动 Hermes

**相关文件**
- `scripts/install.ps1`
- `clear.ps1`
- `WINDOWS_SUPPORT.md`

---

## 3. Git Bash 兼容层

- [x] 明确采用 **Git Bash** 作为本地命令执行兼容层
- [x] 自动探测 `bash.exe` 常见安装位置
- [x] 将 Git Bash 作为 Windows 版 Hermes 的关键依赖
- [x] 在文档里明确说明：Hermes 启动于 PowerShell/CMD，但本地 shell 执行通过 Git Bash 路由

**相关文件**
- `WINDOWS_SUPPORT.md`
- `scripts/install.ps1`
- `packaging/windows-installer/bootstrap.py`
- `CONTRIBUTING.md`

---

## 4. 自动依赖安装 / 预检

- [x] 自动准备 `uv`
- [x] 自动准备 Git for Windows
- [x] 自动准备 Node.js
- [x] 自动准备 `ripgrep`
- [x] 自动准备 `ffmpeg`
- [x] 安装前执行环境预检
- [x] 缺依赖时显示说明、推荐版本、官方下载链接
- [x] 支持手动下载指引

**相关文件**
- `WINDOWS_SUPPORT.md`
- `scripts/install.ps1`
- `packaging/windows-installer/bootstrap.py`

---

## 5. Windows 安装器体验增强

- [x] 提供基于 `PyInstaller` 的 EXE 安装器
- [x] 提供 GUI 安装器：`HermesInstaller.exe`
- [x] 提供 Console 安装器：`HermesInstallerConsole.exe`
- [x] 安装器内置并复用 `install.ps1`
- [x] 构建时打包本地仓库快照
- [x] 安装日志写入 `%TEMP%\hermes-installer.log`
- [x] 支持 `--check-only`
- [x] 支持 `--skip-setup`
- [x] 支持 `--no-venv`
- [x] 支持 GUI / Console 模式切换

**相关文件**
- `packaging/windows-installer/README.md`
- `packaging/windows-installer/bootstrap.py`
- `packaging/windows-installer/build.ps1`

---

## 6. Windows 用户体验优化

- [x] 安装器和预检信息支持中文说明
- [x] 更偏向普通 Windows 用户的说明文档
- [x] 出错时给出更明确的环境/依赖提示
- [x] 提供清理旧安装与旧环境变量的脚本

**相关文件**
- `README.md`
- `packaging/windows-installer/README.md`
- `packaging/windows-installer/bootstrap.py`
- `clear.ps1`

---

## 7. 项目 README 明确声明过的适配项

根据 `hermes-agent-windows/README.md`，该 Windows 适配版明确声明包含：

- [x] Windows 原生安装，无需 WSL2
- [x] Git Bash 兼容性
- [x] 修复 Windows 下 `os.kill` WinError 11 问题
- [x] 新增 `hermes web` 命令
- [x] 新增对话页面 `ChatPage`
- [x] 中文界面支持

**相关文件**
- `README.md`

---

## 8. 与当前主线版本的关键差异（高层）

- [x] 上游/主线 README 仍明确提示 **Windows native 不支持，建议 WSL2**
- [x] Windows fork 则以 **原生 Windows** 为目标
- [x] Windows fork 明确增加了安装器、预检、Git Bash 路由、环境变量设置等 Windows 专属逻辑
- [x] Windows fork 更强调“安装成功率”和“普通用户体验”

---

## 9. 对当前排障最相关的部分

如果要把这些适配重新移植到新版本，最值得优先检查的是：

- [ ] shell 检测与命令路由
- [ ] Git Bash 调用链
- [ ] Windows 路径与 `/mnt/...` / bash 路径之间的桥接
- [ ] PowerShell 调用时的引号与参数转义
- [ ] `rg.exe` / Windows 原生命令在当前运行模型中的调用方式
- [ ] `os.kill` / 进程管理在 Windows 下的兼容逻辑
- [ ] `hermes web` 与 ChatPage 相关代码是否已并入新版本或需要重新适配

---

## 10. 建议后续动作

- [ ] 对比 `D:\Code\hermes-agent-windows` 与 `D:\Code\hermes-agent-2026.4.16` 的安装脚本差异
- [ ] 对比终端 / shell / 进程管理相关代码差异
- [ ] 找出 Windows fork 中仍然存在、但新版本缺失的关键补丁
- [ ] 优先恢复“Windows 命令执行桥接”这条链路

