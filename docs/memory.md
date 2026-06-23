# 记忆

## 概述

该模板包含由 mem0 和 pgvector 驱动的长期记忆系统。记忆从对话中提取，存储为向量嵌入，并在每个请求上语义检索 — 为 agent 提供过去会话的上下文。

## 工作原理

```mermaid
sequenceDiagram
    participant G as LangGraph
    participant MS as MemoryService
    participant Cache as Cache (Valkey/TTL)
    participant M as mem0
    participant PG as pgvector

    Note over G: 每个聊天请求时
    G->>MS: search(user_id, query)
    MS->>Cache: get(memory:{user_id}:{hash})
    alt 缓存命中
        Cache-->>MS: 缓存结果
    else 缓存未命中
        MS->>M: memory.search(user_id, query)
        M->>PG: 向量相似性搜索
        PG-->>M: top-k 记忆
        M-->>MS: 格式化结果
        MS->>Cache: set(key, result, TTL)
    end
    MS-->>G: 相关记忆字符串

    Note over G: LLM 响应后（后台）
    G-)MS: add(user_id, messages)
    MS->>M: memory.add(messages, user_id)
    M->>PG: 存储新嵌入
```

## 缓存层

记忆搜索结果被缓存，以避免在同一 TTL 窗口内对类似问题进行重复的 pgvector 查询。

- **有 Valkey/Redis**：缓存在应用实例间共享。在 `.env` 中设置 `VALKEY_HOST`。
- **无 Valkey**：降级到内存 `TTLCache` — 单实例运行良好。

缓存键：`memory:{user_id}:{sha256(query)[:16]}`
TTL：`CACHE_TTL_SECONDS`（默认：60s）

仅缓存成功且非空的结果。错误永不缓存。

## 记忆更新

LLM 生成响应后，记忆通过 `asyncio.create_task` 在**后台**更新。这意味着：
- 响应立即返回，不等待 mem0 完成
- 记忆更新不会阻塞或减慢聊天响应

## 配置

| 变量 | 默认值 | 描述 |
| --- | --- | --- |
| `LONG_TERM_MEMORY_COLLECTION_NAME` | `longterm_memory_nv_embed_v1` | pgvector 集合名称 |
| `LONG_TERM_MEMORY_MODEL` | `deepseek-v4-flash` | mem0 通过 LangChain 调用的 DeepSeek 记忆提取模型 |
| `LONG_TERM_MEMORY_EMBEDDER_MODEL` | `nvidia/nv-embed-v1` | 通过 LangChain `NVIDIAEmbeddings` 调用的嵌入模型 |
| `LONG_TERM_MEMORY_EMBEDDER_DIMENSIONS` | `4096` | NV-Embed-v1 输出维度，必须与 pgvector 集合匹配 |
| `NVIDIA_API_KEY` | — | NVIDIA AI Endpoints 所需的访问密钥 |
| `CACHE_TTL_SECONDS` | `60` | 记忆搜索缓存 TTL |

> 不能复用维度不同的 pgvector 集合。默认集合名使用 `longterm_memory_nv_embed_v1`，以保留已有 BGE-M3 或 OpenAI 数据；如需迁移历史记忆，请重新嵌入和写入向量。

> `nv-embed-v1` 输出 4096 维向量，超过 pgvector HNSW 索引的 2000 维限制，因此该集合使用精确余弦检索，不创建 HNSW 索引。

## 启动预热

在启动时，在应用生命周期中调用 `memory_service.initialize()`。这建立 pgvector 连接池并运行 mem0 的架构检查，因此第一个用户请求不需支付约 130ms 的冷启动成本。

## 每用户隔离

每个用户的记忆使用 `user_id` 作为命名空间独立存储和搜索。用户不能访问彼此的记忆。
