# 004 北斗凭据绑定与校验 — 测试计划

## Happy Path

1. **未绑定状态查询**
   - 测试层级：API 测试。
   - 测试文件：`tests/api/test_beidou_credentials_routes.py`。
   - 测试数据：
     - 使用现有测试用户登录 token 或 session token。
     - Fake 凭据服务返回未绑定。
   - 关键断言：
     - `GET /api/v1/beidou/credentials/status` 返回 200。
     - 响应包含 `bound=false`。
     - `username`、`last_verified_at`、`session_expires_at` 为 `null`。
     - 响应不包含 `password`、`encrypted_password`、`session_uuid`。

2. **已绑定状态查询返回用户名**
   - 测试层级：API 测试。
   - 测试数据：
     - Fake 凭据服务返回已绑定记录。
   - 关键断言：
     - 返回 `bound=true`。
     - 返回北斗用户名原文。
     - 返回 `last_verified_at` 和 `session_expires_at`。
     - 不返回明文密码、加密密码或 `SessionUUID`。

3. **首次绑定成功**
   - 测试层级：服务测试 + API 测试。
   - 测试文件：
     - `tests/unit/test_beidou_credential_service.py`
     - `tests/api/test_beidou_credentials_routes.py`
   - 测试数据：
     - 输入北斗用户名和密码。
     - Fake 北斗 client 返回 `ResponseCode="200"` 和 `SessionUUID`。
     - Fake 加密服务返回可识别密文。
   - 关键断言：
     - 先调用上游登录验证，再写入数据库。
     - 保存 `beidou_username`。
     - 保存的是加密密码，不是请求中的明文密码。
     - 保存加密后的 `SessionUUID`。
     - `session_expires_at` 约等于当前时间 + `BEIDOU_SESSION_TTL_SECONDS`。
     - API 返回 `bound=true` 和用户名。

4. **更新凭据成功覆盖旧记录**
   - 测试层级：服务测试。
   - 测试数据：
     - 数据库已有旧凭据。
     - 新凭据上游验证成功。
   - 关键断言：
     - 仍然只有一条该 `user_id` 的凭据记录。
     - 用户名、加密密码、加密 session 和 `last_verified_at` 被更新。
     - 旧密文不再保留在当前记录中。

5. **解绑已绑定凭据**
   - 测试层级：服务测试 + API 测试。
   - 测试数据：
     - 数据库已有凭据记录。
   - 关键断言：
     - `DELETE /api/v1/beidou/credentials` 返回 200。
     - 响应为 `bound=false`。
     - 数据库中该用户凭据记录被删除。
     - 后续状态查询返回未绑定。

6. **解绑未绑定用户保持幂等**
   - 测试层级：API 测试。
   - 测试数据：
     - 用户没有凭据记录。
   - 关键断言：
     - DELETE 返回 200。
     - 响应为 `bound=false`。
     - 不抛出 404 或数据库异常。

7. **用户 token 与 session token 都能访问用户级凭据接口**
   - 测试层级：API 测试。
   - 测试数据：
     - 使用登录后用户 token。
     - 使用创建会话后的 session token。
   - 关键断言：
     - 两类 token 均可查询同一用户的凭据状态。
     - session token 解析出的 `session.user_id` 被用于用户级凭据查询。

8. **配置项加载**
   - 测试层级：单元测试。
   - 测试文件：可放在 `tests/unit/test_beidou_config.py` 或配置相关测试中。
   - 测试数据：
     - monkeypatch 环境变量设置北斗 API 基址、加密密钥、超时和 TTL。
   - 关键断言：
     - `settings` 能读取 `BEIDOU_API_BASE_URL`。
     - `settings` 能读取 `BEIDOU_CREDENTIAL_ENCRYPTION_KEY`。
     - `BEIDOU_API_TIMEOUT_SECONDS` 和 `BEIDOU_SESSION_TTL_SECONDS` 类型正确。

## 边界场景

1. **用户名为空或过长**
   - 测试层级：schema/API 测试。
   - 输入：
     - `username=""`
     - `username="   "`
     - 超过设计上限的用户名。
   - 关键断言：
     - 返回 422。
     - 不调用北斗上游。
     - 不写数据库。

2. **密码长度不符合北斗文档约束**
   - 测试层级：schema/API 测试。
   - 输入：
     - 长度小于 12。
     - 长度大于 64。
   - 关键断言：
     - 返回 422。
     - 不调用北斗上游。
     - 不写数据库。

3. **更新时新凭据验证失败保留旧凭据**
   - 测试层级：服务测试。
   - 测试数据：
     - 数据库已有旧凭据。
     - 新凭据上游返回账号密码错误。
   - 关键断言：
     - 服务返回认证失败错误。
     - 旧凭据仍存在。
     - 旧用户名、旧密码密文、旧 session 密文未被覆盖。

4. **`SessionUUID` 缺失或格式异常**
   - 测试层级：北斗 client 单元测试。
   - 测试数据：
     - 上游返回 `ResponseCode="200"` 但缺少 `SessionUUID`。
     - 上游返回空字符串或非 UUID 字符串。
   - 关键断言：
     - 视为上游响应格式异常。
     - 不保存凭据。
     - API 映射为 502 或设计中定义的上游响应异常。

5. **加密服务可逆性**
   - 测试层级：单元测试。
   - 测试文件：`tests/unit/test_beidou_crypto.py`。
   - 测试数据：
     - 固定 Fernet 测试密钥。
     - 明文密码和 `SessionUUID`。
   - 关键断言：
     - 加密结果不等于明文。
     - 解密后等于原文。
     - 多次加密同一明文可得到不同密文，但都可解密。

6. **状态响应不泄露 session 有效凭证**
   - 测试层级：API 测试。
   - 测试数据：
     - 已绑定记录包含加密 session。
   - 关键断言：
     - 响应中没有 `session_uuid`、`session_uuid_encrypted` 或任何可复用上游会话值。

7. **跨用户隔离**
   - 测试层级：服务测试/API 测试。
   - 测试数据：
     - 用户 A 和用户 B 分别存在或不存在凭据。
   - 关键断言：
     - 用户 A 查询不到用户 B 的凭据。
     - 用户 A 解绑不影响用户 B 的凭据。
     - `user_id` 唯一约束只限制单用户一条记录，不限制不同用户使用相同北斗用户名。

8. **时间计算边界**
   - 测试层级：服务测试。
   - 测试数据：
     - 固定当前时间。
     - `BEIDOU_SESSION_TTL_SECONDS=28800`。
   - 关键断言：
     - `session_expires_at` 使用 UTC 时间。
     - 时间误差在可接受范围内。

## 失败场景

1. **北斗账号密码错误**
   - 测试层级：client/service/API 测试。
   - Mock 上游返回 `ResponseCode="400111"`。
   - 关键断言：
     - API 返回 400 或 401。
     - 错误消息可理解。
     - 不保存新凭据。
     - 不记录明文密码。

2. **北斗账号锁定、停用或密码过期**
   - 测试层级：client/service 测试。
   - Mock 上游返回：
     - `400113` 密码过期。
     - `400114` 账号锁定或停用。
   - 关键断言：
     - 返回业务失败错误。
     - 不保存凭据。
     - 错误原因保留上游语义。

3. **北斗权限不足**
   - 测试层级：client/service 测试。
   - Mock 上游返回 `400000`。
   - 关键断言：
     - 不保存凭据。
     - 返回权限不足说明。

4. **北斗上游超时**
   - 测试层级：client 测试。
   - Mock `httpx.TimeoutException`。
   - 关键断言：
     - 使用 tenacity 指数退避重试。
     - 最终失败映射为 503。
     - 不写数据库。

5. **北斗上游网络错误**
   - 测试层级：client 测试。
   - Mock `httpx.RequestError`。
   - 关键断言：
     - 可重试。
     - 最终失败映射为 503。
     - 日志记录失败类别，不含密码。

6. **北斗上游 5xx**
   - 测试层级：client 测试。
   - Mock 连续 500 或前两次 500、第三次成功。
   - 关键断言：
     - 连续失败最终返回可重试错误。
     - 第三次成功时服务继续保存凭据。
     - 只有最终成功才写数据库。

7. **北斗上游 4xx HTTP 错误**
   - 测试层级：client 测试。
   - Mock HTTP 状态码 400/403。
   - 关键断言：
     - 不按网络故障重试。
     - 映射为认证/权限/请求错误。
     - 不保存凭据。

8. **北斗响应不是 JSON 或结构异常**
   - 测试层级：client 测试。
   - Mock JSON 解析失败或返回数组/字符串。
   - 关键断言：
     - 映射为 502。
     - 不保存凭据。

9. **加密密钥未配置**
   - 测试层级：crypto/service/API 测试。
   - 测试数据：
     - `BEIDOU_CREDENTIAL_ENCRYPTION_KEY=""`。
   - 关键断言：
     - 绑定/更新返回 500 配置错误。
     - 不调用或不完成数据库写入。
     - 日志记录配置缺失，不含密码。

10. **加密密钥格式无效**
    - 测试层级：crypto/service 测试。
    - 测试数据：
      - 非 Fernet 格式密钥。
    - 关键断言：
      - 返回配置错误。
      - 不保存凭据。

11. **数据库写入失败**
    - 测试层级：服务测试。
    - 测试数据：
      - Fake async session 在 commit 或 execute 时抛异常。
    - 关键断言：
      - 返回 500。
      - 使用 `logger.exception()` 记录堆栈。
      - 错误响应不暴露数据库内部细节或凭据。

12. **未认证请求**
    - 测试层级：API 测试。
    - 请求：
      - 不带 Authorization header。
      - 无效 token。
    - 关键断言：
      - 返回 401。
      - 不调用凭据服务或北斗上游。

13. **本地用户不存在**
    - 测试层级：API/依赖单元测试。
    - 测试数据：
      - token subject 指向不存在的 user 或 session。
    - 关键断言：
      - 返回 404 或现有认证依赖约定错误。
      - 不调用北斗上游。

14. **日志敏感信息防泄露**
    - 测试层级：单元测试。
    - 测试方式：
      - monkeypatch logger，捕获 info/warning/exception 调用参数。
      - 使用明显可识别密码和 fake `SessionUUID`。
    - 关键断言：
      - 日志参数和值中不包含明文密码。
      - 日志参数和值中不包含 `SessionUUID` 明文。
      - 日志事件名为 lowercase_with_underscores。

## 测试层级、数据与依赖

1. **单元测试**
   - `tests/unit/test_beidou_crypto.py`
   - `tests/unit/test_beidou_client.py`
   - `tests/unit/test_beidou_credential_service.py`
   - `tests/unit/test_beidou_auth_dependency.py`
   - 主要覆盖加密、上游 client、响应码映射、服务事务逻辑和认证依赖。

2. **API 测试**
   - `tests/api/test_beidou_credentials_routes.py`
   - 使用现有 `httpx.AsyncClient` + ASGITransport 测试风格。
   - 通过 monkeypatch 替换凭据服务或北斗 client，避免真实网络。

3. **迁移/集成测试**
   - 可在现有集成测试基础上增加迁移验证，或在编码阶段使用 Alembic 迁移命令人工验证。
   - 验证 `beidou_credential` 表存在、`user_id` 唯一约束生效、外键引用 `user.id`。
   - 若本地没有 PostgreSQL 环境，至少运行 Alembic migration import 检查和单元级模型 metadata 检查。

4. **HTTP Mock**
   - 不使用真实北斗账号作为自动化测试数据。
   - 使用 fake async client 或 monkeypatch `BeidouClient.login`。
   - 覆盖成功、业务失败、网络失败、超时、响应格式异常和重试。

5. **数据库 Mock**
   - 服务单元测试优先使用 fake repository / fake async session，验证事务和覆盖逻辑。
   - API 测试通过 monkeypatch service，重点验证路由、认证、响应契约和不泄露字段。
   - 集成测试再验证真实数据库约束。

6. **时间控制**
   - 使用 monkeypatch 固定 UTC 当前时间，验证 `last_verified_at` 和 `session_expires_at`。

7. **敏感数据约束**
   - 测试资料不得写入真实北斗用户名密码。
   - 自动化测试使用明显 fake 值，例如 `fake_beidou_user`、`FakePassword123!`。
   - 普通验收汇报不重复写任何真实测试账号；如后续需要真实账号验收，账号来源引用 `docs/tests/test-accounts.md` 或测试环境变量。

8. **验收前验证命令**
   - 编码阶段至少运行：
     - `uv run pytest tests/unit/test_beidou_crypto.py`
     - `uv run pytest tests/unit/test_beidou_client.py`
     - `uv run pytest tests/unit/test_beidou_credential_service.py`
     - `uv run pytest tests/api/test_beidou_credentials_routes.py`
     - `make check`
   - 如本地 PostgreSQL 可用，再运行迁移验证：
     - `make migrate`

## 验收标准映射

- **未绑定北斗凭据的用户查询绑定状态时，返回未绑定状态**
  - 覆盖测试：未绑定状态查询。

- **已绑定北斗凭据的用户查询绑定状态时，返回已绑定状态和北斗用户名**
  - 覆盖测试：已绑定状态查询返回用户名。

- **用户提交北斗用户名和密码绑定时，系统必须先调用北斗登录认证接口验证可用性**
  - 覆盖测试：首次绑定成功、北斗账号密码错误、北斗上游超时。

- **北斗登录认证失败时，系统不保存或覆盖用户已有有效凭据，并返回可理解错误**
  - 覆盖测试：北斗账号密码错误、更新时新凭据验证失败保留旧凭据、账号锁定/停用/密码过期。

- **北斗登录认证成功时，系统加密保存北斗密码，并保存可复用的会话信息**
  - 覆盖测试：首次绑定成功、加密服务可逆性、状态响应不泄露 session 有效凭证。

- **用户更新北斗凭据时，新凭据必须重新通过上游验证后才能覆盖旧凭据**
  - 覆盖测试：更新凭据成功覆盖旧记录、更新时新凭据验证失败保留旧凭据。

- **用户可以解绑自己的北斗凭据，解绑后状态接口返回未绑定**
  - 覆盖测试：解绑已绑定凭据、解绑未绑定用户保持幂等。

- **解绑后，所有需要北斗/GNSS 上游数据的后续能力应能识别授权缺失并提示用户绑定凭据**
  - 本功能范围内覆盖：解绑后状态查询返回未绑定。
  - 后续 GNSS 分析功能测试中继续覆盖 Graph `Gate` 授权缺失路径。

- **前端或 API 响应中不得返回明文密码、加密密码或 `SessionUUID`**
  - 覆盖测试：未绑定状态查询、已绑定状态查询、首次绑定成功、状态响应不泄露 session 有效凭证。

- **日志不得记录明文密码、加密前密码或 `SessionUUID` 明文**
  - 覆盖测试：日志敏感信息防泄露。

- **缺少加密密钥配置时，系统拒绝保存凭据并返回配置错误**
  - 覆盖测试：加密密钥未配置、加密密钥格式无效。

- **本功能相关路由必须使用现有认证依赖和限流装饰器**
  - 覆盖测试：未认证请求、用户 token 与 session token 都能访问用户级凭据接口；限流装饰器通过代码审查和路由测试确认。

- **本功能相关数据库操作必须异步**
  - 覆盖测试：服务单元测试使用 async 调用路径；代码审查确认不调用同步 `DatabaseService` 写北斗凭据。

- **相关代码在后续实现阶段必须通过 `make check` 或等价验证**
  - 覆盖验证：验收前验证命令中的 `make check`。
