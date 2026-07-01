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

### 2026-06-29 - 测试账号渐进式披露

- Type: Constraint
- Area: docs | tests | agent
- Record: 测试账号等敏感测试资料应通过测试说明文件渐进式披露；执行测试时先读对应 `docs/tests/{编号}-{功能名}.md`，只有涉及认证状态时才读取 `docs/tests/test-accounts.md`。
- Prevention: 后续验收、提交信息和评审结论不要重复暴露测试账号明文；需要说明账号来源时引用 `docs/tests/test-accounts.md`，不要把测试账号硬编码进业务代码或生产配置。
- Links: `AGENTS.md`、`docs/tests/test-accounts.md`

### 2026-06-29 - 功能测试与 LLM 评估分离

- Type: Correction
- Area: docs | tests | agent
- Record: 功能测试/前端验收与 LLM 输出评估是两类不同测试；测试账号只服务于功能验收和集成测试，不属于 `evals/` 的 LLM 输出质量评估流程。
- Prevention: 功能测试失败时优先排查代码、测试数据、服务、数据库和环境配置；只有 LLM 输出质量、推理格式、工具调用行为或评估指标不达标时，才考虑优化系统提示词、评估提示词或 LangGraph agent prompt。
- Links: `AGENTS.md`、`docs/tests/`、`evals/`

### 2026-06-30 - 大体量监测事实与错误状态边界

- Type: Correction
- Area: agent | backend | frontend | tests | docs
- Record: 北斗站点、GNSS 实时数据和日监测数据可能包含多站点、多月份、每小时或每分钟粒度的大体量事实；不得用固定字符数、固定条数预览或 `Message.content` 长度限制来裁剪事实数据以适配单次 LLM 输入。上下文预算应通过结构化事实存储、按任务检索、分块分析、聚合指标和 token 预算调度解决。
- Prevention: 事实获取层应保存完整可追溯数据或数据引用；LLM 输入层只装载当前推理步骤需要的事实切片、统计摘要和证据引用。非人工澄清错误不得设置为 HITL 中断，只有显式 `interrupt()` 等待用户补充时才展示干预卡片；系统异常、上游失败、上下文超预算和响应组装失败应走结构化错误事件、可重试提示和日志。
- Links: `AGENTS.md`、`docs/specs/005-beidou-station-resolution.md`、`app/core/langgraph/graph.py`

### 2026-07-01 - GNSS 目标图结构与月度分组分析边界

- Type: Correction
- Area: agent | backend | docs | requirements
- Record: 后续 Agent 图结构应参考 `router → chat/chat_tools 或 gnss_preflight → gnss/gnss_tools → action_router → artifact/HITL/side_effect_tools → render`。不再新增独立 `context` 节点；上下文由 `router` 和后续业务节点按需读取。站点列表规模通常不是主要瓶颈；每个分组下几十个站点，监测数据为每站每小时 1 条，常见按月分析，单分组月度分析可能达到数万行。GraphState 不应保存完整原始监测序列，应保存站点/分组范围、时间范围、指标、粒度、数据集引用、分析进度、站点摘要、分组摘要、异常候选和证据引用。
- Prevention: 后续设计 GNSS 数据分析、报告和订阅能力时，先阅读 `docs/plans/006-prd-agent-graph-roadmap.md`。多站点或分组月度分析是正常业务场景，不得因 LLM 上下文无法容纳原始数据而拒绝；应通过分块查询、结构化数据引用、每站摘要、分组聚合和证据切片处理。不清楚默认时间范围、指标集合、后台任务阈值、质量码或报告附录要求时，必须先向用户确认并记录结论。
- Links: `docs/reference/prd.md`、`docs/plans/006-prd-agent-graph-roadmap.md`

### 2026-07-01 - GNSS 月报默认规则与订阅运行语义

- Type: Decision
- Area: requirements | agent | backend | docs
- Record: 月度分析默认采用上一个完整自然月；多站点或分组默认指标为 H residual 和 U residual；站点数大于 10 个或估算时序行数大于 5,000 条时触发后台长任务提示，目标保证同步 HTTP 响应在 5 秒内完成；分组分析对话窗口默认输出“分组概览趋势 + 异常站点 Top 3 + 核心结论”，其余站点细节进入 PDF；`station_summaries` 必须包含 `missing_ratio`，缺测率大于 20% 时向 LLM 标记“数据置信度低”。报告 PDF 后台异步生成。订阅立即运行单独生成邮件内容；定时订阅运行时，智能体根据用户原始订阅诉求生成本次真正执行的问题，再执行查询/分析并发送邮件。
- Prevention: 后续 GNSS 分析、PDF 报告和邮件订阅的 spec/design/test 必须引用这些默认规则；不得把默认周期、指标、长任务阈值、输出粒度、缺测低置信度或订阅运行语义写成临时 prompt 文案。修改这些口径前，先同步 `docs/plans/006-prd-agent-graph-roadmap.md` 和对应功能文档。
- Links: `docs/reference/prd.md`、`docs/plans/006-prd-agent-graph-roadmap.md`

### 2026-07-01 - GNSS Preflight 与天气工具边界

- Type: Decision
- Area: requirements | agent | backend | docs
- Record: 后续目标图不再包含独立 `context` 节点；`router` 和后续业务节点按需读取上下文。GNSS 业务进入 `gnss` 节点前必须先经过轻量 `gnss_preflight` 凭证校验门禁，凭证缺失、不可用或登录刷新失败时直接进入授权缺失提示。天气查询工具改为无北斗鉴权的纯经纬度工具 `query_open_meteo_weather(latitude, longitude, ...)`；特定站点天气必须先调用 `get_beidou_station_detail(station_uuid)` 获取经纬度，再组合调用天气工具。
- Prevention: 后续实现图结构、工具注册和测试计划时，不要新增独立 `context` 节点，不要让普通天气查询触发北斗授权链路，也不要继续使用 `get_beidou_station_weather(station_uuid)` 这类混合北斗鉴权和天气查询的包装工具。GNSS 工具层仍要保留用户级凭证校验，防止绕过 `gnss_preflight`。
- Links: `docs/reference/prd.md`、`docs/plans/006-prd-agent-graph-roadmap.md`
