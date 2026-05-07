# Profile 配置示例

本目录提供一组已经去敏的 Hermes Windows profile 配置示例，来源于本机实际配置文件：

```text
docs/windows/profile-config-examples/
├── default/
│   ├── .env.example
│   └── config.yaml
├── belbin/
│   ├── .env.example
│   └── config.yaml
├── goldie/
│   ├── .env.example
│   └── config.yaml
├── mem/
│   ├── .env.example
│   └── config.yaml
└── turing/
    ├── .env.example
    └── config.yaml
```

## 去敏规则

- `.env` 文件中的所有赋值都替换为 `<REDACTED_SECRET>`。
- `config.yaml` 中包含 `api_key`、`token`、`secret`、`password`、`webhook`、`cookie`、`dsn` 等敏感字段名的值会替换为 `<REDACTED_SECRET>`。
- `C:\Users\gotmo`、`/c/Users/gotmo` 等本机用户路径会替换为 `C:\Users\<用户名>` 或 `/c/Users/<用户名>`。

这些文件只能作为结构参考，不能直接复制后运行。使用前需要填入你自己的 API key、Bot token、路径、端口和 profile 设置。

## 对应关系

| 示例目录 | 实际配置位置 |
|----------|--------------|
| `default/` | `C:\Users\<用户名>\.hermes\` |
| `belbin/` | `C:\Users\<用户名>\.hermes\profiles\belbin\` |
| `goldie/` | `C:\Users\<用户名>\.hermes\profiles\goldie\` |
| `mem/` | `C:\Users\<用户名>\.hermes\profiles\mem\` |
| `turing/` | `C:\Users\<用户名>\.hermes\profiles\turing\` |

## 使用方式

参考 default profile：

```powershell
notepad C:\Users\<用户名>\.hermes\config.yaml
notepad C:\Users\<用户名>\.hermes\.env
```

参考指定 profile：

```powershell
notepad C:\Users\<用户名>\.hermes\profiles\turing\config.yaml
notepad C:\Users\<用户名>\.hermes\profiles\turing\.env
```

配置后可以用以下命令检查：

```powershell
hermes doctor
hermes -p turing doctor
hermes profile list
```

多实例和 Dashboard 端口说明见 [Profile 与多实例](profiles-and-multi-instance.md)。

## 中国大陆用户的 Telegram 代理

如果在中国大陆使用 Telegram Gateway，通常需要给 Telegram bot 配置代理。示例 `.env.example` 中的 `TELEGRAM_PROXY` 是这个用途：

```env
TELEGRAM_PROXY=socks5://127.0.0.1:12334
```

这里的 `12334` 是本机代理软件的 SOCKS5 监听端口。比如使用 Hiddify 时，如果它的本地透明代理 / SOCKS5 端口是 `12334`，就可以这样写；如果你的 Hiddify、Clash、v2rayN 或其他代理软件使用了不同端口，请改成实际端口。

常见写法：

```env
TELEGRAM_PROXY=socks5://127.0.0.1:<你的 SOCKS5 端口>
```

如果代理需要用户名和密码：

```env
TELEGRAM_PROXY=socks5://<用户名>:<密码>@127.0.0.1:<你的 SOCKS5 端口>
```

每个启用 Telegram 的 profile 都需要在自己的 `.env` 中配置。例如：

```text
C:\Users\<用户名>\.hermes\.env
C:\Users\<用户名>\.hermes\profiles\turing\.env
C:\Users\<用户名>\.hermes\profiles\belbin\.env
```

配置后重启对应的 Gateway：

```powershell
hermes gateway run
hermes -p turing gateway run
```
