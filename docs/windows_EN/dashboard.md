# Dashboard Web UI

The Dashboard Web UI runs at:

```text
http://127.0.0.1:9119
```

## Starting the Dashboard

```powershell
python -m hermes_cli.main dashboard --no-open --tui
```

Parameter reference:

| Flag | Description |
|------|-------------|
| `--no-open` | Do not auto-open the browser |
| `--tui` | Embed the full TUI experience in the Chat page |
| `--port <port>` | Specify a custom Dashboard port |

## Building the Frontend (First Time)

If this is your first run or you have modified the `web/` frontend code, build it first:

```powershell
cd web
npm install
npm run build
cd ..
```

The build output is served by the Python Dashboard server. You do not need to run `npm run dev` when using the pre-built Web UI.

## Multi-profile Dashboard

Bind a Dashboard to a specific profile via `HERMES_HOME`:

```powershell
$env:HERMES_HOME = "C:\Users\<username>\.hermes\profiles\turing"
python -m hermes_cli.main dashboard --no-open --tui --port 9120
```

Multiple Dashboard instances must use different ports.

## Chat Page

The Chat page in Dashboard embeds the real `hermes --tui` process — it is not a React-rewritten chat interface. The main chat transcript, input box, and slash command behavior all belong to the TUI; React only handles the outer page structure.
