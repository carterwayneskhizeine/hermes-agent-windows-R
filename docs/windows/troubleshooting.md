# Windows 故障排查

## `hermes` 命令找不到

确认虚拟环境已激活，或直接使用完整路径：

```powershell
.\venv\Scripts\Activate.ps1
.\venv\Scripts\hermes.exe gateway run
```

## Git Bash 找不到

安装 Git for Windows，或手动指定：

```powershell
$env:HERMES_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"
```

## `write_file` 返回成功但文件没有创建

通常是 WSL bash 抢占了 Git Bash。让 AI 运行终端命令 `pwd`：

- 返回 `/d/Code/...`：Git Bash，正确。
- 返回 `/mnt/d/Code/...`：WSL bash，错误。

解决方式：安装 Git for Windows，或设置 `HERMES_GIT_BASH_PATH` 指向 Git Bash，然后重启 Hermes。

## `uv pip install` 失败

先检查版本：

```powershell
python --version
uv --version
```

Python 需要 3.12.x。

## `hermes doctor` 提示缺少 ripgrep

```powershell
winget install BurntSushi.ripgrep.MSVC
```

## API Server 端口冲突

查找占用端口的进程：

```powershell
netstat -ano | findstr :8642
```

终止进程：

```powershell
taskkill /PID <pid> /T /F
```

多 profile 同时运行时，请为每个 profile 配置不同的 `gateway.platforms.api_server.extra.port`。

## Dashboard 端口被占用

默认端口是 `9119`。换一个端口：

```powershell
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

## `HERMES_HOME` 设错

当前 PowerShell 窗口中清除：

```powershell
$env:HERMES_HOME = $null
```

或者关闭 PowerShell 窗口重开。全局环境变量需要在“系统属性 -> 环境变量”中修改。

## Web UI 显示 `Frontend not built`

重新构建前端：

```powershell
cd web
npm install
npm run build
cd ..
```

## `Gateway runtime lock is already held by another instance`

通常是已有 Gateway 仍在运行，或上次异常退出留下 runtime lock。

先查看是否已有进程：

```powershell
Get-Process | Where-Object { $_.ProcessName -match "python|hermes" }
```

如果确认没有 Gateway 运行，再删除对应 profile 下的 runtime lock。不要在另一个 Gateway 正在运行时删除 lock。
