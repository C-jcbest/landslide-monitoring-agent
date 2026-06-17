<div align="right"><a href="./getting-started.en-US.md">English</a></div>

# 快速开始

## 前置要求

- Python 3.13+
- uv — `pip install uv`
- Docker + Docker Compose（本地开发推荐）
- OpenAI API 密钥
- Langfuse 账户（可选 — 设置 `LANGFUSE_TRACING_ENABLED=false` 跳过）

## 选项 A：Docker（推荐）

最快的方式。一个命令启动 API 和带 pgvector 的 PostgreSQL。

```bash
git clone <repo-url> my-agent
cd my-agent

# 复制并填写您的环境文件
cp .env.example .env.development
# 必需：OPENAI_API_KEY, JWT_SECRET_KEY
# 可选：LANGFUSE_* 密钥（或设置 LANGFUSE_TRACING_ENABLED=false）

make install       # 安装 Python 依赖 + pre-commit hooks
make docker-up     # 启动 API (port 8000) + PostgreSQL
make docker-migrate # 在应用容器内运行 Alembic 迁移
```

打开 http://localhost:8000/docs 查看交互式 API。

## 选项 B：本地 Python

```bash
git clone <repo-url> my-agent
cd my-agent

cp .env.example .env.development
# 填写：OPENAI_API_KEY, JWT_SECRET_KEY, POSTGRES_*（指向您的数据库）

make install       # 安装依赖 + pre-commit hooks
make migrate       # 通过 Alembic 创建表
make dev           # 启动热重载服务器，端口 8000
```

## 您的第一个 API 调用

### 1. 注册用户

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "Secret123!", "username": "you"}'
```

返回 `user_id` 和 JWT 令牌。

### 2. 创建会话

```bash
curl -X POST http://localhost:8000/api/v1/auth/session \
  -H "Authorization: Bearer <token from step 1>"
```

返回 `session_id` 和作用域为会话的 JWT。

### 3. 聊天

```bash
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -H "Authorization: Bearer <session token>" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

或使用流式端点获取实时响应：

```bash
curl -X POST http://localhost:8000/api/v1/chatbot/chat/stream \
  -H "Authorization: Bearer <session token>" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## 自定义 agent

您最可能更改的部分：

| 内容 | 位置 |
|---|---|
| Agent 个性与指令 | `app/core/prompts/system.md` |
| 可用工具 | `app/core/langgraph/tools.py` |
| LLM 模型与降级顺序 | `app/services/llm.py` → `LLMRegistry.LLMS` |
| 记忆集合名称 | `.env` 中的 `LONG_TERM_MEMORY_COLLECTION_NAME` |

## 运行 pre-commit hooks

Hooks 在 `git commit` 时自动运行。手动运行：

```bash
make pre-commit
```

Hooks 包括：尾部空白检查、YAML/TOML/JSON 验证、秘密检测、ruff lint + format。

## 故障排除

**启动时数据库连接错误**
确保 PostgreSQL 正在运行，且 `.env` 中的 `POSTGRES_*` 变量匹配。使用 Docker：`make docker-up` 处理（包括迁移）。

**`could not translate host name "db"`**
`POSTGRES_HOST=db` 仅在 Docker 网络内解析（这是 Compose 服务名）。如果在主机上运行命令（例如本地 Python 流程中的 `make migrate` 或 `make dev`），请改为设置 `POSTGRES_HOST=localhost` — 数据库端口通过 `docker-compose.yml` 发布到主机。在容器内，保持使用 `db`。

**`detect-secrets` 阻止提交**
如果是误报，在被标记行的末尾添加 `# pragma: allowlist secret`。

**Langfuse 错误**
在 `.env` 中设置 `LANGFUSE_TRACING_ENABLED=false` 在开发期间完全禁用追踪。
