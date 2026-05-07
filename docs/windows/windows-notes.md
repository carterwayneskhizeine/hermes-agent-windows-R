# Windows 特有说明

## 文件写入路径

Hermes 的文件工具通过 Git Bash 执行。Windows 路径会转换为 MSYS 路径：

```text
D:\Doc\foo\bar.md  ->  /d/Doc/foo/bar.md
```

转换逻辑位于 `tools/platform_compat.py` 的 `windows_path_to_msys()`。

不要让 Hermes 使用 WSL bash。WSL 的 `/mnt/d/...` 路径和 Git Bash 的 `/d/...` 路径不兼容，可能导致文件被写到 WSL 文件系统内部。

## 会话 CWD 和临时文件

`LocalEnvironment` 在 Windows 上会额外处理：

- 初始 CWD 转为 `/d/Code/...` 形式，确保 bash 的 `cd` 可靠。
- 会话快照和 CWD 临时文件放在 `%LOCALAPPDATA%\Temp\hermes\`。
- 同时保存 Windows 路径和 MSYS 路径，方便 Python 与 bash 共同访问。

## 危险命令拦截

Git Bash 下某些命令会遍历整个 Windows 根目录或卡住，Hermes 会拦截：

- `find /`
- `find /home`
- `ls -R /`

请改为指定具体路径，例如：

```powershell
find /d/Doc -name '*.md'
```

## 进程管理

Windows 不支持 `os.kill(pid, 0)` 和 `signal.SIGKILL`，Hermes 使用以下替代：

- 进程存活检查：`psutil.pid_exists()` 或 `tasklist`
- 强制终止：`taskkill /PID <pid> /T /F`

## 已知限制

以下功能在 Windows 上未经充分测试：

- Discord 语音频道
- WhatsApp bridge
- Docker / SSH / Modal / Daytona terminal 后端
- RL 训练（`tinker-atropos`）

## Windows 适配摘要

`docs/winodws_support/代码修改总结_*.md` 记录的核心优化可以归为以下几类：

1. **Git Bash 与路径兼容**
   - 优先探测 Git for Windows 的 `bash.exe`，最后才回退到 `PATH`。
   - 过滤 `C:\Windows\System32\bash.exe` / `Sysnative\bash.exe` 这类 WSL 启动器，避免 Hermes 收到 `/mnt/d/...` 路径。
   - 在 `LocalEnvironment` 中把 Windows CWD 转成 MSYS 路径给 bash 使用，同时保存 Windows 路径给 Python `open()` / `os.unlink()` 使用。
   - Windows 临时目录统一转换成 MSYS 形式，保证 bash 能写入 snapshot / cwd 文件。
   - 后续同步中融合了上游 `expanduser` 和 cwd 失效自动恢复逻辑：先把 MSYS CWD 转回 Windows 路径做存在性检查，再同步写回 MSYS 路径。

2. **终端输出与进程管理**
   - Windows 管道读取不再使用 `select.select()`，改为 `proc.stdout.buffer.read1()`，修复 terminal 工具输出为空的问题。
   - PID 文件读写、`taskkill` 调用、进程状态检查加入 Windows 兼容处理。
   - Gateway 重启标记采用原子写入，减少 Windows 文件锁冲突。

3. **UTF-8 编码修复**
   - 大量 `subprocess.run(..., text=True)` 调用补充 `encoding="utf-8", errors="replace"`，避免中文 Windows 默认 GBK 解码导致 Gateway / CLI 崩溃。
   - `hermes_cli/main.py` 对 stdout / stderr 做 UTF-8 重配置。
   - `tui_gateway/entry.py` 和 `slash_worker.py` 对 stdin / stdout / stderr 全量 UTF-8 重配置，修复中文输入被解码成乱码的问题。
   - `tui_gateway/transport.py` 直接向底层 buffer 写 UTF-8 字节，绕过可能被 Rich 或 TextIOWrapper 带回 GBK 的编码层。
   - npm、plugin install / update、`which`、`systemctl` 等子进程调用在后续上游重构中继续保留 UTF-8 参数。

4. **Dashboard / TUI Chat**
   - `hermes_cli/pty_bridge.py` 增加 Windows ConPTY 后端，通过 `pywinpty` 支持 Dashboard Chat 嵌入真实 TUI。
   - Dashboard 启动 TUI 时传递 `HERMES_PYTHON`，确保 Node 子进程使用当前虚拟环境里的 Python，避免找不到 `tui_gateway`。
   - 最初用 ephemeral session 避免 Dashboard Chat 侧边栏制造空的无标题会话，后续被上游更通用的 lazy session creation 替代。
   - 与上游 TUI 长会话性能、stdio 半关闭管道、生产模式 React、冷启动优化等改动合并时，保留 Windows 编码和 ConPTY 补丁。

5. **危险命令与安全拦截**
   - 在 `tools/approval.py` 中拦截 `find /`、`find /home`、`ls -R /` 等会在 Git Bash 下遍历整个 Windows 根目录的命令。
   - 后续与上游 hardline blocklist、危险模式预编译等改动合并，Windows 专用拦截规则继续保留。

6. **前端与依赖构建**
   - npm 子进程统一 UTF-8 编码，避免 Windows 控制台输出造成解码失败。
   - 04-29 同步时修复 Web 构建依赖：将 `@nous-research/ui` 锁到稳定版本，消除当时的 TypeScript 构建错误。

7. **上游同步时保留的 Windows 补丁**
   - 04-27、04-29、04-30、05-01、05-07 多次同步上游时，主要工作是解决冲突并保留上述 Windows 补丁。
   - 05-01 还合入了上游新增的 ACP WSL cwd 规范化，以及 Gateway 原子写入 / Windows 锁修复。
   - 05-07 合并时继续保留 ConPTY、MSYS 路径转换、UTF-8 subprocess 编码、plugin 安装编码、cwd 恢复等补丁。

更详细的移植记录见 [../winodws_support/](../winodws_support/)。
