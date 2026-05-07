# Profile 与多实例

Hermes 支持 profile 隔离。每个 profile 拥有独立的配置、记忆、会话和技能，数据位于：

```text
~/.hermes/profiles/<name>/
```

默认 profile 使用：

```text
~/.hermes/
```

## 创建和使用 Profile

```powershell
hermes profile create turing --clone
hermes profile list
hermes profile info turing
```

在 Windows PowerShell 中推荐使用 `-p` 或 `--profile`：

```powershell
hermes -p turing setup
hermes -p turing chat
hermes -p turing gateway run

hermes --profile=turing setup
```

也可以切换默认 profile：

```powershell
hermes profile use turing
hermes setup
hermes chat
hermes profile use default
```

## Dashboard 使用 Profile

`dashboard` 子命令通常通过 `HERMES_HOME` 选择 profile：

```powershell
$env:HERMES_HOME = "C:\Users\<用户名>\.hermes\profiles\turing"
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

`$env:HERMES_HOME` 只在当前 PowerShell 窗口有效。关闭窗口后失效。

## 同时运行多个 Agent

每个 Agent 实例需要独立的 API Server 端口。如果使用 Telegram，还需要独立的 Bot Token，否则会出现端口冲突或 Telegram 轮询冲突。

API Server 端口需要写在平台配置的 `extra.port` 中，不要直接写在 `api_server.port`：

```yaml
gateway:
  platforms:
    api_server:
      enabled: true
      extra:
        port: 8643
```

示例启动方式：

```powershell
# default Gateway
hermes gateway run

# default Dashboard
python -m hermes_cli.main dashboard --no-open --tui

# turing Gateway
hermes -p turing gateway run

# turing Dashboard
$env:HERMES_HOME = "C:\Users\<用户名>\.hermes\profiles\turing"
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

如果需要一键启动多个 profile，优先使用根目录的 `start-hermes.ps1`，参考 [psmux 一键启动](psmux-startup.md)。

## 管理命令

```powershell
hermes profile list
hermes profile info turing
hermes profile rename turing ada
hermes profile delete turing
hermes -p turing model
hermes -p turing doctor
```
