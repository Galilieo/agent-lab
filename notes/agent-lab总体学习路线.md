# agent-lab 总体学习路线

> 文档角色：这是个人整体学习路线（技术栈主线）中 Python / FastAPI / Agent 部分的详细子路线，不是另一条并行总路线。
>
> 维护位置：本文件是 agent-lab 项目路线的唯一正式版本，与代码和测试一起更新。
>
> 最近核验：2026-10-20。

> 阶段 7 记忆完整设计基线：[`Memory V1.1：轻量分层长期记忆方案`](./Memory-V1.1轻量分层长期记忆方案.md)。本路线仍是进度和下一步的唯一正式版本，方案确定不代表功能完成。

## 1. 项目定位

`agent-lab` 是最小 AI 机制实验室，负责把下面的技术真正学懂、写出、测过并能讲清：

```text
Python 工程
→ FastAPI
→ LLM 调用
→ SQLite 多轮对话
→ 原生 Agent
→ 记忆与 RAG
→ LangChain
→ LangGraph
→ SSE、评测与工程化
```

已经理解并验证成熟的能力，后续再迁移到心屿（Xinyu，GitHub 仓库 `heart-island`；当前本地目录 `heart_island`）。

学习原则：

1. 每次只学习一个小主题。
2. 先讲项目链路，再读源码，最后补概念。
3. 先写原生最小闭环，再学习框架封装。
4. 每一阶段必须有正常和失败验证。
5. 优先形成能手写、能面试、能结合项目解释的能力。
6. 测试服务于学习主线：练手阶段优先保护核心路径和关键回归，不按正式生产项目的穷举密度扩张。
7. 同一请求链上的 2～4 个强相关点默认合并为一个可解释、可手写、可验证的小闭环，不以增加对话轮数制造“循序渐进”。
8. 提升推进速度不能跳过真实源码核验、行为预测、正确 RED、目标测试、全量回归和用户复述；完成标准看掌握质量，不看轮次数量。

## 2. 当前进度

| 阶段 | 状态 | 完成标志 |
| --- | --- | --- |
| 1. Python 必要基础 | **已完成第一轮** | JSON、推导式、uv、异步、pytest 已做基础练习 |
| 2. 读懂现有 agent-lab | **已完成第一轮** | 能解释核心文件和当前请求链 |
| 3. FastAPI 请求链 | **已完成第一轮** | 完成请求、校验、响应、异常和测试 |
| 4. 真实 LLM 调用 | **已完成第一轮** | 异步单轮调用、错误边界、安全日志和 Token usage 已验证 |
| 5. SQLite 与多轮对话 | **已完成第一轮** | 会话可持久化、恢复和隔离 |
| 6. 原生 Tool Calling 与 Agent 循环 | **已完成第一轮** | 三工具、原生循环和失败边界已验证；完成 Pydantic 参数校验、MCP 接线与 Tool / Resource / Prompt 职责复述 |
| 7. 轻量记忆与原生最小 RAG | **进行中：存储回归通过，轻量分层记忆方案已确定** | 会话归属已收口；两种范围记忆存储已实现并通过回归；采用显式保存与按需 LLM 提取、核心记忆默认注入与其他记忆分类选择，后续请求链接入尚未实现 |
| 8. LangChain | 待开始 | 用框架重构已完成的调用、工具和 RAG |
| 9. LangGraph | 待开始 | 完成有状态、分支、循环和人工确认 |
| 10. SSE、评测与工程化 | 待开始 | 可流式、可测、可追踪、可部署 |
| 11. 迁移到心屿 | 待开始 | 成熟模块进入真实业务项目 |

### 当前测试策略

`agent-lab` 当前是 FastAPI + Agent 学习项目，不以正式生产项目的完整测试矩阵为目标。后续每个小主题通常只新增一条代表性 RED，只有高风险核心边界才额外增加一条失败测试。

教学和回归优先保护：

- `/health` 正常返回。
- `/chat` 正常调用并返回，非法请求由 Pydantic 返回 `422`。
- LLM 超时、连接失败和上游失败保持现有 `504 / 503 / 502` 映射。
- `conversation → message` 外键有效。
- 聊天历史会话隔离、稳定排序和最近消息窗口正确。
- 数据 `commit()` 后可在重新连接后恢复。
- 成功和失败的 `model_call` 均能关联本轮 user message，并保留正确的结果分类和可用调用元数据。

日志精确条数、单个日志字段、缺少 usage 时的具体日志文本、所有异常响应字段组合、跨会话组合外键排列、索引字段顺序和未提交重连等细粒度测试已有部分可以继续保留作为回归保护，但不要求用户全部从零手写，也不再按同样密度新增。重复的 `FakeAsyncClient`、会话/消息插入等样板默认由 Codex 处理；明显影响阅读时再单独抽取 fixture/helper，不让测试重构挤占 Agent 主功能学习。

### 当前代码基线

已经存在：

- `app/main.py`：FastAPI 应用、`GET /health`、真实异步 `POST /chat`；通过 lifespan 在应用启动时初始化 SQLite schema，由 `/chat` 调用原生 Agent，按两个短事务保存当前 user message、最终 assistant message 和本轮调用记录；后续模型调用失败时保存此前成功调用和最终失败调用，工具处理失败时保存此前成功调用但不虚构失败模型调用，并保持 `504 / 503 / 502` 错误映射。
- `app/schemas.py`：Pydantic 请求与响应模型。
- `app/config.py`：环境变量配置对象。
- `app/database.py`：SQLite 连接入口，为每个连接开启外键，并初始化 `conversation`、`message`、`model_call`、`memory` 四表结构；组合外键保证模型调用引用的请求/回复消息属于同一会话，`load_recent_messages()` 按会话读取最近消息窗口并恢复为模型上下文正序，成功/失败调用插入函数负责保存可追踪调用记录；`upsert_memory()` 筛选匹配用户或会话范围的用户消息来源，按 `(scope, scope_id, key)` 新增或更新，零写入时抛出 `ValueError`，事务由调用方提交。
- `app/services/llm.py`：原生 `httpx.AsyncClient` 异步 LLM service，负责组装普通或 Tool Calling 请求、调用 DeepSeek OpenAI 兼容接口、解析回答与 `tool_calls`，并让超时、连接、上游状态和非法响应异常携带结构化失败元数据。
- `app/services/agent.py`：原生 Agent 编排层，当前支持直接回答或 calculator / get_current_time / search_notes 可重复工具调用，每轮通过 `AVAILABLE_TOOLS` 提供三个工具，将工具请求和结果继续回传模型；默认最多执行 3 次模型调用，用 `AgentResult` 返回最终回答和全部成功调用，用 `AgentRunError` 在后续模型失败时携带此前成功调用，用 `AgentModelCallLimitError` 表达调用预算耗尽，并用 `AgentToolError` 统一承接工具处理失败及此前成功调用。
- `app/tools.py`：calculator、get_current_time 和 search_notes 工具定义、统一工具列表、Pydantic 参数校验和本地执行边界；时间工具通过 `ZoneInfo` 返回含 UTC offset 的 ISO 8601 时间；笔记工具固定读取项目 notes 目录中的普通 Markdown 文件，按关键词逐行匹配，最多返回五条含文件路径、行号和原文的记录。未知工具、参数校验和工具执行异常沿现有工具错误边界处理。
- `app/mcp_server.py`：使用官方 MCP SDK 的 `MCPServer` 将 search_notes 注册为 MCP 工具，复用已有参数模型和查询函数，返回 JSON 文本；另注册 `notes://learning-route` Resource，读取固定学习路线文件并返回 Markdown 文本。作为模块运行时提供 stdio 服务。
- `app/services/mcp_tools.py`：为 Agent 的 search_notes 分支提供异步 MCP Client 调用，校验模型参数后按 stdio 配置连接 Server，将文本内容块转换成工具消息字符串，并将工具错误标记或缺少文本转换成异常；calculator / get_current_time 继续由 Agent 调用本地执行函数。
- `tests/test_database.py`：使用内存 SQLite 和 pytest 临时文件验证连接外键、三表写入、模型调用重试、失败调用无回复、无效外键、跨会话消息引用拒绝、消息历史稳定排序与最近消息窗口，以及提交和未提交数据在重新连接后的差异。
- `tests/test_health.py`：TestClient 请求校验、应用启动 schema 初始化、业务异常、LLM 正常返回、Tool Calling 响应解析、超时、连接失败、上游状态错误和非法 JSON 映射测试；通过进入 TestClient 上下文触发 lifespan，并使用真实临时 SQLite 验证成功 Agent 调用链、直接失败、中途成功后最终 timeout，以及调用预算耗尽时的调用记录持久化。
- `tests/test_agent.py`：使用 fake HTTP client 验证 calculator 和 get_current_time 工具请求、工具结果消息、第二次模型请求、最终回答和完整成功调用列表；时间工具真实执行，代表性测试检查两轮工具注册、调用 ID 关联、上海 UTC offset 和返回时间位于执行前后之间。
- `tests/test_tools.py`：验证 calculator 参数校验、本地执行和除零边界；笔记工具使用临时文件验证匹配原文及出处、忽略非 Markdown 文件，以及未命中时返回空列表。
- `tests/test_mcp.py`：使用同进程 MCP Client 和真实临时笔记验证工具发现、必填参数声明、成功状态与 JSON 文本结果。
- `tests/test_agent_mcp.py`：使用 fake 模型、真实临时笔记与同进程 MCP Server 验证 Agent 经 MCP 查询、调用参数、工具请求与结果 ID 关联、结果回传和最终回答；测试将 stdio 启动配置替换为同进程连接，不启动子进程。
- `pyproject.toml`：Python、运行依赖、开发依赖和 pytest 配置；`httpx` 和 `mcp>=2.3,<3.0` 是运行依赖，当前锁定 MCP SDK 2.3.0。
- `playground/`：JSON、推导式、异步和 pytest 的第一轮练习，以及独立 stdio Client `mcp_note_client.py`。

2026-07-26 实际验证：

```text
uv 0.11.32
Python 3.12.13
pytest 8.4.2
2 passed
```

2026-08-05 学习验收：

- 已按顺序完成五个核心文件的第一轮源码走读和检查题验收。
- 已能解释 Uvicorn、FastAPI、Pydantic、TestClient、配置对象和路由函数的职责边界。
- 已用真实 Uvicorn + curl 验证正常 `POST /chat` 返回 `200`，空消息在路由匹配后因 Pydantic 校验失败返回 `422`。
- 当前 `/chat` 仍返回固定占位结果，没有调用真实模型。

2026-08-07 学习验收：

- 已为 `POST /chat` 保留正常输入测试，并补齐空字符串、缺失字段和错误类型测试。
- 已能通过 `422`、`detail[].loc` 和 `detail[].type` 判断失败字段与校验类型。
- 已在模拟 `POST /chat` 中用 `HTTPException` 实现关闭会话返回 `409`，并补充对应测试。
- 已能区分 FastAPI 可转换为 HTTP Response 的业务异常与 TestClient 默认重新抛出的未处理程序错误。
- 已将 `POST /chat` 改为 `async def`，理解协程、事件循环、`await` 与 I/O 并发的基本边界。
- 已验证同步 TestClient 无需因服务端异步路由而改变写法，`200`、`409`、`422` 响应契约保持不变。
- 已通过四层综合验收，能判断失败发生在路由、Pydantic 校验、业务处理还是 pytest 断言层。
- 已能解释 `developer`、`user`、`assistant` 消息角色，以及 `ChatRequest.message` 到模型请求和模型响应到 `ChatResponse.answer` 的映射。
- 已能区分 API Key、Base URL 和模型名的职责，理解应用启动成功不等于 LLM 配置有效。
- 已建立 `app/services/llm.py`，由异步 `/chat` 路由通过 `await` 调用，路由不再直接生成占位回答。
- `uv run pytest -q` 实际验证为 `6 passed`，`git diff --check -- app/main.py tests/test_health.py` 通过。

2026-08-09 学习验收：

- 已将 `httpx` 明确为运行依赖，理解第三方安装项目时运行依赖必须随项目声明。
- 已配置 DeepSeek OpenAI 兼容服务的 Base URL、API Key 和 `deepseek-v4-flash` 模型；真实 Key 只保存在被 Git 忽略的 `.env` 中。
- 已能解释 `httpx.AsyncClient` 在请求链中的位置，并确认真正的异步网络等待发生在 `await client.post(...)`。
- 已在 LLM service 中组装 `Authorization: Bearer ...`、`Content-Type`、`model`、`messages` 和非流式请求体。
- 已完成一次真实异步单轮调用，`POST /chat` 实际返回“连接成功”。
- 已完成 DeepSeek 兼容响应的 JSON 解析，并将 `choices[0].message.content` 映射为 `ChatResponse.answer`。
- 已将 HTTPX 客户端超时显式延长为 `60.0` 秒，理解默认读取超时不能直接代表模型调用失败。
- 已用 fake HTTP client 复现 `httpx.ReadTimeout`，由 service 转换为 `LLMTimeoutError`，再由路由映射为 HTTP `504`。
- 已用 fake HTTP client 复现 `httpx.ConnectError`，由 service 转换为 `LLMConnectionError`，再由路由映射为 HTTP `503`。
- 已通过 `response.raise_for_status()` 识别上游 `4xx / 5xx`，将 `httpx.HTTPStatusError` 转换为 `LLMUpstreamError`，再由路由映射为 HTTP `502`。
- 正常路由测试仍通过 fake service 隔离真实模型调用；超时测试也不会访问 DeepSeek 或产生费用。
- `.venv\\Scripts\\python.exe -m pytest -q` 实际验证为 `10 passed`，`git diff --check` 通过。

2026-08-10 学习验收：

- 已理解 HTTP `200` 只表示状态码成功，不保证响应正文是合法 JSON 或符合模型成功响应结构。
- 已实际确认 `response.json()` 解析非法正文时抛出 `json.JSONDecodeError`，并与 `response.raise_for_status()` 抛出的 `httpx.HTTPStatusError` 区分。
- 已由 service 将 `json.JSONDecodeError` 转换为 `LLMResponseError`，再由路由映射为 HTTP `502`。
- 已确认合法 JSON 缺少 `choices` 或 `message.content` 时会在字段提取处抛出 `KeyError`，它与 `json.JSONDecodeError` 属于不同异常。
- 已将字段提取放入响应解析的 `try`，由 service 将 `json.JSONDecodeError` 和 `KeyError` 统一转换为 `LLMResponseError`，复用路由已有的 HTTP `502` 映射。
- 已用 `time.perf_counter()` 覆盖异步网络等待和响应提取过程，并在成功调用后通过 `app.services.llm` logger 记录 `model`、上游 HTTP `status` 和 `latency_ms`。
- 已用 `caplog` 验证成功调用日志存在且包含预期字段；日志不记录 API Key、Authorization Header、完整用户问题或模型回答。
- 已为 timeout、connection error、上游 HTTP 状态错误和无效响应统一记录 `WARNING` 失败日志；没有上游 Response 时记录 `status=unavailable`，有 Response 时保留真实上游状态，并使用稳定的 `error` 分类。
- 已用 `caplog` 验证四类失败日志均包含 `model`、可用 `status`、`latency_ms` 和 `error`，且原有 `504 / 503 / 502` 路由映射保持不变。
- 已根据 DeepSeek 官方 Chat Completion 响应结构确认并提取 `prompt_tokens`、`completion_tokens` 和 `total_tokens`，在成功日志中记录三项 Token usage。
- 已验证成功响应缺少 `usage` 时仍返回有效 answer，并将三项 Token 日志记录为 `unavailable`，不因可观测元数据缺失返回 `502`。
- 三个响应异常目标测试实际验证为 `3 passed`，成功日志目标测试实际验证为 `1 passed`，四类失败日志目标测试实际验证为 `4 passed`，Token usage 目标测试实际验证为 `2 passed`，全量 `.venv\\Scripts\\python.exe -m pytest -q` 实际验证为 `15 passed`，`git diff --check` 通过。
- 已通过阶段 4 综合验收，能解释完整异步请求链、`504 / 503 / 502` 错误映射、核心 answer 与可观测 usage 的边界，以及允许和禁止记录的日志内容。
- 最终安全核验确认 `.env` 被 `.gitignore` 忽略且未被 Git 跟踪，仓库只跟踪 Key 为空的 `.env.example`；阶段 4 标记为完成第一轮。

2026-08-11 学习验收：

- 已完成 `conversation`、`message` 和 `model_call` 的最小逻辑数据模型与关系草案。
- 已实现 SQLite 内存连接，并确认外键需要按连接开启。
- 已实现 `conversation` / `message` 最小表结构，验证合法消息可写入、孤儿消息被外键拒绝。
- `uv run pytest -q` 实际验证为 `18 passed`。

2026-08-13 学习验收：

- 已实现 `model_call` 最小表结构，保存会话、请求/回复消息、模型、调用结果、上游状态、耗时和 Token usage。
- 已验证同一条 user message 可以对应多次模型调用，支持失败后重试；失败调用允许 `response_message_id` 为 `NULL`。
- 已验证不存在的会话、请求消息和回复消息会触发 `sqlite3.IntegrityError`。
- 已通过 `message` 的 `(conversation_id, message_id)` 唯一组合与 `model_call` 组合外键，阻止模型调用引用其他会话中的真实消息。
- 已完成跨会话请求消息边界的 RED → GREEN；能区分普通外键保证“记录存在”和组合外键保证“同一会话关系匹配”。
- `tests/test_database.py` 实际验证为 `6 passed`，全量 `uv run pytest -q` 为 `21 passed`；`py_compile` 和 `git diff --check` 通过。

2026-08-14 学习验收：

- 已为 `message` 增加 `(conversation_id, created_at, message_id)` 组合索引。
- 已使用两个会话和同一时间的多条消息，验证历史查询只返回目标会话，并先按 `created_at`、再按 `message_id` 稳定排序。
- 已通过 `EXPLAIN QUERY PLAN` 确认 SQLite 对目标查询使用 `idx_message_history` 索引。
- 已使用 pytest 的 `tmp_path` 创建临时 SQLite 文件，验证第一个连接提交并关闭后，第二个连接仍能恢复同一会话消息。
- 已验证写入后不调用 `commit()`，关闭连接会回滚未提交事务，第二个连接查询不到该会话。
- 已使用内层 `created_at DESC, message_id DESC` 取得最近 N 条消息，再由外层按 `created_at, message_id` 恢复模型上下文的正序。
- 最近消息窗口只使用一条代表性 RED → GREEN，同时覆盖最近 N 条选取和同一创建时间下的稳定顺序。
- 已将最近消息窗口 SQL 抽取为 `load_recent_messages(connection, conversation_id, limit)`，返回后续 LLM 上下文需要的 `role` / `content` 字典列表，并由原代表性测试直接验证函数行为。
- `tests/test_database.py` 实际验证为 `11 passed`，全量 `uv run pytest -q` 为 `26 passed`；`py_compile` 和 `git diff --check` 通过。

2026-08-16 学习验收：

- 已为 `generate_reply()` 增加可选历史消息参数，并保持原有单轮调用兼容。
- 已按 `system → 历史消息 → 当前 user` 的顺序组装模型请求；历史消息通过列表解包进入 `messages`，不会形成嵌套列表。
- 已能解释 `None` 默认值与可变默认列表的区别，以及 Python 默认参数对象可能被多次调用共享的风险。
- 已改造一条现有 fake HTTP client 测试直接观察上游 `messages` payload，没有扩张测试矩阵，也没有访问真实模型。
- 目标测试实际验证为 `1 passed, 14 deselected`，全量 `uv run pytest -q` 为 `26 passed`；`git diff --check` 通过。
- 已增加 `DATABASE_PATH` 配置边界：应用缺省使用文件数据库 `agent-lab.db`，路由测试通过 autouse fixture 为每条测试注入独立的临时 SQLite 文件，并继续由 `.gitignore` 排除数据库文件。
- 已让 `POST /chat` 打开目标 SQLite、确保表结构存在、按 `conversation_id` 读取最近 10 条消息，并在关闭连接后把当前问题和历史传给 LLM service。
- 已能解释数据库查询异常时 `finally` 会关闭连接、原异常继续向外传播且后续模型调用不会执行，以及为什么外部模型等待不应占用数据库连接或事务。
- 已改造一条现有路由测试，使用真实临时 SQLite 验证会话 A/B 隔离和历史传递，只 fake 外部 LLM；目标测试为 `1 passed, 14 deselected`，全量测试为 `26 passed`，`git diff --check` 通过。
- 已为数据库层增加 `upsert_conversation()` 和 `insert_user_message()`：新会话以 `active` 状态创建，已有会话保留 `created_at` 并更新 `updated_at`，当前 user message 与会话更新由路由统一提交。
- 已将路由写入顺序固定为“创建或复用会话 → 读取旧历史 → 插入当前 user message → commit → 关闭连接 → 调用 LLM”，避免当前问题同时出现在 history 和 message 中。
- 已能解释数据库函数不自行提交的原因、同一事务的原子性，以及写入失败时 `finally` 关闭连接会回滚尚未提交的会话和消息数据。
- 已用同一条临时数据库路由测试连续请求新会话两次，验证第一次创建、第二次复用、当前 user message 在 fake LLM 调用前已提交，且第二次 history 只包含此前消息；目标测试为 `1 passed, 14 deselected`，全量测试为 `26 passed`，`git diff --check` 通过。
- 已为数据库层增加 `insert_assistant_message()`；路由只在 `generate_reply()` 成功返回后重新打开 SQLite，将 assistant message 提交并关闭连接，再返回 `ChatResponse`。
- 已保持模型调用位于两个短数据库事务之外：第一次事务保存当前 user message，模型成功后第二次事务保存 assistant message；模型失败时不会生成或保存不存在的 assistant message。
- 已用同一条两轮临时数据库测试验证第一轮 assistant message 会进入第二轮 history，第二轮当前 user message 不会重复进入 history，最终四条 user / assistant 消息顺序正确。
- 已能解释 SQLite `:memory:` 数据库与连接绑定：第一个连接中的提交不能被第二个 `:memory:` 连接读取；应用默认改用文件数据库，路由测试则用独立临时文件保证跨连接与测试隔离。
- assistant 持久化目标测试实际验证为 `1 passed, 14 deselected`，全量 `uv run pytest -q` 为 `26 passed`；`git diff --check` 通过。
- 已为 LLM service 增加内部 `LLMResult` dataclass，统一返回 `answer`、模型、上游状态、耗时和三项可选 Token usage；路由仍只将 `result.answer` 映射为原有 `ChatResponse`，没有扩大 HTTP 响应契约。
- 已将缺失 Token 在结构化结果中表示为 `None`，为 SQLite 可空整数列保留正确数据类型，同时在安全日志中继续显示 `unavailable`。
- 已复用现有成功与 usage 缺失测试完成 RED → GREEN，并让路由 fake service 返回完整 `LLMResult`；结构化结果目标测试为 `2 passed, 13 deselected`，全量 `uv run pytest -q` 为 `26 passed`。
- 已能解释 `@dataclass` 根据字段生成初始化方法等样板代码，以及普通类型标注本身不会让类接受字段构造参数。

2026-08-17 学习验收：

- 已让 user / assistant message 插入函数返回 SQLite 自动生成的 `message_id`，并用 `request_message_id` / `response_message_id` 将成功调用关联到本轮请求与回复。
- 已在第二个短事务中统一保存 assistant message 和成功 `model_call`，避免只留下其中一条的半套成功数据；模型等待继续位于两个数据库事务之外。
- 已增加 `LLMRequestError` 结构化失败边界，四类异常保留 `model`、具体 `outcome`、可用 `upstream_status` 和 `latency_ms`，同时保持原有错误文本与 `504 / 503 / 502` HTTP 映射。
- 已在 LLM 失败后保留事务一提交的 user message，不生成 assistant message，并保存 `response_message_id=NULL`、Token 字段为空的失败 `model_call`。
- 已用原有两轮路由测试验证两条成功调用及消息归属，并用 timeout 路由测试完成一条代表性失败持久化 RED → GREEN；其他三类失败复用现有测试完成回归。
- 成功与 timeout 目标测试均为 `1 passed`，`tests/test_health.py` 为 `15 passed`，全量 `uv run pytest -q` 为 `26 passed`；`py_compile` 和 `git diff --check` 通过。
- 截至这一自动化测试步骤，验证使用 TestClient、真实临时 SQLite 和 fake LLM/HTTP client，尚未重新执行真实 Uvicorn 网络请求或真实 DeepSeek 多轮调用。
- 已新增一条不调用 `/chat` 的代表性启动测试，先确认当前应用启动后临时 SQLite 中没有三张业务表，形成正确 RED。
- 已使用 FastAPI lifespan 在应用启动时打开目标 SQLite、执行 `initialize_schema()` 并关闭初始化连接，同时从 `/chat` 请求链移除 schema 初始化。
- 已将模块级 TestClient 和各失败测试中的临时客户端整理为 pytest `yield` fixtures，确保临时数据库路径先注入、lifespan 后启动，并在测试结束后退出应用生命周期。
- schema 启动目标测试为 `1 passed`，`tests/test_health.py` 为 `16 passed`，全量 `uv run pytest -q` 为 `27 passed`；`py_compile` 和 `git diff --check` 通过。
- 已使用全新的临时文件数据库、本地 fake OpenAI 兼容上游和真实 Uvicorn 进程完成两轮 HTTP 验收；`GET /health` 与两次 `POST /chat` 均返回 `200`，没有访问真实 DeepSeek 或产生费用。
- 已在 fake 上游实际观察第二轮 `messages` 为 `system → 第一轮 user → 第一轮 assistant → 第二轮 user`，确认真实 HTTP 请求链正确注入上一轮历史。
- 两轮结束后真实 SQLite 数据为 `conversation=1`、`message=4`、`model_call=2`；两条成功调用分别关联请求/回复消息 `1→2` 和 `3→4`，模型、上游状态和 Token usage 均已保存。
- 用户明确授权联网和少量费用后，已使用 `uvicorn --env-file .env` 加载本地配置但不读取或输出其内容，并通过独立临时数据库完成两次真实 DeepSeek 请求；`GET /health` 与两次 `POST /chat` 均返回 `200`。
- 第一轮合成消息要求记住测试代号“蓝鲸42”，模型回答“已记住。”；第二轮询问测试代号，模型正确回答“蓝鲸42”，实际证明当前 DeepSeek 请求链能够接收数据库恢复的上一轮历史。
- 两次真实调用均由当前配置模型 `deepseek-v4-flash` 返回，上游状态为 `200`，耗时约为 `2136.33ms / 2002.82ms`；Token usage 分别为 `106 / 11 / 117` 和 `122 / 78 / 200`，并正确保存为两条 `succeeded` 调用记录。
- 真实联调后的 SQLite 数据仍为 `conversation=1`、`message=4`、`model_call=2`，请求/回复消息分别关联为 `1→2` 和 `3→4`；临时数据库已在验证后删除。
- 阶段 5 已完成第一轮；本次真实联调证明了当前时点的外网连接、API Key、配置模型和两轮历史链路，但单次验收不代表长期模型质量、稳定性、限流或所有错误场景。

2026-08-21 阶段 6 进行中验收：

- 已为原生 LLM service 增加 `tools`、`tool_choice="auto"`、`tool_calls` 解析和当前轮追加消息边界，并保留工具参数原始 JSON 供执行层校验。
- 已实现 calculator 工具定义、Pydantic 参数模型和本地执行，覆盖合法计算、额外字段拒绝、非法运算符与除零参数边界。
- 已实现直接回答或单轮 calculator 调用的原生 Agent 编排：第一次模型决定工具，Python 校验并执行，工具结果通过 `tool_call_id` 回传，第二次模型生成最终回答。
- 已使用 `AgentResult` 区分最终业务回答与本轮全部成功 `LLMResult`，避免工具链第一次调用元数据在返回最终答案时丢失。
- 已将 `/chat` 接入 `run_agent()`；成功工具链只保存一条最终 assistant message，同时保存中间和最终两条 `model_call`，中间调用的 `response_message_id=NULL`，最终调用关联 assistant message。
- Agent 目标测试为 `1 passed`，`tests/test_health.py` 为 `17 passed`，全量为 `31 passed`；`py_compile` 和 `git diff --check` 通过。所有自动化测试均使用 fake Agent 或 fake HTTP client，没有访问真实 DeepSeek。

2026-08-26 阶段 6 暂停前验收：

- 已新增 `AgentRunError`，当后续模型调用失败时携带原始 `LLMRequestError` 和此前已经成功的 `LLMResult`，同时通过异常链保留直接失败原因。
- 已让 `/chat` 在不生成 assistant message 的前提下，用同一个 SQLite 事务保存此前成功的 `model_call` 和最终失败调用；代表性 timeout 链继续返回 HTTP `504`，成功调用和失败调用都关联本轮 user message。
- 已将单轮 Agent 改为可重复循环，每轮继续向模型提供 calculator 工具，并按顺序累积 assistant `tool_calls` 和 tool 结果消息，直到模型直接返回最终回答。
- `max_model_calls` 默认值为 3；预算耗尽时在执行本轮工具前停止，避免已经没有下一次模型调用预算时继续产生无用或有副作用的工具执行。
- 定向测试覆盖多轮工具调用、最大调用预算停止和后续模型 timeout 时保留成功调用；路由测试使用真实临时 SQLite 验证完整失败链持久化。
- Agent 与失败持久化定向测试为 `5 passed`，全量 `uv run pytest -q` 为 `35 passed`；受影响 Python 文件通过 `py_compile`，`git diff --check` 通过。
- 本次封存验证仅使用 fake Agent / fake LLM 和本地临时 SQLite，没有访问真实 DeepSeek、没有产生模型费用，也没有重新执行真实 Uvicorn 网络请求。
- 2026-08-26 起阶段 6 保持“进行中但暂停”，学习重心切换到大厂算法面试；恢复时从下面列出的剩余错误边界继续，不把暂停状态误记为阶段完成。

2026-09-04 阶段 6 恢复说明：

- 大厂算法面试准备已经结束，算法学习内容已移至独立仓库，不再占用 `agent-lab` 的开发主线。
- 阶段 6 从暂停状态恢复为“进行中”，继续完成原生 Tool Calling 与 Agent 循环的剩余错误边界，不把恢复开发误记为阶段完成。
- 恢复时重新核验当前源码和测试；全量 `uv run pytest -q` 为 `35 passed`，测试使用 fake Agent / fake LLM 和本地临时 SQLite，没有访问真实 DeepSeek。
- 恢复后的第一个小主题是最大模型调用预算耗尽时的结构化 Agent 异常、HTTP 状态映射和已完成调用持久化边界。

2026-09-08 阶段 6 进行中验收：

- 已使用 `AgentModelCallLimitError` 表达最大模型调用预算耗尽，并携带预算内已经成功的全部 `LLMResult`。
- `/chat` 将该异常映射为 HTTP `502`，只保存本轮 user message 和两条成功 `model_call`；不创建 assistant message，也不虚构失败调用。
- 代表性目标测试为 `1 passed`，全量 `uv run pytest -q` 为 `36 passed`；受影响 Python 文件通过 `py_compile`，`git diff --check` 通过。验证仅使用 fake Agent 和临时 SQLite，没有访问真实 DeepSeek。

2026-09-21 阶段 6 进行中验收：

- 已使用 `AgentToolError` 统一承接 `execute_tool()` 边界内的未知工具、非法 JSON、参数 Schema 校验和工具执行异常，并通过异常链保留原始原因，同时携带工具失败前已经成功的全部 `LLMResult`。
- `/chat` 将工具处理失败映射为 HTTP `502`，保留事务一已经提交的 user message 和此前成功的 `model_call`；不创建不存在的 assistant message，也不把工具失败伪装成失败的模型调用。
- 已将“保存已完成模型调用”的逻辑抽取为 `persist_completed_model_calls()`，由调用预算耗尽和工具失败两条边界复用；代表性未知工具测试贯穿真实 `/chat → run_agent() → execute_tool() → SQLite`，只 fake 外部模型调用。
- 代表性目标测试为 `1 passed`，全量 `uv run pytest -q` 为 `37 passed`，`git diff --check` 通过；验证没有访问真实 DeepSeek、没有产生模型费用。

2026-10-11 当前时间工具小主题验收：

- 已新增 `CurrentTimeArguments`，要求 timezone 为必填字符串并拒绝额外字段；时区名称是否存在由执行阶段的 `ZoneInfo` 检查。
- 已新增 `CURRENT_TIME_TOOL`、`AVAILABLE_TOOLS` 和 `run_current_time()`，执行 `datetime.now(ZoneInfo(arguments.timezone)).isoformat()`；当前 macOS 环境可加载所需时区数据，没有增加第三方依赖。
- 已让 `execute_tool()` 分发 calculator / get_current_time，并让 Agent 每轮提供两个工具；工具消息回传和 `AgentToolError` 边界沿用现有实现。
- 代表性测试先因 `Unknown tool: get_current_time` 形成正确 RED；手写实现和关键断言后，时间工具目标测试为 `1 passed`，Agent / 工具相关测试为 `7 passed`，全量为 `38 passed`，`git diff --check` 通过。
- 模型响应由 fake HTTP client 预设，时间工具真实执行；本次没有访问真实 DeepSeek，不把自动化验证记为真实模型选择工具的联调验收。
- 已完成预测、核心代码和关键断言手写、正确 RED → GREEN、全量回归及复述收口；用户已能说明工具请求 / 结果消息、调用 ID 关联、参数对象字段取值、额外字段拒绝和可用工具名称 / 执行结果的区别。
- 最终检查中已补充纠正测试覆盖范围：新增时间工具测试验证的是 Asia/Shanghai 的成功调用链，未新增额外字段或无效时区的失败测试；参数模型额外字段拒绝曾用本地探索代码验证，不能将其记为该代表性测试的覆盖项。用户已明确自动化测试不能证明真实模型会正确选择工具。

2026-10-14 本地 Markdown 查询工具小主题验收：

- 已新增 `SearchNotesArguments`，拒绝额外字段、去除关键词首尾空白并要求至少一个字符；已新增 `SEARCH_NOTES_TOOL` 并加入统一工具列表。
- 已使用基于 `__file__` 的固定 notes 目录、按文件名排序的 Markdown 文件遍历和从 1 开始的行号；跳过非普通文件与符号链接，按字面包含查询，最多返回五条匹配，未命中正常返回空列表。
- `execute_tool()` 使用正确参数模型执行查询，并通过 `json.dumps(..., ensure_ascii=False)` 将结构化结果转换成 Agent 工具消息所需的字符串。
- 代表性测试先因未知工具形成正确 RED；手写实现后统一修正工具名中的逗号、错误参数模型、文件循环缩进及两处三工具注册预期。目标测试为 `1 passed`，全量为 `39 passed`，`git diff --check` 通过。
- 额外使用临时文件做本地检查，验证多文件扫描、五条上限、关键词首尾空白处理和读取范围；另用 fake 模型配合真实本地查询检查两次模型调用、调用 ID 关联、工具结果回传和最终回答。上述检查未新增正式 pytest 用例，没有访问真实 DeepSeek。
- 已完成预测、核心实现与关键断言手写、正确 RED → GREEN、全量回归和复述验收；用户能说明空白关键词先去除首尾空白、再因最小长度不足被参数模型拒绝，并在纠正消息角色后准确复述：查询结果经 JSON 序列化进入 tool 消息，通过 tool_call_id 关联模型原工具请求的 id。

2026-10-14 最小 MCP Server / Client 小主题验收：

- 已安装官方 MCP Python SDK 2.3.0，新增 Server 包装函数，通过 `@mcp.tool()` 注册 search_notes，复用已有参数校验与查询逻辑。
- 已准备同进程 Client 测试，先观察工具列表为空形成正确 RED；补齐精确名称比较并修正 `listed.tools` 拼写后，手写 Server 注册函数完成 GREEN。
- MCP 目标测试为 `1 passed`，全量测试为 `40 passed`，`git diff --check` 通过。
- 已运行 `uv run --offline python playground/mcp_note_client.py`，真实启动独立 Server 子进程，通过 stdio 列出 search_notes 并查询真实笔记，程序以退出码 0 结束。Client 使用当前 Python 解释器和固定项目 cwd，读取结果前检查 `is_error`，再读取 `TextContent.text`。
- 同进程测试与 stdio 实验均未调用真实模型；`run_agent()` 尚未接入 MCP Client，现有 `/chat` 查询仍直接调用本地工具。
- 已完成独立 MCP 服务和调用链验证及复述收口；逐段复习了客户端脚本、启动配置、连接生命周期和内容块读取。用户能准确区分：`StdioServerParameters` 只准备配置，进入 `async with Client(...)` 才启动并连接 Server；`list_tools()` 列出声明，`call_tool()` 执行工具。

2026-10-15 MCP Client 与 Agent 工具执行链接线验收：

- 用户手写关键断言；修正工具名漏写的 s 后，代表性测试因 MCP 调用记录为空形成正确 RED，能区分直接本地查询成功与实际经过 MCP Client。
- 用户手写 `execute_mcp_notes()` 和 Agent 查询分支：参数解析与校验 → MCP Client 调用 → 检查错误标记 → 提取并返回文本 → 原有 tool 消息回传模型。其他工具、模型循环和错误边界沿用现有实现。
- 目标测试为 `1 passed`，全量为 `41 passed`，`git diff --check` 通过。该正式测试使用 fake 模型和真实同进程 MCP Server，没有启动 stdio 子进程，也没有访问真实模型；此前独立 stdio 实验为另一项已通过证据。
- 另以临时缺失笔记目录运行真实同进程 MCP 失败探索，确认 `is_error` 触发的异常可由原有边界包装为 `AgentToolError`，保留此前一条成功模型调用且不再请求模型。SDK 清理连接时会以 `ExceptionGroup` 包装内部异常；现有 `except Exception` 能承接。此项未新增正式 pytest 用例。
- 已完成复述收口：用户能说明 Agent 负责工具分发与 LLM 循环、Client 封装负责 MCP 调用、Server 包装函数调用真实笔记工具，以及异常抛出后不会继续追加工具结果消息；补充明确实际查询执行位于 Server 端。

2026-10-16 MCP 职责复习与阶段 6 第一轮验收：

- 用户已区分 Tool 的参数化操作、Resource 的资源读取接口和 Prompt 的提示词模板；能说明获取 Prompt 后仍需要应用调用模型，模板本身不构成输出正确性保证。
- 用户补写 `notes://learning-route` Resource。复述中纠正了 URI 与文件路径混淆：URI 是 Client 请求使用的资源标识，实际文件由处理函数中的 `route_file` 决定；读取结果是否成为模型上下文，由应用如何组装消息决定。
- 对真实 Server 运行 stdio 资源发现与读取探索，验证列出的 URI、Markdown 内容类型，以及返回文本与正式学习路线文件一致。此项未新增正式 pytest 用例，未调用真实模型；Resource 当前未自动注入 Agent 上下文，MCP Prompt 未新增实现。
- 重新运行全量测试为 `41 passed`，`git diff --check` 通过。阶段 6 的工具实现、核心参数与失败边界、原生循环、MCP 接线、概念职责与复述均完成第一轮验收；真实模型的工具选择与完整 MCP 联调不在本次自动化证据范围内。

2026-10-16 阶段 7 轻量记忆契约讨论：

- 已结合真实最近 10 条消息窗口解释数据库持久化与模型请求上下文的区别；用户理解记忆需要读取后注入 Agent / 模型请求，用户改口时应更新内容、更新时间和来源消息。
- 用户明确希望同时支持会话隔离与同一用户跨会话复用，已正确预测同 key 会话级偏好覆盖用户级默认值，以及不同用户不能共享记忆。
- 已采用可选 user_id 契约：不传时为匿名会话，传入时固定用户归属；后续归属必须一致，包括是否匿名；匿名会话不自动认领。归属冲突返回 409，必须先于读取历史、保存本轮消息和调用 Agent；兼容旧请求及旧会话表数据。当前尚未实现身份认证。
- 已准备会话归属测试样板，从不含 user_id 的旧会话表启动，覆盖同归属继续聊天、不同用户、省略用户、认领匿名会话三类冲突，以及原会话保留。仅确认三个参数化场景可被 pytest 收集，关键断言待用户手写，尚未确认正确 RED。
- 本阶段尚未新增记忆表、请求字段、提取或注入实现；正式测试基线仍为阶段 6 验证过的 `41 passed`。

2026-10-19 会话归属正确 RED：

- 用户已手写完整关键断言，三个参数化场景均因冲突请求实际返回 200、预期为 409 形成正确 RED（`3 failed`）；没有 collection error，也没有调用真实模型。
- 已用临时内存 SQLite 探索带归属条件的 UPSERT：同归属（包括双方均为 NULL）写入计数为 1，三类归属冲突计数为 0，原归属与更新时间均保持不变。此探索未修改业务源码或新增正式测试。
- 本次 RED 检查后，由用户手写可选请求字段、会话表补列与迁移、归属条件 UPSERT、自定义异常及路由 409 映射；后续 GREEN 结果见下条记录。

2026-10-19 会话归属 GREEN 与回归：

- 用户手写实现经真实 diff 检查，目标测试为 `3 passed`，全量为 `44 passed`，`git diff --check` 通过；测试使用 fake Agent 和临时数据库，没有访问真实模型。
- ChatRequest 接收可选 user_id；新会话保存归属，归属条件 UPSERT 只允许一致归属更新时间（包括匿名双方均为 NULL），不匹配时按零写入行数抛出 ConversationOwnershipError。
- 路由在读取历史、保存本轮消息和调用 Agent 前执行归属检查，将冲突映射为 409。正式测试确认不同用户、省略已绑定用户和认领匿名会话均被拒绝；原归属不变，冲突不新增消息，也不触发 Agent。
- 初始化通过检查列名为旧 conversation 表补列，正式测试验证旧会话归属为 NULL 且创建时间保留；另以临时内存数据库探索重复初始化与旧会话省略用户继续聊天，均通过。探索未新增正式测试。
- 已完成复述收口：用户能说明 IS 对匿名归属的处理和旧建表语句不会修改已有表；补充澄清 WHERE 只限制冲突后的 UPDATE，条件不成立时 SQL 合法地跳过更新，由 Python 根据 rowcount 为 0 主动抛出异常，再由路由映射为 409。本小主题实现、回归和复述均通过；记忆表、提取、选择与注入尚未实现，不将阶段 7 标记完成。

2026-10-19 两种范围记忆的存储契约与测试准备：

- 已明确 memory 使用 scope（user / conversation）、scope_id（对应用户或会话标识）、key、value、source_message_id、updated_at 及记录 ID；唯一组合为 (scope, scope_id, key)。同组合写入更新内容、来源与时间，不影响其他范围、归属或 key。
- 来源必须为对应范围内的用户消息：用户级来源可以出自该用户的不同会话，会话级来源必须属于指定会话。已澄清“将 B 消息写成 A 的会话级记忆应拒绝”与“将 B 消息存为用户级记忆后可供 A 使用”是不同操作；后续读取仍按会话级同 key 优先的规则。
- 已准备 tests/test_memory.py：一条正常场景验证三个风格记录与另一 key 的语言记录共存、指定记录更新；一条参数化失败场景保护跨用户、跨会话及助手消息来源，失败必须抛出 ValueError 且不覆盖原记录。共四个场景仅确认可被收集，关键断言待用户手写，尚未确认对应 RED。
- 当前仍只有测试样板，尚未新增 memory 表或 upsert_memory 实现；全量通过基线保持为 `44 passed`。

2026-10-19 记忆存储正确 RED：

- 用户已补齐完整结果比较、pytest.raises(ValueError) 和失败前后记录相同的关键断言；已逐段复习 fixture、消息 ID 映射、参数化场景、异常检查与两次更新时间常量。
- 目标测试为 `4 failed`，均因 app.database 尚无 upsert_memory 函数而在执行阶段报 AttributeError；不是 collection error，未访问真实模型，确认新能力缺失的正确 RED。
- 已用临时内存 SQLite 验证命名参数的 INSERT SELECT UPSERT：来源过滤支持两种范围、同用户跨会话来源，以及零写入拒绝错误来源并保留原记录。此探索未修改业务源码。
- 下一步用户手写 memory 表与 upsert_memory：按唯一组合更新，在写入前筛选匹配范围的用户消息，零写入时抛出 ValueError。当前不增加 created_at，FIRST / SECOND_UPDATED_AT 是同一更新时间字段在不同操作时的测试值。

2026-10-20 记忆存储 GREEN 与回归、下一步校准：

- 已核验用户现有手写实现：新增 memory 表与 upsert_memory()，来源先经 INSERT SELECT 的用户角色与范围过滤，再按 (scope, scope_id, key) 新增或更新内容、来源和更新时间；零写入由 Python 抛出 ValueError，函数不自行 commit。
- 目标 `UV_CACHE_DIR=/private/tmp/agent-lab-uv-cache uv run --offline pytest -q tests/test_memory.py` 为 `4 passed`；全量 `UV_CACHE_DIR=/private/tmp/agent-lab-uv-cache uv run --offline pytest -q` 为 `48 passed`；`git diff --check` 通过。
- 正常测试验证不同范围、归属和 key 的四条记录共存，以及同一用户跨会话来源更新；三个失败场景验证跨用户、跨会话与助手消息来源被拒绝且原记忆不变。测试使用本地 SQLite 和 fake Agent / HTTP client，没有访问真实模型。
- 本小主题实现与回归已通过。用户指出存储检查题此前已经问过，不再以重复复述作为当前推进条件；本次不虚构新的复述验收记录。当前 /chat 尚未调用记忆写入函数，也未读取或注入记忆，阶段 7 仍未完成。
- 用户明确纠正下一步：先想清楚采用什么记忆方案，再决定后续实现。存储契约已明确不代表完整记忆方案已确定；此前提出的“直接实现读取、合并与注入”尚未成为已确认的实现安排。

2026-10-20 轻量分层记忆方案确定：

- 用户确定保留现有 SQLite memory 表及 user / conversation 两种范围，采用“显式保存 + 按需 LLM 结构化提取”；不默认每轮额外调用模型提取，避免无必要的延迟、Token 成本和临时信息持久化。
- 明确记忆请求及时处理；普通对话成功后仅在满足触发条件时提取。少量高价值 key 作为核心记忆默认注入，其他记忆先按 key 分类选择；同 key 会话级优先，用户改口时更新。
- 支持显式删除、用户检查记忆，并防止删除后自动重建；记忆处理失败不影响正常回答，保留不含敏感正文的错误记录。操作失败时不能声称保存或删除成功。
- “核心 / 其他”是记忆选择与注入策略的分层，与 user / conversation 的作用范围是两个维度；当前不据此增加 scope 或重建存储表。FTS5 仅在分类选择不足时评估，不作为第一版必需依赖，也不引入向量记忆框架。
- 当前已确定总体方案，尚需在实现对应小主题时明确触发条件、固定 key、候选结构、写入时序及删除防重建机制；这些细节尚未编码或验证。存储测试基线仍以本日实际执行的目标 4 passed、全量 48 passed 为准。

当前仍未完成：

- 当前只支持同一 user message 关联多条 `model_call` 并记录每次尝试，尚未执行自动重试；重试策略、退避、最大次数和可重试错误选择归阶段 10“评测与工程化”。
- 当前最近 10 条消息窗口已经形成阶段 5 的最小上下文裁剪闭环；历史摘要会引入额外模型调用、摘要持久化和质量评测，暂不作为阶段 5 阻塞项，待阶段 7 记忆或阶段 10 评测出现真实需求后再实现。
- 记忆与 RAG。
- LangChain / LangGraph。
- SSE 与评测。

## 3. 阶段 1：Python 必要基础

### 当前状态

已完成第一轮，不继续机械刷语法。

已经覆盖：

- 基础类型、容器、流程控制和函数。
- 类型标注、`None`、异常、模块和类。
- 文件读写与 JSON。
- 列表 / 字典推导式。
- `uv`、`.venv`、`pyproject.toml` 基本概念。
- `async` / `await` 基本概念。
- pytest 基本概念。

“完成第一轮”只表示知道基本概念并做过练习，不表示能脱离项目熟练运用。后续遇到这些知识时，直接在真实源码中巩固。

## 4. 阶段 2：读懂现有 agent-lab（已完成第一轮）

按顺序学习：

1. `app/main.py`
2. `app/schemas.py`
3. `app/config.py`
4. `tests/test_health.py`
5. `pyproject.toml`

重点问题：

- FastAPI 应用怎样创建？
- 装饰器怎样把 URL 和函数联系起来？
- 请求体怎样进入 `ChatRequest`？
- Pydantic 在什么时候校验？
- `ChatResponse` 怎样变成 JSON？
- TestClient 怎样发送模拟 HTTP 请求？
- `.env`、`os.getenv` 和 `settings` 怎样连接？

完成标准：

- 能逐行解释五个核心文件。
- 能画出 `POST /chat` 请求链。
- 能故意传空消息，解释为什么得到 `422`。
- 能说明当前 `/chat` 为什么没有调用模型。

## 5. 阶段 3：FastAPI 请求链（已完成第一轮）

按小主题推进：

1. 路由和 HTTP 方法。
2. 请求体与 Pydantic 校验。
3. 响应模型。
4. 状态码和异常。
5. 配置与环境变量。
6. 同步和异步接口。
7. TestClient 与错误输入测试。

项目成果：

- 保留 `GET /health`。
- 完善模拟 `POST /chat`。
- 为正常输入、空字符串、缺失字段和错误类型补测试。

完成标准：

- 能写一个最小路由、模型和测试。
- 发生失败时能区分路由、校验、业务和测试四层。

## 6. 阶段 4：真实 LLM 调用（已完成第一轮）

学习：

- OpenAI 兼容接口。
- `messages` 和角色。
- API Key、Base URL、模型名和 `.env`。
- 异步 HTTP / SDK 调用。
- 超时、连接失败、上游错误和返回结构异常。
- 模型、耗时、Token、状态和错误日志。

目标链路：

```text
POST /chat
→ ChatRequest
→ LLM service
→ 模型 API
→ 标准化结果 / 错误
→ ChatResponse
```

完成标准：

- Key 不进入源码和 Git。
- 正常、超时和上游失败都有测试或可复现验证。
- 路由不直接堆满模型调用细节。

## 7. 阶段 5：SQLite 与多轮对话（已完成第一轮）

学习：

- `conversation`、`message`、`model_call` 表。
- 主键、外键、索引和事务基础。
- 根据 `conversation_id` 读取历史。
- 上下文裁剪和最近消息窗口；理解历史摘要的收益与额外调用、持久化和评测成本。
- 数据访问层与 API 层边界。

本阶段只要求数据模型支持同一 user message 关联多次调用并完整记录每次尝试，不实现自动重试策略；自动重试归阶段 10。最近消息窗口作为当前最小上下文裁剪方案，历史摘要不阻塞阶段 5 完成，后续根据记忆和评测结果决定是否实现。

完成标准：

- 重启后能继续已有会话。
- 不同会话不会串线。
- 用户消息、模型回复和调用日志可以追踪。
- 能解释为什么外部模型调用不应长期占用数据库事务。

## 8. 阶段 6：原生 Tool Calling 与 Agent 循环

先实现三个简单工具：

- 计算器。
- 当前时间。
- 查询本地 Markdown 笔记。

目标链路：

```text
用户问题
→ 模型决定是否调用工具
→ 校验工具名和参数
→ Python 执行工具
→ 工具结果回传模型
→ 模型生成最终回答
```

必须处理：

- 未知工具。
- 参数错误。
- 工具执行失败。
- 最大循环次数。
- 直接回答。

### 小补充：Structured Output / Pydantic 结构化输出

放在工具参数校验和结构化信息提取中学习，不单独扩成一个大阶段：

- 区分合法 JSON 与符合业务 Schema 的结构化数据。
- 使用 Pydantic 定义字段、类型、枚举和必填约束。
- 处理字段缺失、类型错误和结构化输出失败。
- 在 Tool Calling 和后续轻量记忆提取中复用同一套结构校验思路。

### 小补充：MCP

在原生 Tool Calling 和 Agent 循环完成后学习，避免用协议封装掩盖核心执行链：

- 理解 MCP Client、Server、Tool、Resource 和 Prompt 的职责。
- 将一个本地 Markdown 查询能力暴露为最小 MCP 工具，或接入一个本地 MCP Server。
- 能说明 Tool Calling 负责模型选择工具，Agent 循环负责执行与回传，MCP 负责标准化工具和资源的接入边界。
- MCP 不替代 Agent 循环，也不作为进入 LangChain / LangGraph 前的新大阶段。

完成标准：

- 不用 LangChain / LangGraph，也能写出并解释最小 Agent 循环。
- 能用 Pydantic 校验一种工具参数或结构化输出，并解释 JSON 合法与 Schema 合法的区别。
- 能解释 MCP 与 Tool Calling、Agent 循环的关系，并完成一个最小本地 MCP 工具接入。

## 9. 阶段 7：轻量记忆与原生最小 RAG

### 轻量记忆

第一版采用已确定的轻量分层方案，继续使用现有 SQLite memory 表：

完整契约与边界见 [`Memory V1.1 方案`](./Memory-V1.1轻量分层长期记忆方案.md)，后续教学与实现须连同本路线读取。

- 显式保存与按需 LLM 结构化提取结合；明确记忆请求及时处理，普通对话成功后按需提取，不默认每轮调用提取模型。
- 保存记忆来源和更新时间，保持 user / conversation 两级范围与同 key 会话级优先。
- 少量高价值 key 默认注入；其他记忆先按 key 分类选择，并限制注入条数和长度。FTS5 仅作为有实际需要时的后续选项。
- 支持用户检查、修正和显式删除，避免删除后从旧消息自动重建；记忆处理失败不影响正常回答，并保留错误记录。

Memory V1.1 优先级：提取器、触发规则、核心/普通选择与注入为 P0；显式删除与防重建为 P1。FTS5 全文检索、Embedding 语义检索及可靠后台执行均为后续选项，不混作已实现能力。

当前只完成存储层验证；提取、选择、注入、检查及删除的请求链接入仍待实现，不把方案确定记为功能完成。

### 原生最小 RAG

- 读取本地 Markdown。
- 切分文档。
- 生成 Embedding。
- 检索 TopK。
- 注入上下文。
- 返回来源。
- 无结果时明确兜底。

完成标准：

- 能区分会话历史、长期记忆和检索文档。
- 引用能追溯到真实片段。
- 固定问题可以比较检索前后结果。

## 10. 阶段 8：LangChain

LangChain 不作为入门起点，而用于重构已经完成的原生能力。

学习：

- Chat model 与消息抽象。
- Prompt template。
- Runnable / 链式组合。
- Tool。
- Retriever 与 RAG 链。
- 回调、日志和流式接口。

项目成果：

- 用 LangChain 重写一次模型调用。
- 用 LangChain 重写工具调用。
- 用 LangChain 重写原生最小 RAG。
- 保留相同测试集，对比原生版和框架版。

完成标准：

- 能说明框架封装了什么。
- 能说明哪些地方更方便、哪些地方更难排错。
- 没有实现前，不写入简历成果。

## 11. 阶段 9：LangGraph

学习：

- State。
- Node。
- Edge 和条件分支。
- 循环与停止条件。
- Checkpoint / 持久化。
- human-in-the-loop。
- 失败恢复。

项目成果：

```text
接收请求
→ 判断直接回答或调用工具
→ 工具节点
→ 失败重试 / 人工确认
→ 最终回答
```

完成标准：

- 能画出状态图。
- 能解释每个节点读写的状态。
- 分支、循环和最大次数有测试。
- 高风险动作可暂停确认。

## 12. 阶段 10：SSE、评测与工程化

依次完成：

1. SSE 流式输出。
2. 用户中断和断开检测。
3. 固定评测问题集。
4. 正确性、引用、延迟和失败率记录。
5. 重试、限流、日志追踪和内容安全。
6. Docker 与部署。

完成标准：

- 流式输出不是前端假打字机。
- 改 Prompt、模型、框架或检索参数前后有可比较结果。
- 失败可以从日志还原。

## 13. 阶段 11：迁移到心屿

迁移原则：

```text
agent-lab 中先理解
→ 写出最小实现
→ 正常 / 错误测试
→ 自己复述
→ 再设计 Java 侧迁移
```

建议迁移顺序：

1. 模型调用日志。
2. 非流式多轮对话。
3. 业务数据上下文。
4. SSE。
5. 小型 RAG。
6. 查询型 Tool Calling。

## 14. 当前下一步

已确认方案为 [`Memory V1.1：轻量分层长期记忆方案`](./Memory-V1.1轻量分层长期记忆方案.md)。新会话先完整读取本路线、导师提示词和该方案，再核验真实源码与 Git 状态，不重新猜测已确认选型。

阶段 5、阶段 6 均已完成第一轮。阶段 7 前置的可选 user_id、会话归属检查与旧库兼容已完成验证、复述和提交。两种范围记忆存储已完成正确 RED → 用户手写 GREEN → 回归：目标 `4 passed`，最近实际验证的全量基线为 `48 passed`（2026-10-20）。用户已指出此前存储检查题重复，不再重问。现已确定轻量分层记忆方案，后续请求链接入尚未实现，阶段 7 仍在进行中。提交与推送仍按用户明确指令执行。

```text
当前小主题：明确显式保存与按需提取的触发、候选结构和校验契约
```

已确认且继续沿用：支持会话级与用户级记忆，不同用户隔离，同 key 会话级优先；存储按 (scope, scope_id, key) 新增或更新，来源必须为匹配范围的用户消息。无需重新讨论已确认的这些契约。

已确定的实现方向：保留 SQLite，显式保存 + 按需 LLM 结构化提取；明确记忆请求及时处理，普通聊天成功后按需提取；核心记忆默认注入，其他记忆按 key 分类选择；支持检查、修正、显式删除与删除后防重建；记忆处理失败不影响正常回答并保留错误记录。不再重新比较已选定的总体方案，也不默认每轮额外调用模型提取。

下一步结合真实请求链集中明确一个可编码、可验证的局部契约：

1. 哪些明确请求进入保存、修改或删除流程，哪些普通对话值得提取，哪些临时要求应跳过；明确记忆请求的具体处理时序。
2. 候选动作、固定 key、scope 和 value 的结构及无候选表示，Pydantic 与业务规则各自负责哪些校验；归属标识和真实来源由代码绑定。
3. 正常结果、无候选、无效候选与提取失败的函数返回或异常边界，为一组紧密相关的 RED → GREEN 准备清楚预期。

本小主题契约明确后，准备代表性 RED，由用户手写核心实现与关键断言，Codex 负责重复样板、命令执行与路线同步。后续再依次接通提取与写入、分层选择与注入、检查与删除及端到端验证；删除防重建机制须在删除功能落地前明确。FTS5 仅在出现实际检索需求时评估，当前不扩展到 Embedding、向量库、LangChain、LangGraph 或 SSE。
