<div align="right"><a href="./README.en-US.md">English</a></div>

# FastAPI LangGraph Agent 模板

一个生产就绪的 AI Agent 后端构建模板，使用 FastAPI 和 LangGraph。处理复杂部分 — 有状态对话、长期记忆、工具调用、可观测性、限流、认证 — 让您专注于 Agent 逻辑。

**为 AI 工程师构建**，提供坚实基础，而非教程项目。

---

## 由 Atlas Cloud 提供支持 — LangGraph Agent 的即插即用 LLM 后端

<div align="center">
  <a href="https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=fastapi-langgraph-agent-production-ready-template">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/atlas-cloud-logo-dark.png"/>
      <img src="docs/atlas-cloud-logo.png" alt="Atlas Cloud" width="200"/>
    </picture>
  </a>
</div>

[**Atlas Cloud**](https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=fastapi-langgraph-agent-production-ready-template) 提供一个 **OpenAI 兼容的 LLM API**，可无缝集成到此 FastAPI + LangGraph 模板中 — 无需更改 Agent 图逻辑。只需更换 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`，即可通过单一统一端点访问 **DeepSeek、Qwen、GLM、Kimi、MiniMax、Gemini、Claude、GPT** 等。

此模板中的 `LLMRegistry` 使用 `langchain_openai.ChatOpenAI` — Atlas Cloud 兼容，因此您无需触碰任何 LangGraph 逻辑即可即时访问 59+ 精选推理模型。

### 快速设置

**步骤 1 — 获取免费 API 密钥：** [atlascloud.ai/console/coding-plan](https://www.atlascloud.ai/console/coding-plan)

**步骤 2 — 更新 `.env.development`：**

```env
OPENAI_API_KEY=<your-atlascloud-key>
OPENAI_BASE_URL=https://api.atlascloud.ai/v1
DEFAULT_LLM_MODEL=deepseek-ai/deepseek-v4-pro
```

**步骤 3 — 或直接在代码中使用：**

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-ai/deepseek-v4-pro",
    openai_api_base="https://api.atlascloud.ai/v1",
    openai_api_key="<your-atlascloud-key>",
    max_tokens=512,  # 推理模型需要 max_tokens >= 512
)
```

这可以作为 `ChatOpenAI` 的直接替代品，在您的 LangGraph Agent 中任何地方使用 — 包括 `LLMRegistry`、循环降级服务和 mem0 长期记忆。

<details>
<summary>📋 完整模型目录（59 个 LLM 可用）</summary>

| 模型 ID | 提供商 |
|---|---|
| `deepseek-ai/DeepSeek-V3-0324` | DeepSeek |
| `deepseek-ai/deepseek-r1-0528` | DeepSeek |
| `deepseek-ai/DeepSeek-V3.1` | DeepSeek |
| `deepseek-ai/DeepSeek-V3.1-Terminus` | DeepSeek |
| `deepseek-ai/DeepSeek-V3.2-Exp` | DeepSeek |
| `deepseek-ai/deepseek-v3.2` | DeepSeek |
| `qwen/qwen3-32b` | Alibaba Qwen |
| `qwen/qwen3-8b` | Alibaba Qwen |
| `qwen/qwen3-235b-a22b-thinking-2507` | Alibaba Qwen |
| `qwen/qwen3-30b-a3b` | Alibaba Qwen |
| `qwen/qwen3-30b-a3b-thinking-2507` | Alibaba Qwen |
| `Qwen/Qwen3-Coder` | Alibaba Qwen |
| `Qwen/Qwen3-235B-A22B-Instruct-2507` | Alibaba Qwen |
| `Qwen/Qwen3-Next-80B-A3B-Instruct` | Alibaba Qwen |
| `Qwen/Qwen3-Next-80B-A3B-Thinking` | Alibaba Qwen |
| `Qwen/Qwen3-30B-A3B-Instruct-2507` | Alibaba Qwen |
| `Qwen/Qwen3-VL-235B-A22B-Instruct` | Alibaba Qwen |
| `moonshotai/Kimi-K2-Instruct` | Moonshot AI |
| `moonshotai/Kimi-K2-Instruct-0905` | Moonshot AI |
| `moonshotai/Kimi-K2-Thinking` | Moonshot AI |
| `moonshotai/kimi-k2.5` | Moonshot AI |
| `zai-org/GLM-4.6` | Zhipu AI |
| `zai-org/glm-4.7` | Zhipu AI |
| `MiniMaxAI/MiniMax-M2` | MiniMax |
| `minimaxai/minimax-m2.1` | MiniMax |
| `google/gemini-2.5-flash` | Google |
| `google/gemini-2.5-flash-preview-202509` | Google |
| `google/gemini-2.5-flash-lite` | Google |
| `google/gemini-2.5-flash-lite-preview-202509` | Google |
| `google/gemini-2.5-pro` | Google |
| `google/gemini-3-flash-preview` | Google |
| `google/gemini-2.0-flash` | Google |
| `google/gemini-2.0-flash-lite` | Google |
| `openai/gpt-5.1` | OpenAI |
| `openai/gpt-5.1-chat` | OpenAI |
| `openai/gpt-5.1-codex` | OpenAI |
| `openai/gpt-5.1-codex-mini` | OpenAI |
| `openai/gpt-5.1-codex-max` | OpenAI |
| `openai/gpt-4o` | OpenAI |
| `openai/gpt-4o-mini` | OpenAI |
| `openai/gpt-4.1` | OpenAI |
| `openai/gpt-4.1-mini` | OpenAI |
| `openai/gpt-4.1-nano` | OpenAI |
| `openai/o1` | OpenAI |
| `openai/o3` | OpenAI |
| `openai/o3-mini` | OpenAI |
| `openai/o4-mini` | OpenAI |
| `openai/o3-pro` | OpenAI |
| `openai/gpt-5` | OpenAI |
| `openai/gpt-5-chat` | OpenAI |
| `openai/gpt-5-codex` | OpenAI |
| `openai/gpt-5-mini` | OpenAI |
| `openai/gpt-5-nano` | OpenAI |
| `openai/gpt-5-pro` | OpenAI |
| `openai/gpt-5.2` | OpenAI |
| `openai/gpt-5.2-chat` | OpenAI |
| `anthropic/claude-sonnet-4-20250514` | Anthropic |
| `anthropic/claude-haiku-4.5-20251001` | Anthropic |
| `anthropic/claude-sonnet-4.5-20250929` | Anthropic |
| `anthropic/claude-opus-4.1-20250805` | Anthropic |
| `anthropic/claude-opus-4-20250514` | Anthropic |
| `anthropic/claude-opus-4.5-20251101` | Anthropic |

[查看实时模型列表 →](https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=fastapi-langgraph-agent-production-ready-template)

</details>

---

## 功能特性

- **LangGraph** 有状态 Agent，支持检查点、工具调用和人在回路
- **长期记忆** 通过 mem0 + pgvector — 每用户语义搜索，带缓存
- **LLM 服务** 支持循环模型降级、指数退避重试和总超时预算
- **Langfuse** 追踪所有 LLM 调用；Prometheus 指标 + Grafana 仪表板
- **JWT 认证** 配会话管理；通过 slowapi 限流
- **Alembic** 迁移；可选 Valkey/Redis 缓存层
- **结构化日志** 每次输出都带有 request/session/user 上下文

## 快速开始

```bash
git clone <repo-url> my-agent && cd my-agent
cp .env.example .env.development   # 填写您的密钥
make install
make docker-up                     # 启动 API + PostgreSQL
```

打开 [http://localhost:8000/docs](http://localhost:8000/docs) 查看交互式 API。

> 无 Docker 的本地开发，请参见 [docs/getting-started.md](docs/getting-started.md)。

## 文档

| 指南 | 内容 |
|---|---|
| [快速开始](docs/getting-started.md) | 前置要求、本地设置、首次 API 调用 |
| [架构](docs/architecture.md) | 系统设计、请求流程、组件图 |
| [配置](docs/configuration.md) | 所有环境变量及默认值 |
| [认证](docs/authentication.md) | JWT 流程、会话、端点参考 |
| [数据库与迁移](docs/database.md) | 架构、Alembic 迁移、pgvector |
| [LLM 服务](docs/llm-service.md) | 模型、重试、降级、超时预算 |
| [记忆](docs/memory.md) | mem0 长期记忆、缓存层 |
| [可观测性](docs/observability.md) | Langfuse、结构化日志、Prometheus、性能分析 |
| [评估](docs/evaluation.md) | 评估框架、自定义指标、报告 |
| [Docker](docs/docker.md) | Docker、Compose、完整监控堆栈 |

## 项目结构

```
app/
  api/v1/          # 路由处理程序
  core/
    langgraph/     # Agent 图 + 工具
    prompts/       # 系统提示词模板
    cache.py       # Valkey/Redis + 内存降级
    config.py      # 设置
    middleware.py  # 指标、日志上下文、性能分析
    limiter.py     # 限流
  models/          # SQLModel ORM 模型
  schemas/         # Pydantic 请求/响应 schema
  services/        # LLM、数据库、记忆服务
alembic/           # 数据库迁移
evals/             # LLM 评估框架
```

## 贡献

欢迎提交 PR。请阅读 [docs/getting-started.md](docs/getting-started.md) 设置环境，然后遵循 [AGENTS.md](AGENTS.md) 中的编码规范。

私下报告安全问题 — 参见 [SECURITY.md](SECURITY.md)。

## 许可证

参见 [LICENSE](LICENSE)。

## 常见问题

### 概述

**这是什么模板？**
一个生产就绪的 AI Agent 后端基础，使用 FastAPI + LangGraph 构建。它捆绑了您需要手动连接的组件：有状态对话、长期记忆、工具调用、可观测性、限流和 JWT 认证。

**这与基本 LangGraph 设置有何不同？**
基础 LangGraph 快速入门仅止于"agent 本地运行"。此模板添加了 Alembic 迁移、mem0 + pgvector 长期记忆、Langfuse 追踪、Prometheus + Grafana 仪表板、JWT 会话、slowapi 限流、带有每请求上下文的结构化日志，以及循环降级 LLM 服务 — 这些都是您原本需要单独构建的生产级特性。

### 设置与配置

**需要 Docker 吗？**
推荐但非必需。`make docker-up` 一起启动 API + PostgreSQL。纯本地设置请参见 [docs/getting-started.md](docs/getting-started.md)。

**支持哪些 LLM 提供商？**
目前：**仅 OpenAI**，通过 `app/services/llm/registry.py` 中的 `LLMRegistry`。多提供商支持（Anthropic、Google、OpenRouter）通过 LangChain 的 `init_chat_model` 已列入计划 — 参见 [#51](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template/issues/51)。通过 `.env.development` 中的 `DEFAULT_LLM_MODEL` 配置模型。

**如何配置长期记忆？**
长期记忆是自托管的：mem0 在进程内运行并通过 pgvector 持久化到您现有的 PostgreSQL — 无需单独的 mem0 云账户或 API 密钥。您只需要一个有效的 `OPENAI_API_KEY`（用于事实提取 + 嵌入）和启用的 pgvector 扩展。详情请参见 [docs/memory.md](docs/memory.md)。

### 开发

**如何添加自定义工具？**
在 `app/core/langgraph/tools/` 中放置一个 LangChain `@tool` 装饰的函数，并在该包导出的 `tools` 列表中注册。Agent 在下次启动时自动拾取；无需更改图。

**LLM 服务如何处理失败？**
两层：(1) 通过 `tenacity` 的每调用指数退避重试，(2) **循环降级** — 如果活动模型用尽重试次数，服务轮转到 `LLMRegistry` 中的下一个模型并继续。总超时预算限制整个调用，使延迟保持有界。参见 [docs/llm-service.md](docs/llm-service.md)。

**可以在不使用 Langfuse 的情况下使用吗？**
可以。设置 `LANGFUSE_TRACING_ENABLED=false`（或省略 Langfuse 密钥）。Agent 运行不变；结构化日志仍然捕获 request/session/user 上下文。

### 故障排除

**API 无法启动**
- 确保 PostgreSQL 正在运行（`make docker-up` 会随 API 一起启动）
- 确认 `.env.development` 存在 — 从 `.env.example` 复制并填写必需密钥
- 应用迁移：`make migrate`

**记忆/语义搜索返回空**
- 验证 PostgreSQL 实例中已启用 `pgvector` 扩展
- 确认 `OPENAI_API_KEY` 有效（mem0 调用 OpenAI 进行事实提取 + 嵌入）
- 检查 `.env.development` 中是否设置了 `LONG_TERM_MEMORY_MODEL` 和 `LONG_TERM_MEMORY_EMBEDDER_MODEL`

**限流过于严格**
限制在 `app/core/limiter.py`（slowapi）中定义。调整该文件中的每路由装饰器或默认限制。参见 [docs/configuration.md](docs/configuration.md) 了解相关环境变量。
