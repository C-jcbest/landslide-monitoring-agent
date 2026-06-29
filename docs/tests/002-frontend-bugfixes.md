# 002 前端会话与消息渲染轻量修复 — 测试计划

## Happy Path

1. **Markdown 表格渲染**
   - 层级：前端组件单元测试。
   - 文件：`frontend/src/components/__tests__/MarkdownMessage.test.tsx`。
   - 数据：包含 GFM 表头、分隔行和两行数据的天气表格。
   - 断言：
     - 页面存在 `role="table"`。
     - 表头“日期”渲染为 columnheader。
     - 单元格“2.3 mm”渲染为 table cell。
   - 对应验收：Markdown 表格正确渲染。

2. **SSE 正常流式输出**
   - 层级：前端服务单元测试。
   - 文件：`frontend/src/services/__tests__/api.test.ts`。
   - 数据：模拟两段 `data: {"content": "...", "done": false}` 和一个 `done: true`。
   - 断言：
     - `onChunk` 按顺序收到文本片段。
     - 收到 `done: true` 后调用 `onDone`。
     - 正常流程不调用 `onError`。
   - 对应验收：流式消息可正常完成并恢复界面状态。

3. **连续 assistant 消息合并**
   - 层级：后端单元测试。
   - 文件：`tests/unit/test_agent_workflows.py`。
   - 数据：一个用户消息后跟三条连续 `AIMessage`，再跟用户消息和 assistant 消息。
   - 断言：
     - 前三条连续 assistant 合并为一个 `assistant` 响应。
     - 不跨 user 消息继续合并。
   - 对应验收：AI 完成后不会拆分成多个气泡。

4. **生成状态显示**
   - 层级：前端组件测试和浏览器烟测。
   - 文件：`frontend/src/components/__tests__/ThinkingIndicator.test.tsx`，以及本地浏览器烟测。
   - 断言：
     - `ThinkingIndicator` 默认状态文本可渲染。
     - 传入自定义状态文本时可渲染。
     - 流式气泡中显示“正在生成回复...”。
   - 对应验收：生成中有明确标志。

## 边界场景

1. **SSE 服务端错误事件**
   - 层级：前端服务单元测试。
   - 文件：`frontend/src/services/__tests__/api.test.ts`。
   - 数据：`data: {"event":"error","error":"模型调用失败","done":true}`。
   - 断言：
     - `onError` 被调用一次。
     - 错误对象 message 为“模型调用失败”。
   - 对应验收：服务端错误不会被静默吞掉。

2. **SSE 提前断流**
   - 层级：前端服务单元测试。
   - 文件：`frontend/src/services/__tests__/api.test.ts`。
   - 数据：只返回 `done:false` 片段后关闭流。
   - 断言：
     - `onError` 被调用。
     - 错误信息为 `Stream ended before completion`。
   - 对应验收：无 `done:true` 的断流不会导致永久 loading。

3. **Abort 信号传递**
   - 层级：前端服务单元测试。
   - 文件：`frontend/src/services/__tests__/api.test.ts`。
   - 数据：创建 `AbortController` 并传入 `streamChat`。
   - 断言：
     - `fetch` 被调用时包含同一个 `signal`。
   - 对应验收：会话切换或退出登录具备取消旧请求的基础能力。

4. **侧边栏会话按钮 hover/focus**
   - 层级：浏览器烟测。
   - 数据：模拟一个后端会话并渲染侧边栏。
   - 断言：
     - hover 前操作按钮容器 `opacity` 为 `0`，`pointer-events` 为 `none`。
     - hover 后 `opacity` 为 `1`，`pointer-events` 为 `auto`。
   - 对应验收：左侧会话操作按钮只在需要时显现。

5. **输入长度限制**
   - 层级：代码审查和浏览器/组件验证。
   - 文件：`frontend/src/components/ChatWindow.tsx`、`frontend/src/components/HumanPromptCard.tsx`。
   - 断言：
     - 普通输入框和人工干预输入框均设置 `maxLength={3000}`。
     - 两处均显示 `current/3000` 计数。
   - 对应验收：输入长度受控。

## 失败场景

1. **流式解析失败后界面恢复**
   - 层级：前端服务单元测试 + `App.tsx` 状态逻辑审查。
   - 断言：
     - `streamChat` 错误进入 `onError`。
     - `App.tsx` 的错误回调会清理 `loading` 和 `toolStatus`。

2. **旧会话异步回调返回**
   - 层级：代码审查 + 浏览器烟测。
   - 断言：
     - 历史加载、流式 chunk、done、error、同步历史前均校验 `activeSessionRef`。
     - 会话切换、新建草稿、退出登录会 abort 旧请求。

3. **Markdown 内容过宽**
   - 层级：前端组件测试 + 浏览器烟测。
   - 断言：
     - 表格外层存在 `.markdown-table-wrap`。
     - 表格在气泡中横向滚动，不撑破布局。

## 测试层级、数据与依赖

- 前端测试框架：Vitest + Testing Library + jsdom。
- 前端依赖：`react-markdown`、`remark-gfm`。
- 后端测试框架：pytest。
- 浏览器验证：本地 Vite 服务 + Playwright 烟测，使用模拟后端接口返回会话和消息。

## 已执行验证

- `npm test`：通过。
- `npm run build`：通过。
- `make check`：通过。
- 浏览器烟测：通过。
- `uv run pytest tests/unit/test_agent_workflows.py tests/unit/test_graph_llm_and_session_naming.py -q`：未通过运行环境准备，原因是缺少 `pytest_asyncio`；不是当前代码断言失败。

## 验收标准映射

| 验收项 | 测试或验证 |
| --- | --- |
| 左侧会话操作按钮默认隐藏，hover/focus 后显示 | 浏览器烟测 |
| AI 完成后不拆分同一轮 assistant 消息 | `test_process_messages_merges_consecutive_assistant_messages` |
| 生成中有明确标志 | `ThinkingIndicator` 测试 + 浏览器烟测 |
| Markdown 表格正确渲染 | `MarkdownMessage.test.tsx` |
| SSE 错误事件可恢复 | `api.test.ts` |
| SSE 提前断流可恢复 | `api.test.ts` |
| Abort 信号传入 fetch | `api.test.ts` |
| 输入限制和计数器 | 代码审查 + 浏览器烟测 |
| 前端缓存不污染 Git 状态 | `git status` 检查 |

## 后续测试范围

- 真实 `tool_start/tool_end` 事件展示：等待后端改为 `astream_events(version="v2")` 后补充。
- 移动端 Drawer：等待功能实现后补充响应式和交互测试。
- GitHub Actions 前端 job：等待 workflow 更新后补充 CI 验证。
- 删除最后一个活动会话后的目标行为：等待产品确认后补充测试。
