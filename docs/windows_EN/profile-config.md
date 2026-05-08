# Profile Config Examples

This directory provides a set of sanitized Hermes Windows profile configuration examples based on real local config files:

```text
docs/windows_EN/profile-config-examples/
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

## Sanitization Rules

- All values in `.env` files are replaced with `<REDACTED_SECRET>`.
- Values of sensitive fields in `config.yaml` (including `api_key`, `token`, `secret`, `password`, `webhook`, `cookie`, `dsn`, etc.) are replaced with `<REDACTED_SECRET>`.
- Local user paths such as `C:\Users\gotmo` or `/c/Users/gotmo` are replaced with `C:\Users\<username>` or `/c/Users/<username>`.

These files are for structural reference only and cannot be used as-is. Before using them, fill in your own API keys, Bot tokens, paths, ports, and profile settings.

## Path Mapping

| Example Directory | Actual Config Location |
|-------------------|------------------------|
| `default/` | `C:\Users\<username>\.hermes\` |
| `belbin/` | `C:\Users\<username>\.hermes\profiles\belbin\` |
| `goldie/` | `C:\Users\<username>\.hermes\profiles\goldie\` |
| `mem/` | `C:\Users\<username>\.hermes\profiles\mem\` |
| `turing/` | `C:\Users\<username>\.hermes\profiles\turing\` |

## Usage

Reference the default profile:

```powershell
notepad C:\Users\<username>\.hermes\config.yaml
notepad C:\Users\<username>\.hermes\.env
```

Reference a specific profile:

```powershell
notepad C:\Users\<username>\.hermes\profiles\turing\config.yaml
notepad C:\Users\<username>\.hermes\profiles\turing\.env
```

After editing, verify with:

```powershell
hermes doctor
hermes -p turing doctor
hermes profile list
```

For multi-instance and Dashboard port details, see [Profiles & Multi-instance](profiles-and-multi-instance.md).

## Telegram Proxy for Users in Mainland China

If you use Telegram Gateway from mainland China, you typically need to configure a proxy for the Telegram bot. The `TELEGRAM_PROXY` field in the `.env.example` files serves this purpose:

```env
TELEGRAM_PROXY=socks5://127.0.0.1:12334
```

`12334` is the SOCKS5 listening port of your local proxy software. For example, if Hiddify's local SOCKS5 port is `12334`, use that value. Adjust the port to match your actual proxy client (Hiddify, Clash, v2rayN, etc.).

Common format:

```env
TELEGRAM_PROXY=socks5://127.0.0.1:<your-SOCKS5-port>
```

If the proxy requires a username and password:

```env
TELEGRAM_PROXY=socks5://<username>:<password>@127.0.0.1:<your-SOCKS5-port>
```

Each Telegram-enabled profile needs this configured in its own `.env`:

```text
C:\Users\<username>\.hermes\.env
C:\Users\<username>\.hermes\profiles\turing\.env
C:\Users\<username>\.hermes\profiles\belbin\.env
```

Restart the corresponding Gateway after configuring:

```powershell
hermes gateway run
hermes -p turing gateway run
```
