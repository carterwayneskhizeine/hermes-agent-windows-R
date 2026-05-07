# Web Dashboard /chat 页面额外创建 TUI 会话问题

> 日期：2026-05-01
>
> 环境：Windows 11 Pro, hermes dashboard --tui, 访问 http://127.0.0.1:9119

## 问题描述

每次访问 web dashboard 的 `/chat` 页面（包括从 sessions 页面 resume 一个历史会话），都会**额外创建一个新的空 TUI 会话**。被 resume 的会话本身能正常恢复（对话内容不丢失），但在 `/sessions` 页面会看到多出一个空的 TUI 会话。

具体表现：
- 从 `/sessions` 点击某个会话的 ▶ (resume in chat) 按钮 → 跳转到 `/chat?resume=<id>` → 会话成功恢复 → 但同时产生了一个新的空会话
- 直接刷新 `/chat` 页面 → 也会产生一个新的空会话
- 结果：`/sessions` 页面会不断积累空会话

## 复现步骤

1. 启动 `hermes dashboard`
2. 在 `/chat` 页面进行一些对话
3. 切换到 `/sessions` 页面 → **此时已经能看到一个额外的新空会话**
4. 点击刚才对话的会话的 ▶ 按钮，跳转到 `/chat?resume=<id>`
5. 被选中的会话正常恢复，对话内容都在
6. 再次切回 `/sessions` 页面 → **又多了一个新的空会话**

## 架构概述

Web dashboard 的 chat 页面不是独立前端应用，而是**嵌入式 TUI**：

```
浏览器 (xterm.js)
  ↕ WebSocket (/api/pty)
后端 web_server.py (FastAPI)
  ↕ PTY bridge (pywinpty on Windows)
TUI Node.js 进程 (Ink-based React CLI)
  ↕ RPC
Gateway (会话管理 / LLM API)
```

浏览器通过 WebSocket 连接到后端 `/api/pty`，后端为此 spawn 一个 TUI 子进程（Node.js + Ink），在 PTY 中运行。**每个 WebSocket 连接对应一个独立的 TUI 进程。** TUI 进程启动时默认调用 `newSession()` 创建新会话，只有收到 `HERMES_TUI_RESUME` 环境变量时才走 `resumeById()`。

## 根因分析

核心问题：**ChatPage 在 dashboard 加载时就挂载并创建 PTY 连接，不管用户是否真的在 /chat 页面。**

### 1. ChatPage 持久挂载（`web/src/App.tsx` 第 576-602 行）

```tsx
// ChatPage 在 Routes 外部渲染，dashboard 加载时就挂载
{embeddedChat && !chatOverriddenByPlugin && (
  <div
    data-chat-active={isChatRoute ? "true" : "false"}
    className={cn(
      "min-h-0 min-w-0",
      isChatRoute ? "flex flex-1 flex-col" : "hidden",  // hidden 但仍然挂载
    )}
    aria-hidden={!isChatRoute}
  >
    <ChatPage isActive={isChatRoute} />
  </div>
)}
```

ChatPage 在 dashboard 启动时立即挂载。即使用户在 `/sessions` 页面（ChatPage 是 `hidden` 状态），组件已经存在。

### 2. WS Effect 不依赖 isActive（`web/src/pages/ChatPage.tsx`）

```tsx
// 第 243 行：effect 不检查 isActive，只要 host 存在就建连
useEffect(() => {
  const host = hostRef.current;
  if (!host) return;
  // ...
  const url = buildWsUrl(token, resumeRef.current, channel);
  const ws = new WebSocket(url);
  // ...
}, [channel]);  // 依赖只有 channel，没有 isActive
```

**组件一挂载就立即创建 WebSocket → 后端 spawn PTY → TUI 启动 → `newSession()` → 产生空会话。** 此时用户可能还在 `/sessions` 页面，根本没进入 `/chat`。

### 3. 完整的时序问题

```
Dashboard 加载
  → App.tsx 渲染，ChatPage 挂载（hidden）
  → WS effect 触发，WebSocket 连接到 /api/pty（无 resume 参数）
  → 后端 spawn TUI 进程，HERMES_TUI_RESUME 为空
  → TUI 调用 newSession() → 创建空会话 ①

用户在 /sessions 页面点击 resume
  → navigate('/chat?resume=<session_id>')
  → ChatPage 变为 visible，但组件没有重新挂载

如果 resume 参数传递成功：
  → 旧 WS 断开 → 新 WS 带着参数重连
  → 后端 spawn 新 TUI 进程，HERMES_TUI_RESUME=<session_id>
  → TUI 调用 resumeById() → 恢复旧会话 ✓
  → 但空会话 ① 已经存在于 sessions 列表中

```

### 4. resume 参数传递（已修复）

原始代码用 `useRef` 保存 resume 参数，只在首次挂载时读取：

```tsx
const resumeRef = useRef<string | null>(searchParams.get("resume"));
```

首次挂载时 URL 没有 `?resume=` 参数，所以 `resumeRef.current` 始终是 `null`。

已改为 `useState` + effect 监听 `searchParams`，**修复生效**：

```tsx
const [resumeId, setResumeId] = useState<string | null>(
  searchParams.get("resume"),
);

useEffect(() => {
  setResumeId(searchParams.get("resume"));
}, [searchParams]);

// WS effect 依赖也更新了
}, [channel, resumeId]);
```

现在从 sessions 页面点击 resume 后，URL 能正确变为 `/chat?resume=<session_id>`，WS effect 重新建连并带上 resume 参数，TUI 能正确恢复指定会话。

**但根本问题（多余空会话）仍然存在**，因为 resume 参数传递只解决了"恢复哪个会话"的问题，没有解决"dashboard 加载时就创建空会话"的问题。

### 5. 配置方案（部分有效）

```yaml
# ~/.hermes/config.yaml
display:
  tui_auto_resume_recent: true
```

这能让 TUI 自动恢复最近的会话而不是创建新的，但：
- 无法指定恢复哪个特定会话
- 仍然无法解决"dashboard 加载时就创建多余会话"的根本问题

## 相关文件清单

| 文件 | 关键位置 | 作用 |
|------|----------|------|
| `web/src/App.tsx` | 第 576-602 行 | ChatPage 持久挂载（hidden 但不卸载） |
| `web/src/pages/ChatPage.tsx` | 第 149 行 | resume 参数存储（原 useRef） |
| `web/src/pages/ChatPage.tsx` | 第 243-630 行 | WS effect，不检查 isActive |
| `web/src/pages/ChatPage.tsx` | 第 486 行 | `buildWsUrl(token, resumeRef.current, channel)` |
| `web/src/pages/ChatPage.tsx` | 第 621 行 | effect 依赖 `[channel]`，无 resume/isActive |
| `web/src/pages/SessionsPage.tsx` | 第 356-370 行 | resume 按钮，`navigate('/chat?resume=...')` |
| `hermes_cli/web_server.py` | 约第 2741 行 | `/api/pty` WS 端点，读取 resume 参数 |
| `hermes_cli/web_server.py` | 约第 2654 行 | `_resolve_chat_argv()` 设置 `HERMES_TUI_RESUME` |
| `ui-tui/src/config/env.ts` | 第 3 行 | `STARTUP_RESUME_ID = process.env.HERMES_TUI_RESUME` |
| `ui-tui/src/app/createGatewayEventHandler.ts` | 约第 181 行 | resume vs newSession 分支 |

## 可能的解决方向

### 方向 A：延迟 PTY 连接到用户实际进入 /chat 时

在 WS effect 中加入 `isActive` 守卫，只有用户真的在 `/chat` 页面时才创建连接：

```tsx
useEffect(() => {
  const host = hostRef.current;
  if (!host || !isActive) return;  // 增加 isActive 检查
  // ... WebSocket 创建 ...
}, [channel, isActive, resumeId]);
```

这样 dashboard 加载时不会创建空会话，只有用户真正进入 chat 页面才建连。

### 方向 B：将 ChatPage 从持久挂载改为路由内挂载

让 `/chat` 路由直接渲染 ChatPage，离开时卸载：

```tsx
<Routes>
  <Route path="/chat" element={<ChatPage isActive={true} />} />
  {/* ... */}
</Routes>
```

每次导航到 `/chat` 都会重新挂载，`searchParams.get("resume")` 能正确读到 URL 参数。代价是离开 chat 页面时 PTY 进程被销毁。

### 方向 C：改用路由 state 或全局变量传递 resume ID

避免依赖 `useSearchParams`，改用 `navigate('/chat', { state: { resume } })` 或 `window.__HERMES_RESUME_ID__`：

```tsx
// SessionsPage.tsx
navigate('/chat', { state: { resume: session.id } });

// ChatPage.tsx
const location = useLocation();
const resumeId = location.state?.resume ?? null;
```

### 方向 D：后端维护 session 状态

在 `web_server.py` 中追踪 channel → session 映射。新建连接时如果已有活跃 session，自动传 `HERMES_TUI_RESUME` 给 TUI。
