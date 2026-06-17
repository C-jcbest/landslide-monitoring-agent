# 配置

所有配置都从环境变量读取。使用 `.env.development`、`.env.staging` 或 `.env.production` — 应用根据 `APP_ENV` 变量加载相应的文件。

复制 `.env.example` 以开始：

```bash
cp .env.example .env.development
```

---

## 应用

| 变量 | 默认值 | 描述 |
| --- | --- | --- |
| `APP_ENV` | `development` | 环境：`development`、`staging`、`production`、`test` |
| `PROJECT_NAME` | `FastAPI LangGraph Template` | 显示在 API 文档和日志中 |
| `VERSION` | `1.0.0` | API 版本 |
| `DEBUG` | `false` | 启用调试日志和性能分析中间件 |
| `API_V1_STR` | `/api/v1` | API 前缀 |
| `ALLOWED_ORIGINS` | `*` | 逗号分隔的 CORS 来源 |

---

## LLM

| 变量 | 默认值 | 必需 | 描述 |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | — | 是 | OpenAI API 密钥 |
| `DEFAULT_LLM_MODEL` | `gpt-5-mini` | 否 | 起始模型 — 参见 [LLM 服务](llm-service.md) 了解降级顺序 |
| `DEFAULT_LLM_TEMPERATURE` | `0.2` | 否 | 聊天补全的温度 |
| `MAX_TOKENS` | `2000` | 否 | 每次 LLM 响应的最大令牌数 |
| `MAX_LLM_CALL_RETRIES` | `3` | 否 | 切换到降级前每个模型的重试次数 |
| `LLM_TOTAL_TIMEOUT` | `60` | 否 | 整个降级循环的最大秒数 |
| `SESSION_NAMING_ENABLED` | `true` | 否 | 使用 LLM 后台任务根据用户第一条消息自动生成会话标题 |

---

## 长期记忆

| 变量 | 默认值 | 描述 |
| --- | --- | --- |
| `LONG_TERM_MEMORY_COLLECTION_NAME` | `longterm_memory` | pgvector 集合名称 |
| `LONG_TERM_MEMORY_MODEL` | `gpt-5-nano` | mem0 用于提取记忆的 LLM |
| `LONG_TERM_MEMORY_EMBEDDER_MODEL` | `text-embedding-3-small` | 语义搜索的嵌入模型 |

---

## 数据库

| 变量 | 默认值 | 描述 |
| --- | --- | --- |
| `POSTGRES_HOST` | `localhost` | PostgreSQL 主机 |
| `POSTGRES_PORT` | `5432` | PostgreSQL 端口 |
| `POSTGRES_DB` | `food_order_db` | 数据库名称 |
| `POSTGRES_USER` | `postgres` | 数据库用户 |
| `POSTGRES_PASSWORD` | `postgres` | 数据库密码 |
| `POSTGRES_POOL_SIZE` | `20` | SQLAlchemy 连接池大小 |
| `POSTGRES_MAX_OVERFLOW` | `10` | 超出连接池大小的最大溢出连接 |

---

## 认证

| 变量 | 默认值 | 必需 | 描述 |
| --- | --- | --- | --- |
| `JWT_SECRET_KEY` | — | 是 | 用于签名 JWT 令牌的密钥 — 生产环境中使用长的随机字符串 |
| `JWT_ALGORITHM` | `HS256` | 否 | JWT 签名算法 |
| `JWT_ACCESS_TOKEN_EXPIRE_DAYS` | `30` | 否 | 令牌有效期（天） |

---

## 缓存（Valkey/Redis — 可选）

设置 `VALKEY_HOST` 时，应用使用 Valkey/Redis 进行记忆搜索缓存和限流。未设置时，降级到内存 TTL 缓存（不在实例间共享）。

| 变量 | 默认值 | 描述 |
| --- | --- | --- |
| `VALKEY_HOST` | ``（禁用） | Valkey/Redis 主机 — 留空使用内存降级 |
| `VALKEY_PORT` | `6379` | 端口 |
| `VALKEY_DB` | `0` | 数据库索引 |
| `VALKEY_PASSWORD` | `` | 密码（如果需要） |
| `VALKEY_MAX_CONNECTIONS` | `20` | 连接池大小 |
| `CACHE_TTL_SECONDS` | `60` | 缓存记忆搜索结果的 TTL |

---

## 可观测性（Langfuse）

| 变量 | 默认值 | 描述 |
| --- | --- | --- |
| `LANGFUSE_TRACING_ENABLED` | `true` | 设置为 `false` 完全禁用追踪 |
| `LANGFUSE_PUBLIC_KEY` | — | Langfuse 项目公钥 |
| `LANGFUSE_SECRET_KEY` | — | Langfuse 项目密钥 |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse 主机（自托管或云端） |

---

## 限流

| 变量 | 默认值 | 描述 |
| --- | --- | --- |
| `RATE_LIMIT_DEFAULT` | `200 每天, 50 每小时` | 备用限制 |
| `RATE_LIMIT_CHAT` | `30 每分钟` | POST /chat |
| `RATE_LIMIT_CHAT_STREAM` | `20 每分钟` | POST /chat/stream |
| `RATE_LIMIT_MESSAGES` | `50 每分钟` | GET/DELETE /messages |
| `RATE_LIMIT_LOGIN` | `20 每分钟` | POST /auth/login |
| `RATE_LIMIT_REGISTER` | `10 每小时` | POST /auth/register |

配置 Valkey 后，限流在所有应用实例间共享。无 Valkey 时，限制针对每个进程。

---

## 性能分析（仅调试）

仅在 `DEBUG=true` 时激活。对每个请求进行性能分析，当请求超过阈值时保存 JSON 报告。

| 变量 | 默认值 | 描述 |
| --- | --- | --- |
| `PROFILING_DIR` | `/tmp/fastapi_profiles` | 性能分析 JSON 文件的目录 |
| `PROFILING_THRESHOLD_SECONDS` | `2.0` | 触发保存性能分析的最小墙钟时间。设为 `0` 对每个请求进行性能分析。 |

---

## 日志

| 变量 | 默认值（开发） | 默认值（生产） | 描述 |
| --- | --- | --- | --- |
| `LOG_LEVEL` | `DEBUG` | `WARNING` | 日志级别 |
| `LOG_FORMAT` | `console` | `json` | `console` 用于彩色开发输出，`json` 用于结构化生产日志 |
