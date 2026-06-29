# 项目状态记录

### 2026-06-23 - 新功能文档与 TDD 门禁

- Type: Constraint
- Area: docs | tests | backend
- Record: 新功能采用 `specs → designs → tests → TDD` 的阶段流程；三个文档使用相同编号和名称。设计与测试计划均需经用户确认，才能进入下一阶段。
- Prevention: 开发新功能前先阅读 `AGENTS.md` 的“新功能开发流程（Spec 驱动 + TDD）”，严格遵守阶段门禁、分支、测试与用户验收规则。
- Links: `AGENTS.md`、`docs/specs/`、`docs/designs/`、`docs/tests/`

### 2026-06-29 - 002 轻量修复文档范围同步

- Type: Doc Sync
- Area: docs | frontend | backend | tests
- Record: `002-frontend-bugfixes` 当前权威范围是会话操作按钮降噪、AI 消息合并、生成中标志、Markdown/GFM 渲染、SSE 错误与断流处理、会话并发隔离、输入长度限制和缓存忽略；移动端 Drawer、真实 `astream_events` 工具事件流、前端 CI job 暂属后续任务。
- Prevention: 用户明确要求“不先做复杂功能”或缩小范围时，必须同步更新 spec、design 和测试计划；已完成项、未完成项、延期项要分开记录，不得把延期项留在当前验收清单中。
- Links: `AGENTS.md`、`docs/specs/002-frontend-bugfixes.md`、`docs/designs/002-frontend-bugfixes.md`、`docs/tests/002-frontend-bugfixes.md`

### 2026-06-29 - 文档代码不一致需用户决策

- Type: Correction
- Area: docs | agent
- Record: 发现文档与代码实现不一致时，代理不应默认在同一轮自动修正文档或代码；应先报告差异、影响范围和可选处理路径，由用户决定下一步。
- Prevention: 后续审查或实现中遇到 docs/code drift，先暂停相关同步动作并询问用户确认，除非用户已明确授权按某个方向修改。
- Links: `AGENTS.md`
