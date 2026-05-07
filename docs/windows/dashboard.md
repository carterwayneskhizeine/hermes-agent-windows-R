# Dashboard Web UI

Dashboard Web UI 默认运行在：

```text
http://127.0.0.1:9119
```

## 启动 Dashboard

```powershell
python -m hermes_cli.main dashboard --no-open --tui
```

参数说明：

| 参数 | 说明 |
|------|------|
| `--no-open` | 不自动打开浏览器 |
| `--tui` | 在 Chat 页嵌入完整 TUI 体验 |
| `--port <port>` | 指定 Dashboard 端口 |

## 首次构建前端

如果首次运行或修改了 `web/` 前端代码，请先构建：

```powershell
cd web
npm install
npm run build
cd ..
```

构建产物由 Python Dashboard 服务托管。只使用已构建的 Web UI 时，不需要运行 `npm run dev`。

## 多 Profile Dashboard

Dashboard 可通过 `HERMES_HOME` 绑定到指定 profile：

```powershell
$env:HERMES_HOME = "C:\Users\<用户名>\.hermes\profiles\turing"
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

多个 Dashboard 必须使用不同端口。

## Chat 页面

Dashboard 的 Chat 页嵌入真实的 `hermes --tui`，不是 React 重写版聊天界面。主聊天 transcript、输入框、slash command 行为都属于 TUI；React 只负责页面外围结构。
