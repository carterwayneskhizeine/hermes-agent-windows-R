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

当前 Windows fork 的核心适配包括：

1. 全局 subprocess 调用使用 UTF-8 编码和容错解码，避免中文 Windows GBK 崩溃。
2. Windows 终端输出捕获使用兼容方案，修复工具输出为空的问题。
3. TUI stdio 强制 UTF-8，修复中文输入乱码。
4. 使用 ConPTY 支持 Dashboard Chat 嵌入 TUI。
5. Dashboard 侧边栏使用 ephemeral session，避免 Sessions 页出现空的无标题会话。

更详细的移植记录见：

- [代码修改总结](../winodws_support/代码修改总结_2026-04-26.md)
- [Windows 路径测试经验](../winodws_support/Windows路径测试经验.md)
- [Windows Chat 问题记录](../winodws_support/WINDOWS_CHAT_ISSUES.md)
