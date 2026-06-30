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

### 语言规则

- 可见回复、文档说明、提交信息和评审结论优先使用简体中文。
- 当用户输入其他语言时，先识别意图，再默认用简体中文回应；只有用户明确要求时才切换输出语言。
- 对行业标准术语，优先使用中文通译；必要时在括号中保留英文原名。
- 代码、命令、路径、API 字段、协议字段、日志事件名、依赖包名、品牌名和错误原文必须保留原文，不要为了中文化而改写字面量。
- 不要把语言规则用于改变代码语义、配置键名、数据库字段、接口契约或测试断言。

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

### 最小变更与范围控制

- **只碰你必须碰的东西，只收拾你自己的烂摊子。**
- 编辑现有代码时：
  - 不要“改进”相邻的代码、注释或格式。
  - 不要重构没有问题的代码。
  - 即使你的做法不同，也要保持与现有风格一致。
  - 如果你发现无关的死代码，请指出来——不要直接删除它。
- 当你的更改创建了孤立文件时：
  - 删除因您的修改而不再使用的导入项/变量/函数。
  - 除非明确被要求，否则不要删除已有的无效代码。
- **测试要求**：每一行修改后的代码都应该直接追溯到用户的请求。

## LangGraph 和 LangChain 模式

### 图结构
- 使用 `StateGraph` 构建 AI Agent 工作流
- 使用 Pydantic 模型定义清晰的状态 schema（参见 `app/schemas/graph.py`）
- 使用 `CompiledStateGraph` 用于生产工作流
- 实现 `AsyncPostgresSaver` 用于检查点和持久化
- 使用 `Command` 控制节点间的图流

### 智能体规划与响应边界

- 需要智能识别、语义判断、上下文指代、候选消歧或自然语言表达时，必须由智能体完成，不得用固定字符串规则、关键词表、硬编码样例或文本模板替代。
- Prompt 只描述抽象职责、能力边界、安全边界和输出 schema，不要把单条用户问题、具体业务样例、代码枚举值组合或“遇到某句话就输出某字段”的指令写进 prompt。
- 业务修复不能通过给 prompt 追加具体问法来“打补丁”；应优先修正 schema、状态建模、工具/数据边界、评估用例或智能体通用判别能力。
- 确定性代码只负责事实数据获取、权限校验、候选裁剪、结构化校验、状态流转、安全阻断和错误归一化；不得负责生成本应由智能体生成的自然语言业务回答。
- `Response` 类节点应基于结构化事实和智能体能力组织最终回答；不要用 f-string、拼接列表或固定段落模板充当用户可见的业务回复。仅系统级兜底错误、极短状态提示和测试断言说明可使用固定文案。
- 对集合级查询、单实体查询、分析类查询等边界，只能写成抽象分类规则和验收测试，不要写成特定用户句子的特判。
- 北斗站点、GNSS 实时数据和日监测数据可能是大体量事实；不得通过固定字符数、固定条数预览或 `Message.content` schema 限制裁剪事实数据来适配单次 LLM 输入。应使用结构化事实存储、数据引用、按任务检索、分块分析、聚合指标和 token 预算调度来管理上下文。
- 只有显式 `interrupt()` 等待用户补充、确认或消歧时，才允许进入 HITL 中断并展示干预卡片；系统异常、上游失败、上下文超预算、响应组装失败或流式传输错误必须走结构化错误状态和可重试提示，不得伪装成人工干预。

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

## 功能测试与验收

- 功能测试、前端验收、后端接口测试和集成测试优先参考 `docs/tests/{编号}-{功能名}.md`。
- 测试资料采用渐进式披露：先阅读对应功能的测试计划，只有当测试计划涉及登录、会话、订阅、删除会话、发送消息等认证状态时，再读取 `docs/tests/test-accounts.md` 获取测试账号。
- `AGENTS.md`、提交信息、评审结论和普通验收汇报中不要重复写出测试账号明文；需要说明账号来源时引用 `docs/tests/test-accounts.md` 路径即可。
- 不要将测试账号硬编码到业务代码、前端组件或生产配置中；自动化测试需要账号时，应优先通过测试 fixture、测试环境变量或测试说明文件读取。
- 使用测试账号验收前，先确认本地后端、数据库和种子数据已准备；若登录失败，先排查环境配置和测试数据，再判定功能失败。
- 功能测试失败时，优先排查代码实现、测试数据、后端服务、数据库和环境配置；不要默认修改 LLM prompt。

## LLM 输出评估

- 对 LLM 输出实现基于指标的评估（参见 `evals/` 目录）。
- 在 `evals/metrics/prompts/` 中创建 markdown 文件格式的自定义评估指标。
- 使用 Langfuse 追踪作为评估数据源。
- 生成带有成功率的 JSON 报告。
- 只有当 LLM 输出质量、推理格式、工具调用行为或评估指标不达标时，才考虑优化系统提示词、评估提示词或 LangGraph agent prompt。

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

## 本项目的十二诫

1. 所有路由必须有限流装饰器
2. 所有 LLM 操作必须有 Langfuse 追踪
3. 所有异步操作必须有适当的错误处理
4. 所有日志必须遵循结构化日志格式，使用 lowercase_underscore 事件名
5. 所有重试必须使用 tenacity 库
6. 所有控制台输出应使用 rich 格式化
7. 所有缓存仅存储成功响应
8. 所有导入必须在文件顶部
9. 所有数据库操作必须异步
10. 所有端点必须有适当的类型提示 and Pydantic 模型
11. 所有代码必须通过 `make typecheck`（pyright 标准模式）
12. 禁止使用浏览器默认弹窗（如 `confirm`/`alert`），应使用统一的 UI 组件（Modal）进行交互确认，以确保界面风格一致和美观。

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
- ❌ 使用浏览器原生的 alert/confirm 等弹窗
- ❌ 将具体用户问法、具体 intent 输出或用户可见业务回复硬编码进 prompt 或文本模板


## 进行更改时

#### 实施前置要求

- **不要妄下断言。不要掩饰困惑。坦诚地权衡利弊。**
- 在付诸实施前，必须满足以下要求：
  - 请明确陈述您的假设。如有疑问，请提出。
  - 如果存在多种解释，请将它们提出来——绝对不要默默地做出选择。
  - 如果存在更简单的方法，请提出来。必要时要坚持己见。
  - 如果有什么不清楚的地方，**停下来**。直接说出让你困惑的地方，然后向用户提问。

#### 修改现有代码步骤

修改代码前：

1. 先阅读现有实现
2. 检查代码库中的相关模式
3. 确保与现有代码风格一致
4. 添加带有结构化格式的适当日志
5. 包含带有早期返回的错误处理
6. 添加类型提示和 Pydantic 模型
7. 验证 LLM 调用已启用 Langfuse 追踪

## 新功能开发流程（Spec 驱动 + TDD）

所有新功能必须遵循本流程。未通过当前阶段的用户评审前，不得进入下一阶段，也不得提前编写实现代码。

### 文档目录与命名

- `docs/specs/`：功能需求与验收标准。
- `docs/designs/`：经确认的实现设计和完成清单。
- `docs/tests/`：编码前的测试计划。
- 同一功能的三个文档必须使用相同的编号和 kebab-case 名称，例如：
  - `docs/specs/001-account-deletion.md`
  - `docs/designs/001-account-deletion.md`
  - `docs/tests/001-account-deletion.md`

### 阶段 1：需求澄清与 Spec

1. 生成新功能 spec 前，必须向用户提问并确认功能边界，包括权限与参与者、输入输出、状态流转、非目标、数据保留/删除、幂等与并发、失败处理、异步任务和可量化验收标准；按功能实际情况裁剪问题。
2. 用户确认边界后，在 `docs/specs/` 创建 spec。spec 至少包含：`背景`、`目标`、`非目标`、`技术方案`、`验收` 和未解决的待确认项（如有）。
3. spec 中的“技术方案”仅描述供评审的方案方向；表结构、文件改动和执行细节必须留待 design 阶段明确。
4. 必须等待用户确认并通过 spec；此阶段不得创建 design、测试计划、测试代码或业务实现代码。

spec 最小模板：

```markdown
# {编号} {功能名称}

## 背景

## 目标

## 非目标

## 技术方案
<!-- Agent 提出方案方向，供用户评审。 -->

## 验收
- [ ] {可验证的验收项}

## 待确认问题
<!-- 无待确认项时写“无”。 -->
```

### 阶段 2：实现设计与 Checklist

1. spec 通过后才可在 `docs/designs/` 创建对应的 design 文档；此时仍不得编写代码。
2. design 必须从 spec 的目标、验收项及“必须实现”要求中提取全部功能，逐项列为 Markdown checklist。
3. design 必须清晰说明：涉及的数据表、字段和 Alembic 迁移；API/请求响应模型和状态流转；会修改或新增的文件；异步或同步执行方式及原因；事务、幂等、并发、错误处理、重试、日志、指标与安全影响。
4. checklist 只在对应实现和验证完成后勾选；不得以计划完成代替实现完成。
5. 当用户明确缩小范围（例如“暂不做复杂功能”）时，必须先同步 spec、design 和测试计划的当前范围；复杂项移入“非目标”“后续任务”或“延期项”，不得继续留在当前验收项中。
6. 每次实现或验证后，必须同步更新对应 checklist：已实现且已验证用 `[x]`，未实现保持 `[ ]` 并标注原因或后续归属；部分完成项必须拆分成可独立判断的子项。
7. 不得把功能标记为完成，除非代码、测试、spec、design、测试计划和实际验证结果达到一致。
8. 若发现文档与代码实现不一致，不得擅自在同一轮修正文档或代码来消除差异；必须先向用户报告不一致点、影响范围和可选处理路径，并等待用户确认下一步。
9. 必须等待用户确认并通过 design，才能生成测试计划。

design 最小模板：

```markdown
# {编号} {功能名称} — 实现设计

## 实现 Checklist
- [ ] {从 spec 提取的必须实现项}

## 数据与迁移

## API 与状态流转

## 文件改动

## 异步与事务设计

## 错误处理、观测与安全

## 实现计划
1. {具体、可执行的步骤}
```

### 阶段 3：测试计划评审

1. design 通过后，在 `docs/tests/` 创建同编号的测试计划，但不得写测试或实现代码。
2. 测试计划必须列出 happy path、边界场景和失败场景，并明确测试层级、测试数据/依赖、关键断言以及与验收标准的对应关系。
3. 必须等待用户审核测试计划后，才能进入编码阶段。

测试计划最小模板：

```markdown
# {编号} {功能名称} — 测试计划

## Happy Path

## 边界场景

## 失败场景

## 测试层级、数据与依赖

## 验收标准映射
```

### 阶段 4：TDD 编码与验收

1. 进入编码阶段前，为该功能创建分支，命名为 `codex/{编号}-{功能名}`；在该分支完成后续测试与实现。
2. 先编写测试代码并执行一次。测试应为失败（red）；仅当测试依赖尚不可用时可显式标记为 skip，并说明原因和解除条件。
3. 每次只实现使当前一个或一组最小测试场景通过的代码，运行测试至全绿（green）后再继续下一个场景；不得一次性实现大块未经测试验证的功能。
4. 每完成一个独立的绿色用例，可以创建一个小而聚焦的提交。所有提交必须保留对应的 spec、design 与测试计划关联。
5. 功能完成后，由用户亲自运行约定测试并检查输出。验收通过后，合并功能分支到目标分支并删除该功能分支。

### 流程门禁

- 未确认 spec：只允许需求澄清和 spec 编辑。
- 未确认 design：只允许 spec 和 design 编辑。
- 未确认测试计划：只允许文档编辑，不允许测试或实现代码。
- 未获得用户验收：不得将功能视为完成、合并分支或删除分支。

## 参考

- LangGraph 文档: https://langchain-ai.github.io/langgraph/
- LangChain 文档: https://python.langchain.com/docs/
- FastAPI 文档: https://fastapi.tiangolo.com/
- Langfuse 文档: https://langfuse.com/docs
