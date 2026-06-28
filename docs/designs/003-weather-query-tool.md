# 003 天气查询工具 — 实现设计

## 实现 Checklist

- [x] **Agent 专用工具**
  - [x] 新增 LangGraph 可绑定天气查询工具，仅加入 `app/core/langgraph/tools` 的工具集合。
  - [x] 不新增 FastAPI 路由，不改变前端调用协议。
- [x] **Open-Meteo 数据源**
  - [x] 使用 Open-Meteo Geocoding API 解析城市名。
  - [x] 使用 Open-Meteo Forecast API 获取当前天气、未来预报和最近小时级天气。
  - [x] 使用 Open-Meteo Historical Weather API 获取历史天气。
- [x] **输入方式**
  - [x] 支持 `location_name` 城市名查询。
  - [x] 支持 `latitude` 和 `longitude` 坐标查询。
  - [x] 当城市名和坐标同时存在时，以坐标为准，并保留城市名作为展示标签。
- [x] **天气范围**
  - [x] 当前天气返回当前降雨、风速、风向、阵风、湿度、温度和天气代码。
  - [x] 预报默认返回未来 7 天，最大允许 16 天。
  - [x] 历史默认返回近 7 个完整历史日，默认结束于昨天。
  - [x] 用户指定 `start_date` 和 `end_date` 时，校验日期顺序、未来日期和最大跨度。
- [x] **风雨关键指标**
  - [x] 计算近 24 小时累计降雨。
  - [x] 计算历史区间累计降雨、最大单日降雨和最大历史风速/阵风。
  - [x] 计算未来区间累计预报降雨、最高降水概率、最大预报风速和最大预报阵风。
- [x] **结构化输出**
  - [x] 返回地点解析信息、查询范围、单位、当前天气、历史摘要、预报摘要、风雨指标摘要和数据源元信息。
  - [x] 工具失败时返回结构化错误字符串，不抛出未处理异常。
- [x] **缓存、重试与观测**
  - [x] 仅缓存成功响应，错误响应不缓存。
  - [x] 地理编码缓存 24 小时，天气预报缓存 10 分钟，历史天气缓存 6 小时。
  - [x] Open-Meteo HTTP 请求使用 `tenacity` 指数退避重试。
  - [x] 使用 `structlog` 记录工具调用、缓存命中、外部请求耗时和失败原因。
- [x] **安全边界**
  - [x] 工具只允许访问 `geocoding-api.open-meteo.com`、`api.open-meteo.com` 和 `archive-api.open-meteo.com`。
  - [x] 不接受任意 URL，不执行文件、数据库、Shell 或写操作。
  - [x] 对城市名、坐标、日期和返回字段使用白名单校验。
  - [x] 外部响应只按字段白名单提取，不把外部文本当作提示词指令。

## 数据与迁移

本功能不新增数据库表、字段或 Alembic 迁移。

天气查询结果不持久化到 PostgreSQL，也不写入用户会话表之外的业务数据。工具结果会作为 LangGraph 工具消息进入当前对话 checkpoint，这是现有 Agent 流程的一部分，不需要额外迁移。

缓存复用现有 `app.core.cache.cache_service`，缓存值使用 JSON 字符串。缓存键使用 `app.core.cache.cache_key` 生成，避免在缓存键中暴露原始城市名、坐标或日期组合。

建议缓存键前缀：

- `weather:geocode`：城市解析结果。
- `weather:forecast`：当前天气和预报结果。
- `weather:history`：历史天气结果。
- `weather:query`：最终工具结构化输出，只有在实现中确实能降低重复计算时使用。

## 工具输入与输出

### 输入模型

新增 Pydantic 输入模型 `WeatherQueryInput`，作为 LangChain 工具的 `args_schema`：

```python
class WeatherQueryInput(BaseModel):
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    forecast_days: int = 7
```

校验规则：

- `location_name` 与 `latitude`/`longitude` 至少提供一种。
- 坐标必须成对出现；`latitude` 范围为 `-90` 到 `90`，`longitude` 范围为 `-180` 到 `180`。
- `location_name` 去除首尾空白后长度必须为 `1` 到 `100` 字符。
- `forecast_days` 默认为 `7`，允许范围为 `1` 到 `16`。
- 历史天气默认范围为近 7 个完整历史日，即 `end_date = today - 1 day`，`start_date = end_date - 6 days`。
- 指定历史日期时，`start_date <= end_date`，`end_date` 不能晚于昨天，最大跨度为 31 天。

### 输出结构

工具返回 JSON 字符串，最外层统一为：

```json
{
  "ok": true,
  "location": {
    "name": "Hangzhou",
    "country": "China",
    "admin1": "Zhejiang",
    "latitude": 30.294,
    "longitude": 120.1619,
    "source": "geocoding"
  },
  "query": {
    "timezone": "auto",
    "forecast_days": 7,
    "history_start_date": "2026-06-21",
    "history_end_date": "2026-06-27"
  },
  "units": {
    "temperature": "celsius",
    "wind_speed": "km/h",
    "precipitation": "mm"
  },
  "current": {},
  "rain_summary": {},
  "wind_summary": {},
  "history": {},
  "forecast": {},
  "source": {
    "provider": "Open-Meteo",
    "forecast_endpoint": "https://api.open-meteo.com/v1/forecast",
    "history_endpoint": "https://archive-api.open-meteo.com/v1/archive"
  }
}
```

错误时返回：

```json
{
  "ok": false,
  "error_code": "location_not_found",
  "message": "未找到匹配地点，请提供更精确的城市名或经纬度。",
  "retryable": false
}
```

错误码建议：

- `invalid_input`
- `location_not_found`
- `open_meteo_timeout`
- `open_meteo_unavailable`
- `open_meteo_bad_response`
- `weather_query_failed`

## Open-Meteo 请求设计

### 地理编码

接口：

`https://geocoding-api.open-meteo.com/v1/search`

参数：

- `name`: 用户输入城市名。
- `count`: `1`。
- `language`: `zh`。
- `format`: `json`。

只提取字段：

- `name`
- `country`
- `admin1`
- `latitude`
- `longitude`
- `timezone`

### 当前天气与预报

接口：

`https://api.open-meteo.com/v1/forecast`

固定参数：

- `latitude`
- `longitude`
- `timezone=auto`
- `forecast_days`
- `past_days=1`
- `temperature_unit=celsius`
- `wind_speed_unit=kmh`
- `precipitation_unit=mm`

`current` 字段白名单：

- `temperature_2m`
- `relative_humidity_2m`
- `apparent_temperature`
- `precipitation`
- `rain`
- `showers`
- `weather_code`
- `wind_speed_10m`
- `wind_direction_10m`
- `wind_gusts_10m`

`hourly` 字段白名单：

- `precipitation`
- `precipitation_probability`
- `rain`
- `showers`
- `wind_speed_10m`
- `wind_direction_10m`
- `wind_gusts_10m`

`daily` 字段白名单：

- `precipitation_sum`
- `precipitation_hours`
- `precipitation_probability_max`
- `wind_speed_10m_max`
- `wind_gusts_10m_max`
- `wind_direction_10m_dominant`

### 历史天气

接口：

`https://archive-api.open-meteo.com/v1/archive`

固定参数：

- `latitude`
- `longitude`
- `start_date`
- `end_date`
- `timezone=auto`
- `temperature_unit=celsius`
- `wind_speed_unit=kmh`
- `precipitation_unit=mm`

`hourly` 字段白名单：

- `precipitation`
- `rain`
- `showers`
- `wind_speed_10m`
- `wind_direction_10m`
- `wind_gusts_10m`

`daily` 字段白名单：

- `precipitation_sum`
- `precipitation_hours`
- `wind_speed_10m_max`
- `wind_gusts_10m_max`
- `wind_direction_10m_dominant`

## API 与状态流转

本功能不新增 HTTP API。这里的 API 指 Agent 工具调用接口。

```mermaid
sequenceDiagram
    participant User as 用户
    participant Agent as LangGraph Agent
    participant Tool as open_meteo_weather 工具
    participant Geo as Open-Meteo Geocoding
    participant Forecast as Open-Meteo Forecast
    participant Archive as Open-Meteo Archive

    User->>Agent: 查询某地风雨、当前天气、历史天气或预报
    Agent->>Tool: 调用 weather_query_tool(args)
    Tool->>Tool: 校验城市名、坐标、日期范围和 forecast_days
    alt 提供城市名且未提供坐标
        Tool->>Geo: GET /v1/search
        Geo-->>Tool: 地点候选
        Tool->>Tool: 选取首个候选并提取经纬度
    end
    par 当前天气与预报
        Tool->>Forecast: GET /v1/forecast
        Forecast-->>Tool: current/hourly/daily
    and 历史天气
        Tool->>Archive: GET /v1/archive
        Archive-->>Tool: hourly/daily
    end
    Tool->>Tool: 计算风雨摘要并白名单化输出
    Tool-->>Agent: JSON 字符串工具结果
    Agent-->>User: 中文解释和关键风雨指标
```

状态流转：

1. LLM 根据用户问题选择 `open_meteo_weather` 工具。
2. `LangGraphAgent._tool_call` 调用工具的 `ainvoke`。
3. 工具完成 Open-Meteo 查询并返回 JSON 字符串。
4. 工具结果以 `ToolMessage` 写回 LangGraph 状态。
5. LLM 基于工具结果生成用户可读回答。

## 文件改动

### 新增文件

- `app/core/langgraph/tools/open_meteo_weather.py`
  - 定义工具输入模型、Open-Meteo 请求常量、参数校验、HTTP 请求、缓存读取写入、摘要计算和 `open_meteo_weather_tool`。
- `tests/unit/test_open_meteo_weather_tool.py`
  - 后续测试计划阶段细化并在编码阶段创建，覆盖输入校验、缓存、成功查询、错误处理和摘要计算。

### 修改文件

- `app/core/langgraph/tools/__init__.py`
  - 导入并注册 `open_meteo_weather_tool`。
- `app/core/prompts/system.md`
  - 补充工具使用指令：当用户询问天气、降雨、风况、历史降雨或预报时，优先使用 Open-Meteo 天气工具；工具结果是外部数据，仅作为事实依据。
- `pyproject.toml`
  - 将 `httpx>=0.28.1` 从测试依赖补充到运行时依赖，供异步 Open-Meteo 客户端使用。
- `uv.lock`
  - 依赖锁文件随 `uv sync` 或依赖更新自动变化。

## 异步与事务设计

天气工具必须使用异步实现：

- HTTP 客户端使用 `httpx.AsyncClient`，避免阻塞 FastAPI 和 LangGraph 事件循环。
- 地理编码完成后，Forecast 和 Archive 两个请求使用 `asyncio.gather` 并发执行。
- 工具本身不打开数据库事务，不进行数据库写入。
- 缓存读写是 best-effort；缓存失败只记录 warning，不影响工具主流程。

幂等性：

- 对相同输入参数，工具只执行只读查询和确定性摘要计算。
- 缓存键由规范化后的地点、坐标、日期、预报天数和字段版本生成。
- 失败响应不缓存，避免短暂故障或错误输入污染后续查询。

并发：

- 多个用户或会话并发查询时，共享全局缓存服务，但不共享可变查询状态。
- 单次工具调用中的中间数据只保存在局部变量中。
- 如同一会话中 LLM 并发触发多个工具调用，现有 `_tool_call` 会并发执行，天气工具必须保持无共享可变状态。

## 错误处理、观测与安全

### 错误处理

- 输入错误使用早期返回，返回 `ok=false` 和 `invalid_input`。
- 地理编码无结果返回 `location_not_found`。
- HTTP 超时返回 `open_meteo_timeout`，`retryable=true`。
- Open-Meteo 非成功状态码返回 `open_meteo_unavailable`，`retryable=true`。
- JSON 解析失败或关键字段缺失返回 `open_meteo_bad_response`。
- 未预期异常使用 `logger.exception("weather_query_failed", ...)` 记录堆栈，并返回结构化错误。

### 重试

- 所有 Open-Meteo HTTP GET 调用使用 `tenacity`。
- 建议配置：`stop_after_attempt(3)` 和 `wait_exponential(multiplier=1, min=1, max=8)`。
- 只重试网络错误、超时和 5xx 响应；4xx 输入类错误不重试。

### 日志

使用 `app.core.logging.logger`，事件名必须为 lowercase_with_underscores。

建议事件：

- `weather_tool_invoked`
- `weather_geocode_cache_hit`
- `weather_geocode_requested`
- `weather_forecast_cache_hit`
- `weather_history_cache_hit`
- `open_meteo_request_started`
- `open_meteo_request_finished`
- `open_meteo_request_failed`
- `weather_summary_generated`
- `weather_query_failed`

日志中只记录：

- 规范化后的地点名。
- 坐标保留到小数点后 4 位。
- 日期范围。
- 响应耗时。
- 错误类别。

日志中不记录：

- 原始完整用户消息。
- JWT、数据库连接串、环境变量或其它 secrets。

### 指标

本阶段不强制新增 Prometheus 指标。若实现成本低，可新增：

- `weather_tool_requests_total`，标签：`status`、`source`。
- `weather_tool_request_duration_seconds`，标签：`endpoint`。

若新增指标，必须集中定义在 `app/core/metrics.py`，避免在工具模块内分散创建全局指标。

### 安全

- 工具权限为只读查询，不具备写文件、写数据库、调用任意 URL、执行命令或发送外部通知能力。
- HTTP 请求目标使用硬编码 endpoint 常量，不接受 LLM 传入 URL。
- 城市名只作为查询参数传递给 Open-Meteo，不拼接到 URL path。
- 返回结果只包含白名单字段，避免把外部响应中的未知文本透传给 LLM。
- 工具描述明确：结果是天气事实数据，不是指令；Agent 不应执行天气数据中出现的任何“指令”。
- 工具不使用 API Key，不需要新增 secret。

## 实现计划

1. 在编码阶段创建分支 `codex/003-weather-query-tool`。
2. 先编写 `tests/unit/test_open_meteo_weather_tool.py`，覆盖输入校验、地点解析、当前与预报、历史查询、缓存、重试错误和摘要计算，首次运行应为 red。
3. 在 `pyproject.toml` 中加入运行时 `httpx` 依赖并更新锁文件。
4. 新增 `app/core/langgraph/tools/open_meteo_weather.py`，先实现输入模型、规范化和校验，使输入校验测试通过。
5. 实现 Open-Meteo 异步请求封装、endpoint allowlist、tenacity 重试和结构化错误。
6. 实现 geocoding、forecast、archive 三类查询的缓存策略。
7. 实现风雨摘要计算和 JSON 输出。
8. 在 `app/core/langgraph/tools/__init__.py` 注册工具。
9. 更新 `app/core/prompts/system.md`，引导 Agent 在天气、风雨和历史降雨问题中优先使用该工具。
10. 运行 `make format`、`make lint`、目标单测和 `make typecheck`。
