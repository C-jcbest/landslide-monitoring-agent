# 002 前端会话与消息渲染轻量修复

## 背景

前端联调测试中发现四类直接影响交互的问题：

1. 左侧会话列表的重命名、删除按钮长期可见，干扰列表扫描。
2. AI 流式生成时消息看起来连续，但完成并同步历史后会拆成多个 assistant 气泡。
3. 生成过程中缺少明确状态提示，用户无法判断系统是否仍在处理。
4. Markdown 表格、列表等格式渲染不符合预期，尤其是天气汇总表格。

本轮按“先不做复杂功能”的约束，只修复当前交互和前后端联通中的高影响问题，不引入移动端 Drawer、CI 重构或完整工具事件流。

## 目标

1. **会话操作按钮降噪**：左侧会话的重命名、删除按钮默认隐藏，仅在鼠标 hover 或键盘 focus-within 时显现，并保持键盘可访问。
2. **AI 消息不再拆分**：后端历史读取时合并连续 assistant 消息，避免生成完成后从一个回复拆成多个气泡。
3. **生成中状态明确**：流式生成时在聊天区显示明确的“正在生成回复...”状态；如前端收到工具状态事件，则显示工具状态摘要。
4. **Markdown 渲染正确**：前端使用 GitHub Flavored Markdown 支持表格，并补充消息内 Markdown 样式，避免表格撑破气泡。
5. **流式请求更稳健**：前端流式解析能处理服务端错误事件、无 `done: true` 的提前断流和 Abort 信号，避免界面卡死。
6. **会话切换隔离**：切换会话、新建会话、退出登录时终止旧请求，并用当前会话引用阻止旧回调污染新会话。
7. **输入长度限制**：普通输入框和人工干预输入框限制为 3000 字符，并显示计数器。

## 非目标

1. 不在本轮实现移动端侧边栏 Drawer、Backdrop、`100dvh` 布局重构。
2. 不在本轮把后端流式实现改为 `astream_events(version="v2")`，因此真实工具开始/结束事件仍属于后续任务。
3. 不在本轮修改 GitHub Actions 增加前端 CI job。
4. 不改变数据库 Schema、认证流程或核心业务规则。
5. 不做复杂的新功能或大范围视觉重设计。

## 技术方案

- **后端历史合并**
  - 在 `app/core/langgraph/graph.py` 的历史消息处理逻辑中，过滤空内容，仅保留 `user` 和 `assistant`。
  - 对连续的 `assistant` 消息使用空行合并，确保一次 AI 回复在前端表现为一个气泡。
  - 中断恢复时通过 `graph.aupdate_state` 显式写入用户的人工干预回复，避免刷新后丢失。

- **后端 SSE 外层协议**
  - `StreamResponse` 增加 `event`、`tool_name`、`tool_input`、`error` 字段。
  - FastAPI SSE 包装层发送 `token`、`done`、`error` 事件；真实 `tool_start/tool_end` 事件暂不在本轮产生。

- **前端流式与并发**
  - `streamChat` 支持 `AbortSignal`，解析 `event:error` 和 `error` 字段。
  - 如果流结束前没有收到 `done: true`，触发错误回调。
  - `App.tsx` 使用 `activeSessionRef`、`fetchAbortControllerRef`、`streamAbortControllerRef` 隔离旧请求。
  - 发送普通消息和人工干预回复时，只向后端提交最新一条用户消息。

- **前端交互与 Markdown**
  - `Sidebar` 会话操作按钮默认 `opacity-0` 且 `pointer-events-none`，hover/focus-within 后恢复可见和可点击。
  - `ChatWindow` 的流式气泡显示 `Loader2` 和生成状态文案。
  - 新增 `MarkdownMessage` 组件，接入 `remark-gfm`，并补充 `.message-markdown` 表格、列表、代码块等样式。
  - 普通输入框和人工干预输入框增加 3000 字符限制与计数器。

## 验收

- [x] 左侧会话操作按钮默认隐藏，鼠标 hover 后显示；键盘 focus-within 时仍可访问。
- [x] 历史同步后连续 assistant 消息合并为一个气泡，不再把同一轮回答拆成多个气泡。
- [x] 流式生成期间显示明确的生成状态标志。
- [x] Markdown 表格渲染为真实 table 元素，并在气泡内横向滚动，不撑破布局。
- [x] 前端能识别 SSE 错误事件和提前断流，并结束 loading 状态。
- [x] 切换会话或退出登录时旧请求被 Abort，旧会话回调不会污染当前会话。
- [x] 普通输入框和人工干预输入框都有 3000 字符限制和计数器。
- [x] `git status` 不再因 `frontend/node_modules`、`frontend/.npm-cache`、`frontend/dist` 产生缓存污染。

## 后续任务

- [ ] 如需展示真实工具调用进度，将 `get_stream_response` 改为 `astream_events(version="v2")` 并产出 `tool_start/tool_end`。
- [ ] 如需移动端体验，单独实现侧边栏 Drawer、Backdrop 和 `100dvh` 布局。
- [ ] 如需 CI 门禁，单独更新 GitHub Actions，增加 Node 环境、Vitest 和 Vite build。
- [ ] 如需更稳定的 Markdown 输出格式，继续优化后端提示词，要求模型输出合法 GFM 表格。

## 待确认问题

- 删除最后一个活动会话且无剩余会话时，当前实现会创建新会话；是否改为停留在空白欢迎状态，需要产品口径确认。
