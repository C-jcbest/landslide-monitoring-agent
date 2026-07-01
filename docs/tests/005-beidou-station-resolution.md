# 005 北斗站点查询与实体解析 — 测试计划

## Happy Path

1. **GNSS/北斗请求路由到 `gnss_preflight`**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_request_planner_routes_gnss_request_to_gnss_agent`。
   - 关键断言：
     - `request_planner` 调用 LLM 结构化输出 `AgentPlan`。
     - `route="gnss"` 时返回 `Command(goto="gnss_preflight")`。
     - 图状态写入 `plan` 和 `route`。

2. **planner 使用最近对话上下文判断最新消息**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_request_planner_receives_recent_dialogue_context`。
   - 关键断言：
     - planner prompt 包含最近用户/助手消息。
     - 最新用户消息可结合历史消息判断为 GNSS/北斗相关请求。
     - 上下文由图状态消息生成，不依赖固定字符串特判。

3. **普通天气请求进入 `chat`**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_request_planner_routes_weather_request_to_chat`。
   - 关键断言：
     - `route="chat"` 时返回 `Command(goto="chat")`。
     - 不写入 `unsupported_reason`。
     - 不进入 `gnss_preflight` 或 GNSS 工具执行。

4. **GNSS 无凭据时不进入 agent**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_gnss_preflight_auth_missing_routes_to_render_without_agent`。
   - 关键断言：
     - `gnss_preflight` 在会话 provider 返回空时进入 `render`。
     - 写入 `GateDecision(status="auth_missing")` 和原因码。
     - 不调用 LLM，不进入 `gnss_agent`。

5. **普通天气工具不需要北斗凭据**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_chat_tools_weather_does_not_require_beidou_credentials`。
   - 关键断言：
     - `chat_tools` 可执行 `query_open_meteo_weather`。
     - 不调用北斗会话 provider。
     - 工具结果以 `ToolMessage` 返回 `chat`。

6. **GNSS agent 需要事实时路由到 `gnss_tools`**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_gnss_agent_routes_tool_calls_to_gnss_tools`。
   - 关键断言：
     - LLM 返回工具调用时，`gnss_agent` 进入 `gnss_tools`。
     - 工具调用消息保留在图状态中。
     - 不直接在 agent 节点拼接工具结果。

7. **GNSS 工具按当前用户上下文执行**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_gnss_tools_execute_with_user_scoped_session`。
   - 关键断言：
     - `gnss_tools` 从 `RunnableConfig.metadata.user_id` 获取用户上下文。
     - 工具结果以 `ToolMessage` 返回给 `gnss_agent`。
     - 工具执行不需要 LLM 接触北斗 `SessionUUID`。

8. **站点天气必须组合调用**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_gnss_station_weather_requires_detail_then_coordinate_weather`。
   - 关键断言：
     - 先调用 `get_beidou_station_detail(station_uuid)` 获取站点详情和经纬度。
     - 获取站点详情阶段不直接调用天气工具。
     - 再调用 `query_open_meteo_weather(latitude, longitude, ...)` 获取天气事实。

9. **旧站点天气包装工具不再授权**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_removed_station_weather_wrapper_is_not_authorized`。
   - 关键断言：
     - 调用 `get_beidou_station_weather` 返回 `unknown_gnss_tool`。
     - 不通过旧包装工具混合北斗鉴权和天气查询。

10. **GNSS agent 生成最终回复后进入 `action_router`**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_gnss_agent_routes_final_reply_to_action_router`。
   - 关键断言：
     - 无工具调用时写入 `chat_response`。
     - 下一节点为 `action_router`。

11. **订阅动作未接 HITL 时不执行副作用**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_action_router_blocks_subscription_side_effects_until_hitl_exists`。
   - 关键断言：
     - `intent="subscription_action"` 不触发外部订阅副作用。
     - 进入 `render` 并返回受控说明。

12. **render 输出普通 chat 回复**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_render_returns_chat_response`。
   - 关键断言：
     - `render` 生成 assistant 消息。
     - 响应为 `chat_response`。

13. **北斗分组列表从固定端点读取**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 覆盖用例：`test_station_groups_are_loaded_from_fixed_endpoint`。
   - 关键断言：
     - 请求路径为固定分组端点。
     - 返回规范化分组 schema。

14. **北斗站点详情按 `StationUUID` 查询**
    - 测试层级：单元测试。
    - 测试文件：`tests/unit/test_beidou_station_service.py`。
    - 覆盖用例：`test_station_detail_is_loaded_with_station_uuid`。
    - 关键断言：
      - 请求携带指定 `StationUUID`。
      - 返回规范化站点详情。

## 边界场景

1. **planner 上下文排除工具消息**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_request_planner_context_excludes_tool_messages`。
   - 关键断言：
     - `ToolMessage` 不进入 planner prompt。
     - 工具 JSON 不进入 planner prompt。
     - 最近助手文本可以进入 planner prompt。

2. **站点详情返回多个候选时拒绝**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 覆盖用例：`test_station_detail_rejects_ambiguous_upstream_response`。
   - 关键断言：
     - 上游按 `StationUUID` 返回多个站点时映射为歧义错误。
     - 不把多个候选伪装成唯一详情。

3. **站点列表默认请求全部行**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 覆盖用例：`test_station_list_requests_all_rows_by_default`。
   - 关键断言：
     - 请求体中的 `PageInfo.PageSize` 为 `-1`。
     - 当前实现不再使用默认 20 条分页。

4. **候选投影排除会话 UUID 和原始响应**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 覆盖用例：`test_candidate_projection_excludes_session_uuid_and_raw_response`。
   - 关键断言：
     - 候选字段只包含允许暴露给 LLM 的必要站点事实。
     - 不包含 `SessionUUID`。
     - 不包含上游原始响应全文。

5. **候选列表不按固定 20 条截断**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 覆盖用例：`test_station_candidates_are_not_truncated_to_twenty`。
   - 关键断言：
     - 上游返回超过 20 个站点时，候选结果保留全部候选。
     - 当前实现不再通过固定条数解决大列表问题。

6. **流式输出过滤非用户可见图 token**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_agent_workflows.py`。
   - 覆盖用例：`test_stream_response_filters_non_user_facing_graph_tokens`。
   - 关键断言：
     - 流式响应只输出用户可见文本。
     - 图内结构化状态和工具中间内容不会直接流给前端。

## 失败场景

1. **上游权限不足映射为结构化错误**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_station_service.py`。
   - 覆盖用例：`test_upstream_permission_denied_is_mapped_to_structured_error`。
   - 关键断言：
     - 上游权限不足响应映射为结构化错误。
     - 错误中不暴露 `SessionUUID`。

2. **工具调用失败返回工具级错误消息**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 当前覆盖：通过 `gnss_tools` fake runner 验证工具结果回写路径。
   - 后续可补充：
     - 未知工具名返回 `unknown_gnss_tool`。
     - 当前用户缺少北斗会话返回 `auth_missing`。
     - 工具异常映射为受控 tool error。

3. **LLM 结构化输出失败**
   - 测试层级：单元测试。
   - 当前覆盖：现有 LLM fallback 和结构化输出能力由 `tests/unit/test_graph_llm_and_session_naming.py` 覆盖基础行为。
   - 相关用例：
     - `test_llm_fallback_tries_next_model_after_openai_error`
     - `test_structured_llm_call_uses_json_mode_and_schema_instruction`
   - 后续可补充：
     - `request_planner` 收到异常时生成结构化失败状态。

4. **报告和订阅副作用未接入时阻断执行**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_gnss_graph_nodes.py`。
   - 覆盖用例：`test_action_router_blocks_subscription_side_effects_until_hitl_exists`。
   - 关键断言：
     - 未接 HITL 前不创建订阅。
     - 用户只收到受控说明。

## 测试层级、数据与依赖

测试层级：

- 以单元测试为主，覆盖图节点、状态转换、站点 service、字段投影和错误映射。
- 现阶段不新增真实北斗 live 测试。
- 现阶段不新增公开站点 REST API 测试，因为没有新增公开 API。

测试替身：

- fake LLM service：返回 `AgentPlan`、AIMessage 或工具调用消息。
- fake GNSS tool runner：模拟工具执行结果。
- fake HTTP transport：模拟北斗上游响应。
- fake `RunnableConfig.metadata`：提供 `user_id` 等用户上下文。

测试数据：

- 使用 fake UUID 和 fake 站点名。
- 不写入真实账号、真实密码或真实 `SessionUUID`。
- 需要测试账号的端到端验收应引用 `docs/tests/test-accounts.md`，不在本文档重复明文账号。

建议测试命令：

```bash
uv run pytest tests/unit/test_beidou_station_service.py tests/unit/test_gnss_graph_nodes.py tests/unit/test_agent_workflows.py tests/unit/test_graph_llm_and_session_naming.py
uv run ruff check app/core/langgraph/graph.py tests/unit/test_gnss_graph_nodes.py
uv run pyright app/core/langgraph/graph.py
```

说明：`tests/unit/test_gnss_graph_nodes.py` 当前包含测试替身类型与 pyright 的已知不匹配，完整 test-file pyright 不作为本功能验收门禁；图实现文件 `app/core/langgraph/graph.py` 需要通过 pyright。

## 验收标准映射

- **planner 的 LLM 输入包含最近用户/助手消息，并排除工具消息**
  - 覆盖测试：`test_request_planner_receives_recent_dialogue_context`、`test_request_planner_context_excludes_tool_messages`。

- **“重新查询”等上下文依赖表达可结合最近对话识别**
  - 覆盖测试：`test_request_planner_receives_recent_dialogue_context`。

- **GNSS/北斗请求进入 `gnss_preflight`，普通天气进入 `chat`**
  - 覆盖测试：`test_request_planner_routes_gnss_request_to_gnss_agent`、`test_request_planner_routes_weather_request_to_chat`。

- **GNSS 无凭据不进入 agent**
  - 覆盖测试：`test_gnss_preflight_auth_missing_routes_to_render_without_agent`。

- **普通天气不需要北斗凭据**
  - 覆盖测试：`test_chat_tools_weather_does_not_require_beidou_credentials`。

- **GNSS agent 需要事实时只能通过 `gnss_tools` 调用受控工具**
  - 覆盖测试：`test_gnss_agent_routes_tool_calls_to_gnss_tools`、`test_gnss_tools_execute_with_user_scoped_session`。

- **站点天气必须组合调用**
  - 覆盖测试：`test_gnss_station_weather_requires_detail_then_coordinate_weather`、`test_removed_station_weather_wrapper_is_not_authorized`。

- **当前用户有北斗会话时可查询分组、站点候选和详情**
  - 覆盖测试：`test_station_groups_are_loaded_from_fixed_endpoint`、`test_station_detail_is_loaded_with_station_uuid`、`test_candidate_projection_excludes_session_uuid_and_raw_response`。

- **默认站点列表请求使用 `PageSize=-1`，候选不按固定 20 条截断**
  - 覆盖测试：`test_station_list_requests_all_rows_by_default`、`test_station_candidates_are_not_truncated_to_twenty`。

- **候选投影不包含敏感上下文**
  - 覆盖测试：`test_candidate_projection_excludes_session_uuid_and_raw_response`。

- **上游权限不足和异常返回有结构化错误**
  - 覆盖测试：`test_upstream_permission_denied_is_mapped_to_structured_error`、`test_station_detail_rejects_ambiguous_upstream_response`。

- **报告和订阅副作用当前不执行**
  - 覆盖测试：`test_action_router_blocks_subscription_side_effects_until_hitl_exists`。

## 当前测试缺口

以下内容属于建议补充，不影响本文档与当前代码实现的一致性：

- 上游刷新失败时 `gnss_preflight` 的异常分支单元测试。
- 北斗上游超时重试的直接单元测试。
- planner 结构化 LLM 调用异常后的图级兜底测试。
- 报告 PDF `artifact` 节点的独立单元测试。
