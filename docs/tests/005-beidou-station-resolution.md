# 005 北斗站点查询与实体解析 — 测试计划

## Happy Path

1. **普通对话走 Chat 分支并进入 Response**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：fake LLM 返回 `AgentPlan(route="chat")`，fake chat LLM 返回普通回答。
   - 关键断言：
     - 图路由为 `Plan -> Chat -> Response -> END`。
     - 最终消息为 assistant 文本。
     - 未调用北斗站点 service。

2. **普通天气查询走 Chat 分支并可调用天气工具**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：
     - fake LLM 返回 `AgentPlan(route="chat")`。
     - 用户输入为普通天气或降雨问题，不包含北斗站点分析意图。
     - fake weather tool 返回天气事实。
   - 关键断言：
     - 图路由为 `Plan -> Chat -> Response -> END`。
     - 可调用天气只读能力。
     - 不进入 `Gate`。
     - 不调用北斗站点 service。

3. **站点详情请求在已授权且唯一确认时通过 Gate**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：
     - fake session provider 返回当前用户北斗会话。
     - fake station service 返回一个候选站点和详情。
     - fake LLM `Plan` 返回 `route="gnss_analysis"`、`intent="station_detail"`。
     - fake LLM `GateDecision` 返回 `status="ready"`、`confidence="high"`、候选中的 `StationUUID`。
   - 关键断言：
     - 图路由为 `Plan -> Gate -> ExecuteAnalyze -> Response -> END`。
     - `ExecuteAnalyze` 只使用候选列表中当前用户可访问的站点 UUID。
     - 最终响应包含站点名称、分组、状态、类型、位置等必要事实。
     - 响应和日志不包含 `SessionUUID`。

4. **监测分析需要天气事实时由 ExecuteAnalyze 调用天气工具**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：
     - fake LLM `Plan` 返回 `route="gnss_analysis"`。
     - fake session provider 返回当前用户北斗会话。
     - fake station service 和 fake `GateDecision` 确认唯一站点。
     - fake weather tool 返回降雨或风况事实。
   - 关键断言：
     - 图路由为 `Plan -> Gate -> ExecuteAnalyze -> Response -> END`。
     - 天气工具调用发生在 `Gate` 通过之后。
     - `ExecuteAnalyze` 结果同时包含已确认站点事实和天气事实。
     - 天气工具不替代北斗授权或站点确认。

5. **站点 service 可查询分组列表**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 测试数据/依赖：mock `httpx.AsyncClient` 返回 `ResponseCode="200"` 和 `StationGroupList`。
   - 关键断言：
     - 请求路径为固定 `Station/getStationGroupListInfo.php`。
     - 请求体包含 `SessionUUID`，但日志/返回给图状态的候选数据不暴露它。
     - 返回 `BeidouStationGroup` 列表。

6. **站点 service 可查询站点列表**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 测试数据/依赖：mock 上游返回 `StationList` 和 `PageInfo`。
   - 关键断言：
     - 支持按分组 UUID 查询。
     - `PageInfo.PageSize` 可配置，默认不请求无限大结果。
     - 返回规范化站点 schema。

7. **站点详情通过 StationUUID 查询**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 测试数据/依赖：mock `getStationListInfo.php` 携带 `StationUUID` 返回单个 `StationList` 项。
   - 关键断言：
     - service 将单个站点规范化为详情对象。
     - 详情对象包含 `StationUUID`、`StationName`、`DeviceUUID`、坐标、位置和分组字段。

8. **上下文指代可由智能体确认**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：
     - 图状态已有上一轮 `resolved_station`。
     - 用户输入为“查一下这个站点详情”。
     - fake `Plan` 输出 `context_reference=true`。
     - fake `GateDecision` 基于上下文返回上一轮站点 UUID。
   - 关键断言：
     - 确定性代码不通过关键词规则直接解析“这个站点”。
     - 只有当 LLM `GateDecision` 高置信且 UUID 属于当前候选/上下文允许范围时才通过。

## 边界场景

1. **多候选必须澄清**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：fake station service 返回多个名称相近站点；fake `GateDecision` 返回 `needs_clarification` 或中低置信。
   - 关键断言：
     - 图路由为 `Plan -> Gate -> Response -> END`。
     - 不调用 `ExecuteAnalyze`。
     - 最终响应包含候选最小字段和澄清问题。

2. **LLM 偏好某候选但置信度不足时不得执行**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：fake `GateDecision` 返回 `resolved_station_uuid` 但 `confidence="medium"`。
   - 关键断言：
     - Gate 将结果降级为澄清状态。
     - 不进入 `ExecuteAnalyze`。

3. **LLM 返回不属于候选列表的 UUID**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：fake `GateDecision` 返回当前用户候选之外的 `StationUUID`。
   - 关键断言：
     - Gate 拒绝该结果并进入 `Response`。
     - 响应不泄露内部判定细节。

4. **候选为空**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：fake station service 返回空站点列表。
   - 关键断言：
     - Gate 状态为 `no_candidate`。
     - Response 提示用户提供更具体名称、编码或分组。

5. **候选数据裁剪**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 测试数据/依赖：站点详情包含完整字段。
   - 关键断言：
     - 传给 LLM 的候选只包含设计允许字段。
     - 不包含 `SessionUUID`、上游原始响应全文或不必要敏感上下文。

6. **当前用户缺少 user_id**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：`RunnableConfig.metadata` 不含 `user_id`。
   - 关键断言：
     - Gate 返回授权缺失或认证上下文缺失状态。
     - 不调用北斗上游。

7. **普通对话工具能力不暴露额外 tool_call 图节点**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py` 或更新 `tests/unit/test_graph_llm_and_session_naming.py`。
   - 测试数据/依赖：检查编译前或测试替身记录的节点/路由。
   - 关键断言：
     - 图拓扑只包含 `plan`、`chat`、`gate`、`execute_analyze`、`response`。
     - 不再依赖公开 `_tool_call` 节点测试。

8. **天气工具不能绕过 Gate**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：
     - 用户输入为“结合最近降雨分析北坡站点”。
     - fake weather tool 可用。
     - fake session provider 返回 `None` 或 fake `GateDecision` 返回多候选澄清。
   - 关键断言：
     - 不调用 `ExecuteAnalyze`。
     - 不因为天气工具可用而继续监测分析。
     - Response 返回授权缺失或候选澄清。

## 失败场景

1. **当前用户无北斗会话**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：fake session provider 返回 `None`。
   - 关键断言：
     - Gate 状态为 `auth_missing`。
     - 不调用站点查询 service。
     - Response 提示需要绑定北斗凭据。

2. **上游会话无效或过期**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py` 和 `tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：mock 上游返回 `ResponseCode="400101"`。
   - 关键断言：
     - service 映射为 `beidou_session_invalid`。
     - Response 不暴露上游原始会话 UUID。

3. **上游权限不足**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 测试数据/依赖：mock 上游返回 `ResponseCode="400000"`。
   - 关键断言：
     - service 映射为 `beidou_permission_denied`。
     - 错误不可重试。

4. **上游超时可重试**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 测试数据/依赖：mock HTTP 第一次抛 `httpx.TimeoutException`，后续成功或持续失败。
   - 关键断言：
     - 使用 `tenacity` 进行重试。
     - 最终失败映射为 `beidou_timeout` 且 `retryable=true`。

5. **上游返回结构异常**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 测试数据/依赖：mock 返回缺少 `ResponseCode`、`StationList` 类型错误或非 JSON。
   - 关键断言：
     - service 返回或抛出 `beidou_bad_response`。
     - 不缓存错误响应。

6. **LLM 结构化输出失败**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 测试数据/依赖：fake LLM 抛出异常或返回无法通过 Pydantic 校验的数据。
   - 关键断言：
     - `Plan` 或 `Gate` 使用现有 LLM fallback/错误路径。
     - 不产生未校验的执行状态。

7. **站点详情查询返回多个站点**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 测试数据/依赖：mock `StationList` 返回多个项目。
   - 关键断言：
     - service 返回 `station_ambiguous`。
     - Graph 不进入最终分析执行。

## 测试层级、数据与依赖

测试层级：

- 单元测试为主：覆盖 station service、图节点、状态转换和响应组装。
- API 测试只在现有聊天接口合同受影响时补充，优先更新 `tests/api/test_chat_routes.py` 中对 agent 替身的断言。
- 不做 live 测试，不调用真实北斗接口，不使用真实账号。

测试替身：

- `FakeBeidouSessionProvider`：按 `user_id` 返回 fake session 或 `None`。
- `FakeBeidouStationService`：返回固定分组、候选、详情或结构化错误。
- `FakeLLMService`：按调用顺序返回 `AgentPlan`、`GateDecision`、普通聊天内容或响应组装内容。
- `MockTransport` 或 monkeypatch `httpx.AsyncClient`：模拟北斗上游响应。

测试数据：

- 使用 fake UUID，例如 `11111111-1111-4111-8111-111111111111`。
- 使用 fake 站点名，例如 `北坡 GNSS 01`、`北坡 GNSS 02`、`南坡基准站`。
- 使用 fake 设备编码，例如 `DEV-BP-001`。
- 不写入真实账号、真实密码、真实 `SessionUUID`。

建议测试命令：

```bash
uv run pytest tests/unit/test_beidou_station_service.py
uv run pytest tests/unit/test_gnss_graph_nodes.py
uv run pytest tests/unit/test_agent_workflows.py
uv run pytest tests/unit/test_graph_llm_and_session_naming.py
uv run pytest tests/api/test_chat_routes.py
make lint
make typecheck
```

## 验收标准映射

- **图结构保持为 5 节点**
  - 覆盖测试：普通对话路由、普通天气路由、GNSS 路由、无公开 `tool_call` 图节点。

- **当前用户无北斗凭据/会话时返回授权缺失**
  - 覆盖测试：当前用户无北斗会话、缺少 `user_id`。

- **当前用户有凭据/会话时可查询分组、站点列表和详情**
  - 覆盖测试：分组列表查询、站点列表查询、站点详情查询。

- **名称、模糊名称、编码和上下文指代由智能体识别**
  - 覆盖测试：`Plan` 结构化输出驱动路由、上下文指代、fake `GateDecision` 驱动唯一确认。

- **确定性代码不以固定字符串规则替代语义识别**
  - 覆盖测试：上下文指代测试中断言仅 LLM 决策可通过；多候选安全门禁只校验候选归属和置信度。

- **单一高置信候选进入 ExecuteAnalyze**
  - 覆盖测试：站点详情 happy path、监测分析需要天气事实时由 `ExecuteAnalyze` 调用天气工具。

- **多候选、低置信、候选为空或信息不足返回澄清**
  - 覆盖测试：多候选澄清、低置信降级、候选为空、天气工具不能绕过 Gate。

- **北斗上游失败、超时、权限不足和返回格式异常有结构化错误与日志**
  - 覆盖测试：会话无效、权限不足、超时重试、返回结构异常。

- **自动化测试覆盖 happy path、多候选澄清、授权缺失、上游错误和上下文指代**
  - 覆盖测试：本计划中的 `test_beidou_station_service.py` 与 `test_gnss_graph_nodes.py` 全部核心用例。
