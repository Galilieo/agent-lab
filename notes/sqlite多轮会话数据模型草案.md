# SQLite 多轮会话数据模型草案

> 文档角色：记录 agent-lab 阶段 5 的最小逻辑数据模型，以及已经落地验证的表关系和当前实现边界。

## 1. `conversation`

`conversation` 表示一段可持续、可恢复的对话。

| 字段 | 约束 | 职责 |
| --- | --- | --- |
| `conversation_id` | 主键 | 唯一标识一段会话，对应 `ChatRequest.conversation_id` |
| `status` | 必填 | 保存会话状态，当前最小值为 `active` 和 `closed` |
| `created_at` | 必填 | 记录会话创建时间 |
| `updated_at` | 必填 | 记录会话最后更新时间 |

当前项目没有用户系统，因此暂不增加 `user_id`。模型可能在同一会话中切换，因此 `model` 不属于 `conversation`。

## 2. `message`

`message` 保存已经进入会话历史的有效内容。

| 字段 | 约束 | 职责 |
| --- | --- | --- |
| `message_id` | 主键 | 唯一标识一条消息 |
| `conversation_id` | 外键 | 指向消息所属的 `conversation` |
| `role` | 必填 | 区分 `user` 和 `assistant` 消息 |
| `content` | 必填 | 保存用户问题或助手回答 |
| `created_at` | 必填 | 记录消息创建时间 |

读取会话历史的目标查询是先按 `conversation_id` 筛选，再按 `created_at` 和 `message_id` 稳定排序，因此组合索引设计为：

```text
(conversation_id, created_at, message_id)
```

`conversation_id` 放在最左侧，与查询的首要筛选条件一致；`message_id` 在时间相同时提供稳定顺序。

## 3. `model_call`

`model_call` 保存每一次真实的外部模型调用尝试。失败调用也需要记录，但不会被当成有效的助手消息。

| 字段 | 约束 | 职责 |
| --- | --- | --- |
| `model_call_id` | 主键 | 唯一标识一次模型调用尝试 |
| `conversation_id` | 外键 | 指向调用所属的 `conversation` |
| `request_message_id` | 外键 | 指向触发调用的 `user message` |
| `response_message_id` | 可为空外键 | 成功时指向生成的 `assistant message`；失败时为空 |
| `model` | 必填 | 记录本次实际调用的模型 |
| `outcome` | 必填 | 区分 `succeeded`、`timeout`、`connection_error`、`upstream_error` 和 `invalid_response` |
| `upstream_status` | 可为空 | 记录上游 HTTP 状态码；未取得响应时为空 |
| `latency_ms` | 必填 | 记录本次调用耗时 |
| `prompt_tokens` | 可为空 | 记录输入 Token 数；上游未提供时为空 |
| `completion_tokens` | 可为空 | 记录输出 Token 数；上游未提供时为空 |
| `total_tokens` | 可为空 | 记录总 Token 数；上游未提供时为空 |
| `created_at` | 必填 | 记录调用创建时间，用于追踪调用和重试顺序 |

`outcome` 表示应用对整次模型调用的分类，`upstream_status` 只表示 HTTP 层状态码。两者不能合并，例如：

```text
outcome = invalid_response
upstream_status = 200
```

这表示 HTTP 请求成功，但响应正文不是可用的模型回答。

## 4. 表关系

```text
conversation 1 ── N message
conversation 1 ── N model_call
user message  1 ── N model_call
model_call 1 ── 0..1 assistant message
```

- 一个会话可以包含多条用户和助手消息。
- 同一条用户消息可能因超时或其他失败触发多次模型调用。
- 成功调用可以关联一条助手消息；失败调用的 `response_message_id` 为空。
- `request_message_id` 不能设置为唯一值，否则会阻止同一条用户消息发起重试。

## 5. 数据量边界练习

场景：

1. 用户在会话 A 中发送“记住，我今年 18 岁”，模型成功回答。
2. 用户继续询问“我今年多大？”。
3. 第二次请求的首次模型调用超时，重试后成功回答“18 岁”。

最终应保存：

| 数据 | 数量 | 原因 |
| --- | ---: | --- |
| `conversation` | 1 | 两轮对话都属于会话 A |
| `message` | 4 | 两条 user message 和两条成功的 assistant message |
| `model_call` | 3 | 第一轮成功一次，第二轮超时一次、重试成功一次 |

## 6. 当前边界

- 已在 `app/database.py` 中实现 SQLite 连接、按连接开启外键以及 `conversation` / `message` / `model_call` 三表结构。
- 已验证同一条 user message 可关联多次调用，失败调用允许没有 response message。
- 已验证普通无效外键和跨会话 request message 引用会被拒绝；同样的组合外键也应用于 response message。
- 跨会话隔离由 `(conversation_id, message_id)` 父键唯一组合和 `model_call` 组合外键保证。
- 已实现消息历史组合索引 `(conversation_id, created_at, message_id)`，并验证查询只返回目标会话且按 `created_at`、`message_id` 稳定排序。
- 已将最近消息窗口抽取为 `load_recent_messages(connection, conversation_id, limit)`，先倒序取得最近 N 条，再恢复为 `created_at`、`message_id` 正序，并返回模型上下文需要的 `role` / `content`。
- 已使用 pytest 临时文件验证提交后的会话消息可在重新连接后恢复，未提交写入会在连接关闭时回滚。
- 尚未引入 ORM、数据访问层或 CRUD。
- 不保存 API Key、Authorization Header、完整模型请求、完整原始响应或其他敏感内容。
