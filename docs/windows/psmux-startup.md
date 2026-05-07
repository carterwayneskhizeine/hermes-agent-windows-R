# psmux 一键启动

本仓库根目录的 `start-hermes.ps1` 是一个基于 [psmux](https://github.com/psmux/psmux) 的 Windows PowerShell 示例脚本，用于一键启动多个 Hermes Gateway / Dashboard session。

这个脚本是本地定制命令行。使用前需要根据你的机器修改：

- 仓库绝对路径
- 虚拟环境路径，`venv` 或 `.venv`
- profile 名称
- Dashboard 端口
- 每个 profile 对应的 `HERMES_HOME`

## 安装 psmux

```powershell
winget install psmux
```

## 运行脚本

```powershell
.\start-hermes.ps1
```

常用管理命令：

```powershell
psmux list-sessions
psmux attach -t default-gw
psmux kill-session -t default-gw
```

## 给 AI 修改 start-hermes.ps1 的提示词

把下面这段交给 AI，并补全你的本机信息：

```text
请只修改当前仓库根目录下的 start-hermes.ps1，把它改成适合我 Windows PowerShell 环境的一键启动脚本。

目标：
- 使用 psmux 管理多个独立 session。
- 启动前先清理旧的同名 psmux session。
- 为每个 Hermes profile 启动一组服务：Gateway 和 Dashboard Web UI。
- Dashboard 使用 `python -m hermes_cli.main dashboard --no-open --tui` 启动，并为不同 profile 分配不同端口，避免冲突。
- Gateway 优先使用 `hermes -p <profile> gateway run`；default profile 使用 `hermes gateway run`。
- 如果 Dashboard 子命令不能直接使用 `-p`，请在对应 session 中设置 `$env:HERMES_HOME` 指向该 profile 的 Hermes home。
- 虚拟环境激活脚本使用当前仓库下的 `.\venv\Scripts\Activate.ps1`；如果仓库实际使用 `.venv`，请改为 `.\.venv\Scripts\Activate.ps1`。
- `$projectDir` 必须改为当前仓库的绝对路径。
- 最后 attach 到 default gateway session，或者输出可用的 `psmux attach -t <session>` 命令。

我的环境：
- 仓库路径：<填你的仓库绝对路径，例如 D:\Code\hermes-agent-windows-R>
- 默认 Hermes home：<填你的默认路径，例如 C:\Users\<用户名>\.hermes>
- 需要启动的 profiles：<填 profile 列表，例如 default,turing,belbin,mem,goldie>
- Dashboard 端口：<填端口映射，例如 default=9119,turing=9120,belbin=9121,mem=9122,goldie=9123>

约束：
- 不要修改 Hermes 核心代码。
- 不要删除我已有的注释，除非注释已经和新逻辑冲突。
- 修改后请说明每个 session 的名称、启动命令和访问地址。
```
