<div align="right"><a href="./SECURITY.en-US.md">English</a></div>

# 安全策略

## 支持的版本

这是一个模板仓库。安全修复应用于 `master` 分支。Fork 维护者负责保持其 Fork 更新。

## 报告漏洞

**请勿**为安全漏洞公开 GitHub issue。

私下通过 [GitHub 安全咨询](https://github.com/advisories/new) 或直接电子邮件联系维护者。包括：

- 漏洞描述及其潜在影响
- 再现步骤
- 任何建议的缓解措施

对于已确认的漏洞，您可以在 48 小时内收到确认，并在 7 天内收到修复或缓解计划。

## 使用此模板时的安全考虑

**部署到生产环境之前：**

- 设置一个强的随机 `JWT_SECRET_KEY`（32+ 字符）
- 轮换所有 secrets — 永不使用 `.env.example` 中的值
- 设置 `DEBUG=false`
- 将 `ALLOWED_ORIGINS` 限制为您实际的前端域名
- 如果您不想将对话数据发送到 Langfuse，设置 `LANGFUSE_TRACING_ENABLED=false`
- 使用环境特定的 `.env` 文件 — 永不将 secrets 提交到 git

**模板为保护您所做的：**

- 密码使用 bcrypt 哈希（永不存储明文）
- JWT 令牌包含 `jti` 声明以确保唯一性
- 所有用户输入在使用前进行清理
- 认证和聊天端点限流
- 通过 `detect-secrets` pre-commit hook 检测 secrets
- CORS 已配置（在生产中限制 `ALLOWED_ORIGINS`）
