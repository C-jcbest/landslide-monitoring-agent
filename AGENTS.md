# AI Agent 开发指南

本文档为在此 LangGraph FastAPI Agent 项目上工作的 AI Agent 提供基本准则。

## 快速命令

```bash
make install              # 安装依赖 (uv sync) + pre-commit hooks
make dev                  # 开发服务器，热重载 (端口 8000)
make lint                 # ruff check .
make format               # ruff format .
make typecheck            # uv run pyright (静态类型检查)
make check                # lint + typecheck
make eval                 # 运行 LLM 评估 (交互式)
make eval-quick           # 运行 LLM 评估 (默认设置)
make migrate              # 运行数据库迁移到最新 (Alembic)
make docker-up            # Docker: API + DB (默认 ENV=development)
make stack-up ENV=development  # 完整堆栈: API + DB + Prometheus + Grafana
```

> 所有 server/DB/Docker 目标接受 `ENV=development|staging|production|test`。
> 运行 `make help` 查看完整目标列表。

## 项目结构

```
app/
  api/v1/          # 路由处理程序 (auth.py, chatbot.py, api.py)
  core/
    config.py      # Pydantic Settings 配置
    database.py    # 异步数据库设置
    langgraph/     # LangGraph agent 图 + 工具
    logging.py     # structlog 设置
    llm.py         # 带重试逻辑的 LLM 服务
    limiter.py     # 限流 (slowapi)
    metrics.py     # Prometheus 指标
    middleware.py  # ASGI 中间件
    prompts/       # 系统提示词
  models/          # SQLModel ORM 模型
  schemas/         # Pydantic 请求/响应 schema + 图状态
  services/        # 业务逻辑服务
  utils/           # 共享工具
evals/             # LLM 评估框架 (基于 Langfuse)
scripts/           # 环境设置、Docker 构建脚本
```

## 项目概述

这是一个生产就绪的 AI Agent 应用，构建于：
- **LangGraph** 用于有状态的多步 AI Agent 工作流
- **FastAPI** 用于高性能异步 REST API 端点
- **Langfuse** 用于 LLM 可观测性和追踪
- **PostgreSQL + pgvector** 用于长期记忆存储 (mem0ai)
- **JWT 认证** 配会话管理
- **Prometheus + Grafana** 用于监控

## 快速参考：关键规则

### 导入规则
- **所有导入必须放在文件顶部** — 永远不要在函数或类内部添加导入

### 日志规则
- 所有日志使用 **structlog**
- 日志消息必须使用 **lowercase_with_underscores**（例如 `"user_login_successful"`）
- **structlog 事件中禁止使用 f-strings** — 通过 kwargs 传递变量
- 使用 `logger.exception()` 而不是 `logger.error()` 来保留堆栈跟踪
- 示例：`logger.info("chat_request_received", session_id=session.id, message_count=len(messages))`

### 重试规则
- **始终使用 tenacity 库**进行重试逻辑
- 配置指数退避
- 示例：`@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))`

### 输出规则
- **始终启用 rich 库**进行格式化控制台输出
- 使用 rich 显示进度条、表格、面板和格式化文本

### 缓存规则
- **仅缓存成功响应**，永不缓存错误
- 根据数据易变性使用适当的缓存 TTL

### FastAPI 规则
- 所有路由必须有限流装饰器
- 使用依赖注入处理服务、数据库连接和认证
- 所有数据库操作必须异步

## 代码风格约定

### Python/FastAPI
- 异步操作使用 `async def`
- 所有函数签名使用类型提示
- 优先使用 Pydantic 模型而非原始字典
- 使用函数式、声明式编程；避免使用类（服务和 agent 除外）
- 文件命名：小写加下划线（例如 `user_routes.py`）
- 使用 RORO 模式（接收对象，返回对象）

### 错误处理
- 在函数开头处理错误
- 对错误条件使用早期返回
- 将愉快路径放在函数最后
- 使用守卫子句处理前置条件
- 对预期错误使用 `HTTPException` 并提供适当的状态码

## LangGraph 和 LangChain 模式

### 图结构
- 使用 `StateGraph` 构建 AI Agent 工作流
- 使用 Pydantic 模型定义清晰的状态 schema（参见 `app/schemas/graph.py`）
- 使用 `CompiledStateGraph` 用于生产工作流
- 实现 `AsyncPostgresSaver` 用于检查点和持久化
- 使用 `Command` 控制节点间的图流

### 追踪
- 使用 LangChain 的 Langfuse `CallbackHandler` 追踪所有 LLM 调用
- 所有 LLM 操作必须启用 Langfuse 追踪

### 记忆 (mem0ai)
- 使用 `AsyncMemory` 进行语义记忆存储
- 按 user_id 存储记忆以实现个性化体验
- 使用异步方法：`add()`、`get()`、`search()`、`delete()`

## 认证与安全

- 使用 JWT 令牌进行认证
- 实现基于会话的用户管理（参见 `app/api/v1/auth.py`）
- 对受保护端点使用 `get_current_session` 依赖
- 将敏感数据存储在环境变量中
- 使用 Pydantic 模型验证所有用户输入

## 数据库操作

- 使用 SQLModel 作为 ORM 模型（结合 SQLAlchemy + Pydantic）
- 在 `app/models/` 目录中定义模型
- 使用 asyncpg 进行异步数据库操作
- 使用 LangGraph 的 AsyncPostgresSaver 进行 agent 检查点

## 性能指南

- 最小化阻塞 I/O 操作
- 所有数据库和外部 API 调用使用异步
- 对频繁访问的数据实现缓存
- 使用数据库连接的连接池
- 使用流式响应优化 LLM 调用

## 可观测性

- 在所有 agent 操作上集成 Langfuse 进行 LLM 追踪
- 导出 API 性能的 Prometheus 指标
- 使用上下文绑定（request_id、session_id、user_id）的结构化日志
- 跟踪 LLM 推理持续时间、令牌使用量和成本

## 测试与评估

- 对 LLM 输出实现基于指标的评估（参见 `evals/` 目录）
- 在 `evals/metrics/prompts/` 中创建 markdown 文件格式的自定义评估指标
- 使用 Langfuse 追踪作为评估数据源
- 生成带有成功率的 JSON 报告

## 配置管理

- 使用环境特定的配置文件（`.env.development`、`.env.staging`、`.env.production`）
- 使用 Pydantic Settings 进行类型安全配置（参见 `app/core/config.py`）
- 永不硬编码 secrets 或 API 密钥

## 关键依赖

- **FastAPI** - Web 框架
- **LangGraph** - Agent 工作流编排
- **LangChain** - LLM 抽象和工具
- **Langfuse** - LLM 可观测性和追踪
- **Pydantic v2** - 数据验证和设置
- **structlog** - 结构化日志
- **mem0ai** - 长期记忆管理
- **PostgreSQL + pgvector** - 数据库和向量存储
- **SQLModel** - ORM 数据库模型
- **tenacity** - 重试逻辑
- **rich** - 终端格式化
- **slowapi** - 限流
- **prometheus-client** - 指标收集

## 本项目的十诫

1. 所有路由必须有限流装饰器
2. 所有 LLM 操作必须有 Langfuse 追踪
3. 所有异步操作必须有适当的错误处理
4. 所有日志必须遵循结构化日志格式，使用 lowercase_underscore 事件名
5. 所有重试必须使用 tenacity 库
6. 所有控制台输出应使用 rich 格式化
7. 所有缓存仅存储成功响应
8. 所有导入必须在文件顶部
9. 所有数据库操作必须异步
10. 所有端点必须有适当的类型提示和 Pydantic 模型
11. 所有代码必须通过 `make typecheck`（pyright 标准模式）

## 应避免的常见陷阱

- ❌ 在 structlog 事件中使用 f-strings
- ❌ 在函数内部添加导入
- ❌ 忘记在路由上使用限流装饰器
- ❌ LLM 调用缺少 Langfuse 追踪
- ❌ 缓存错误响应
- ❌ 使用 `logger.error()` 而不是 `logger.exception()` 处理异常
- ❌ 没有异步的阻塞 I/O 操作
- ❌ 硬编码 secrets 或 API 密钥
- ❌ 函数签名缺少类型提示

## 进行更改时

修改代码前：
1. 先阅读现有实现
2. 检查代码库中的相关模式
3. 确保与现有代码风格一致
4. 添加带有结构化格式的适当日志
5. 包含带有早期返回的错误处理
6. 添加类型提示和 Pydantic 模型
7. 验证 LLM 调用已启用 Langfuse 追踪

## 参考

- LangGraph 文档: https://langchain-ai.github.io/langgraph/
- LangChain 文档: https://python.langchain.com/docs/
- FastAPI 文档: https://fastapi.tiangolo.com/
- Langfuse 文档: https://langfuse.com/docs
