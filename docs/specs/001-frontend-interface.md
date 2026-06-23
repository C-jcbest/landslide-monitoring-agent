# 001 前端页面开发

## 背景

当前 Landslide Monitoring Agent 具备完整的 FastAPI 异步后端服务，提供 JWT 认证、会话（Session）管理、基于 LangGraph 的 Agent 有状态对话工作流（包含 DuckDuckGo 搜索工具与 `ask_human` 人机交互工具）。
为了向用户提供直观、高效的交互体验，我们需要参考 `google-gemini/gemini-fullstack-langgraph-quickstart` 的前端设计，开发一个现代化、高颜值的 React (Vite) 独立前端页面。

## 目标

1. **前端架构**：在项目根目录下创建独立的 `/frontend` React + TypeScript + Vite 项目，使用 `npm run dev` 独立运行于 `5173` 端口，通过 API 与后端通信。
2. **用户认证（JWT）**：支持注册与登录界面，成功后将 JWT Token 妥善持久化于 `localStorage`，并在后续请求的 Header 中携带。
3. **会话管理（Sidebar）**：
   - 提供左侧边栏，支持展示历史会话列表。
   - 支持创建新会话、重命名会话、删除会话（对接后端的 Session API）。
   - 展示当前登录的用户信息，提供“登出”选项。
4. **对话窗口与流式传输（Main Chat Panel）**：
   - 支持流式输出（Streaming Response），对接 `/chatbot/chat/stream` 接口。
   - 支持优雅渲染 Markdown 格式的 Agent 消息。
5. **Agent 思考与工具执行状态**：
   - 能够展示 Agent 运行中的中间状态（如 DuckDuckGo 搜索状态、思考过程等），提供更具响应感的即时反馈。
6. **人机交互（Human-in-the-loop）**：
   - 当 Agent 调用 `ask_human` 导致 Graph 挂起时，前端以定制卡片的形式提示用户输入，并允许用户提交回复以恢复 Graph 运行。
7. **极致视觉与动态体验**：
   - 采用精致的深色模式（Premium Dark Mode），融合毛玻璃效果（Glassmorphism）、微动画和优雅渐变。

## 非目标

1. **复杂数据可视化看板**：Prometheus / Grafana 指标不在前端页面中进行复杂的图表绘制。
2. **多模型/参数调参界面**：本阶段不提供切换 LLM 模型或调整 Temperature 等高级参数的 UI。
3. **高级安全流**：如找回密码、绑定邮箱、双因子认证（MFA）等。

## 技术方案

1. **开发工具与框架**：
   - 使用 Vite 创建 React + TypeScript 模板项目。
   - 使用 Vanilla CSS（纯原生 CSS，利用变量、Flex/Grid、Transitions）实现符合 Web 规范的高级感 UI。
2. **核心组件划分**：
   - `AuthScreen`：登录/注册切换表单。
   - `Sidebar`：会话列表（创建、删除、重命名）、用户面板、登出按钮。
   - `ChatWindow`：聊天记录（Markdown 渲染）、输入栏。
   - `ThinkingIndicator`/`ToolProgress`：Agent 工具执行状态指示器。
   - `HumanPromptCard`：针对 `ask_human` 状态的卡片。
3. **接口集成方式**：
   - 使用 `fetch` 读取 SSE（Server-Sent Events）流式响应，将文本块逐字追加到当前消息状态中。

## 验收

- [ ] 用户可以注册新账号，或使用已有账号登录，登录状态跨页面刷新不丢失。
- [ ] 侧边栏能正确载入、创建、重命名、删除会话，并能在会话间无缝切换，对话历史正确渲染。
- [ ] 聊天输入框发送消息后，Agent 能够流式逐字输出回答。
- [ ] 当 Agent 进行搜索等操作时，界面显示出工具执行状态指示。
- [ ] 当触发 `ask_human` 中断时，界面以突出卡片询问用户输入，并在提交后继续正常会话。
- [ ] 页面在主流浏览器中呈现完美的响应式毛玻璃/渐变深色风格，交互微动画顺畅。

## 待确认问题

- 无。
