# start-hermes.ps1 — 一键启动全部 10 个 Hermes 服务 (psmux 独立 session)
$projectDir = "D:\Code\goldie-fork\hermes-agent"
$activate   = ".\venv\Scripts\Activate.ps1"

# 清理旧 session
"sessions" | ForEach-Object { psmux kill-session -t $_ 2>$null }
@("default-gw","default-web","turing-gw","turing-web","belbin-gw","belbin-web","mem-gw","mem-web","goldie-gw","goldie-web") |
  ForEach-Object { psmux kill-session -t $_ 2>$null }

# ── 1. default Gateway ──
psmux new-session  -d -s default-gw
psmux send-keys -t default-gw '$env:HERMES_HOME = "C:\Users\gotmo\.hermes"' Enter
psmux send-keys -t default-gw "cd $projectDir; $activate; hermes gateway run" Enter
Start-Sleep -Seconds 12   # wait for Telegram polling to establish before next gateway

# ── 2. default Web UI (port 9119) ──
psmux new-session  -d -s default-web
psmux send-keys -t default-web '$env:HERMES_HOME = "C:\Users\gotmo\.hermes"' Enter
psmux send-keys -t default-web "cd $projectDir; $activate; python -m hermes_cli.main dashboard --no-open --tui" Enter

# ── 3. turing Gateway ──
psmux new-session  -d -s turing-gw
psmux send-keys -t turing-gw "cd $projectDir; $activate; hermes -p turing gateway run" Enter
Start-Sleep -Seconds 12

# ── 4. turing Web UI (port 9120) ──
psmux new-session  -d -s turing-web
psmux send-keys -t turing-web '$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\turing"' Enter
psmux send-keys -t turing-web "cd $projectDir; $activate; python -m hermes_cli.main dashboard --no-open --tui --port 9120" Enter

# ── 5. belbin Gateway ──
psmux new-session  -d -s belbin-gw
psmux send-keys -t belbin-gw "cd $projectDir; $activate; hermes -p belbin gateway run" Enter
Start-Sleep -Seconds 12

# ── 6. belbin Web UI (port 9121) ──
psmux new-session  -d -s belbin-web
psmux send-keys -t belbin-web '$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\belbin"' Enter
psmux send-keys -t belbin-web "cd $projectDir; $activate; python -m hermes_cli.main dashboard --no-open --tui --port 9121" Enter

# ── 7. mem Gateway ──
psmux new-session  -d -s mem-gw
psmux send-keys -t mem-gw "cd $projectDir; $activate; hermes -p mem gateway run" Enter
Start-Sleep -Seconds 12

# ── 8. mem Web UI (port 9122) ──
psmux new-session  -d -s mem-web
psmux send-keys -t mem-web '$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\mem"' Enter
psmux send-keys -t mem-web "cd $projectDir; $activate; python -m hermes_cli.main dashboard --no-open --tui --port 9122" Enter

# ── 9. goldie Gateway ──
psmux new-session  -d -s goldie-gw
psmux send-keys -t goldie-gw "cd $projectDir; $activate; hermes -p goldie gateway run" Enter
Start-Sleep -Seconds 12

# ── 10. goldie Web UI (port 9123) ──
psmux new-session  -d -s goldie-web
psmux send-keys -t goldie-web '$env:HERMES_HOME = "C:\Users\gotmo\.hermes\profiles\goldie"' Enter
psmux send-keys -t goldie-web "cd $projectDir; $activate; python -m hermes_cli.main dashboard --no-open --tui --port 9123" Enter

# attach 到第一个
psmux attach -t default-gw
