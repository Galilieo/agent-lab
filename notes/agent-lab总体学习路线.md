# agent-lab 总体学习路线

> 文档角色：这是个人整体学习路线（技术栈主线）中 Python / FastAPI / Agent 部分的详细子路线，不是另一条并行总路线。
>
> 维护位置：本文件是 agent-lab 项目路线的唯一正式版本，与代码和测试一起更新。
>
> 最近核验：2026-10-28；记忆读取/合并目标 2 passed，全量离线 67 passed，git diff --check 通过。聊天写入接线与读取合并均已验证；Core/Regular 选择、预算和 Prompt 注入尚未实现。

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

已经理解并验证成熟的能力，后续接入心屿（Xinyu，GitHub 仓库 `heart-island`），保留 Python AI 服务，与现有 Java 业务后端协作，不将 Agent 默认重写为 Java。

学习原则：

1. 每次只学习一个小主题。
2. 先讲清目标、设计理由与项目请求链，阅读真实源码并补足概念；可以提供完整局部参考，不强制先独立实现才讲答案。
3. 先写原生最小闭环，再学习框架封装。
4. 每一阶段必须有正常和失败验证。
5. 当前以理解设计、读懂实现、判断与验证行为为主；亲手输入或局部修改服务于理解，不要求每个主题从零独立实现。
6. 测试服务于学习主线：练手阶段优先保护核心路径和关键回归，不按正式生产项目的穷举密度扩张。
7. 同一请求链上的 2～4 个强相关点默认合并为一个可解释设计、读懂实现、可验证的小闭环，不以增加对话轮数制造“循序渐进”。
8. 提升推进速度不能跳过真实源码核验、行为预测、正确 RED、目标测试、全量回归和用户复述；完成标准看能否解释设计、理解关键代码和判断验证结果，不看轮次或抄写量。

### 当前教学方式（2026-10-26 最新调整）

- 用户最新明确恢复以设计理解为主的带读方式，取代同日稍早“每主题一个核心任务先独立尝试、逐渐减少参考”的强制安排；历史记录保留，后续执行以本节和导师提示词为准。
- 默认解释需求、设计理由、模块职责、数据流和失败边界，结合真实源码给出连贯的局部参考，再通过行为预测、运行测试和简短复述核对理解。
- 可以提供完整局部函数、SQL 或关键断言的参考及位置，不要求先猜接口或独立写出；代码可参考输入，样板继续由 Codex 处理。直接修改核心实现仍按用户明确请求执行，不自动接管整个阶段。
- 不强制每主题闭卷复现、独立实现或变式训练；用户想练时再安排。保留新行为正确 RED → GREEN、目标与全量回归，不把重视理解等同于只听概念而不核验代码。
- 测试通过证明已测行为，参考输入不能记为独立实现；学习掌握情况按用户对设计理由、执行链、关键边界与验证结果的实际解释记录，不强制额外补齐独立设计证据。
- 每个主题围绕“解决什么问题、为什么这样设计、代码怎样执行、如何证明有效”带读；重点解释真实数据流、异常归属、事务和副作用边界。源码或概念带读不强造 RED，新增/修改行为仍遵守正确 RED → GREEN 与回归。
- 开源学习包含专门的产品体验、架构总览与设计对照专题，不局限于当前问题临时查询。先建立整体认识，再沿核心链路阅读，不机械逐文件通读或堆框架名；参考文章的功能清单不自动变为开发要求。严格区分文档阅读、源码核验、实际体验、离线测试与生产经验。
- 用户明确时间并非无限，但不赶时间、不追求速成。当前目标是能解释、检查、修改和验证项目，不以从零手写整个 Agent 或资深工程师覆盖面为阶段门槛。实践与必要原理结合推进，允许充分讲解、推敲、追问和复习；最小闭环用于控制主题范围，不压缩理解过程。减少重复抄写、重复教程和机械问答，保留核心验证与真实项目表达。

## 2. 当前进度

| 阶段 | 状态 | 完成标志 |
| --- | --- | --- |
| 1. Python 必要基础 | **已完成第一轮** | JSON、推导式、uv、异步、pytest 已做基础练习 |
| 2. 读懂现有 agent-lab | **已完成第一轮** | 能解释核心文件和当前请求链 |
| 3. FastAPI 请求链 | **已完成第一轮** | 完成请求、校验、响应、异常和测试 |
| 4. 真实 LLM 调用 | **已完成第一轮** | 异步单轮调用、错误边界、安全日志和 Token usage 已验证 |
| 5. SQLite 与多轮对话 | **已完成第一轮** | 会话可持久化、恢复和隔离 |
| 6. 原生 Tool Calling 与 Agent 循环 | **已完成第一轮** | 三工具、原生循环和失败边界已验证；完成 Pydantic 参数校验、MCP 接线与 Tool / Resource / Prompt 职责复述 |
| 7. 轻量记忆与原生最小 RAG | **进行中：记忆读取与合并已 GREEN** | 聊天写入与范围隔离读取/覆盖合并已验证；全量 67 passed；选择、预算、Prompt 注入与端到端验收尚未完成 |
| 8. LangChain | 待开始 | 用框架重构已完成的调用、工具和 RAG |
| 9. LangGraph | 待开始 | 完成有状态、分支、循环和人工确认 |
| 10. SSE、评测与工程化 | 待开始 | 可流式、可测、可追踪、可部署 |
| 11. 接入心屿 | 待开始 | 保留 Python AI 服务，与 Java 业务后端集成 |

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
- 记忆补充：app/services/memory.py 已提供触发、提取、候选绑定、批量持久化及 merge_memories；main.py 在正常聊天提交后处理记忆及反馈，database.py 提供助手内容更新和归属隔离 load_memories。读取尚未接入回答前流程；tests/test_chat_memory.py 与 tests/test_memory_reading.py 的五例已验证上述边界。

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

2026-10-21 提取结果契约与测试准备：

- 已区分轻量触发、LLM 候选、Pydantic 结构校验与业务约束；用户正确预测空 upsert 和模型夹带来源 ID 应被拒绝，并已补充解释 skip 是正常无候选结果、匿名用户级候选则属于依赖请求上下文的业务约束。
- 本轮先实现提取结果模型：app/schemas.py 中的 MemoryCandidate 和 MemoryExtractionResult。固定四个候选 key、upsert 非空列表、skip 默认空列表、字符串去空白以及候选/整体 extra=forbid 的契约见 Memory V1.1 方案 5.2；暂不接入 HTTP、数据库写入或触发规则。
- 已准备 tests/test_memory_extraction.py：正常场景检查多条候选与 skip，失败场景检查空 upsert 与模型伪造来源。仅执行 collect-only，结果为 3 tests collected；关键断言待用户补齐，尚未确认正确 RED，不计为新增通过测试。新增样板前本日实际全量验证仍为 48 passed。

2026-10-21 提取结果模型正确 RED：

- 用户已手写完整 model_dump() 结果比较、skip 动作与空列表断言，以及 pytest.raises(ValidationError)；已修正 key 拼写和内容内部空格，清理完成后的 TODO 并补充测试意图注释。
- 目标 `UV_CACHE_DIR=/private/tmp/agent-lab-uv-cache uv run --offline pytest -q tests/test_memory_extraction.py` 实际为 `3 failed`，均因 app.schemas 尚无 MemoryExtractionResult 而在执行阶段抛出 AttributeError；没有 collection error，确认新模型缺失的正确 RED，未调用真实模型。
- 下一步用户手写 MemoryCandidate 与 MemoryExtractionResult，补足字段约束、字符串去空白、额外字段拒绝及 action 与列表的关联校验；之后运行目标与全量回归。当前不能将这三个新场景计为通过或宣称已经完成提取器。

2026-10-21 源码注释与阅读入口整理：

- 按用户要求，参考 PEP 8 / PEP 257，为 app、tests、playground 共 28 个 Python 文件补充职责说明，并在关键函数、事务、异常转换、工具回传和测试证据边界处添加说明；注释约定保存于 notes/代码注释规范.md，README 增加源码阅读顺序。
- 以整理前源码快照比较，移除 docstring 后全部 Python AST 保持一致；原有 FastAPI / MCP / Pydantic 定义的 docstring 和 pyproject.toml 配置值保持不变。全量仍为 48 passed、3 failed，失败均为提取结果模型尚未实现的既有正确 RED；未新增业务实现或测试场景。
- 这次是可读性整理，不推进记忆功能完成状态；当前下一步仍为用户手写两个 Pydantic 模型，再完成目标与全量回归。

2026-10-21 提取结果模型 GREEN、回归与复述收口：

- 用户手写 MemoryCandidate、MemoryExtractionResult 与 action/list 关联校验。首次检查目标 1 failed、2 passed，发现 learning_goal 误写为 leanring_goal；用户修正后目标为 3 passed，全量为 51 passed，git diff --check 通过。
- 正常测试验证多条候选完整保留、内容去首尾空白及 skip 默认空列表；两个失败场景验证空 upsert 与模型夹带 source_message_id 被 ValidationError 拒绝。模型同时声明固定 key、scope、value 非空与整体/候选的额外字段拒绝；不将每项代码约束都声称为独立正式测试覆盖。
- 用户已理解 key 白名单限制的是 LLM 候选类别，数据库 key 仍是字符串；能说明缺少 memories 时创建独立空列表，以及 Pydantic 会包装校验器的 ValueError。曾将列表与列表元素类型混淆，已用实际输出澄清 result.memories 是 list、其中元素是 MemoryCandidate；本地实验展示漏写 return 时 model_validate 得到 None。
- 用户补充正确复述：self 是 MemoryExtractionResult 实例，合法时返回到调用处的 result；进一步明确它先交回 Pydantic，再由 model_validate 返回调用方。本小主题预测、核心代码与断言手写、正确 RED → GREEN、回归与复述均已收口。不重复存储检查题，不记为完整提取器或阶段 7 完成。
- 本次仅本地结构校验与回归，没有访问真实模型或写入真实会话数据；提取触发、LLM 调用和业务范围检查仍需后续接线。

2026-10-21 轻量触发规则预测与测试准备：

- 用户正确预测显式保存、普通提问、临时/长期混合意图、不保存要求四个场景为 True / False / True / False；明确不保存应优先于消息中的学习目标线索，混合消息中的“这次”不应误伤长期偏好。
- 已创建仅含职责说明的 app/services/memory.py，以及 tests/test_memory_trigger.py 参数化样板；函数 should_extract_memory 尚未实现，关键布尔断言待用户手写。
- 仅运行 collect-only，结果为 4 tests collected；尚未确认正确 RED，不计为四个新增通过测试。新增样板前最近全量为 51 passed。本轮先闭环纯函数门控，LLM 提取调用仍待后续接线。

2026-10-21 轻量触发规则正确 RED：

- 已检查用户手写的 `assert actual is expected`，布尔断言正确。运行 `uv run --offline pytest -q tests/test_memory_trigger.py`，结果为 4 failed，均因 memory 模块尚未定义 should_extract_memory 而抛出 AttributeError；测试已正常收集，失败来源为目标功能缺失。
- 下一步由用户手写触发函数：本条不保存要求优先，再检查显式记忆或长期信息线索；不以“这次”作为整条消息的否决条件。尚未实现 GREEN，不能将新增四例计入通过基线。

2026-10-21 轻量触发规则 GREEN 与回归：

- 用户已手写 should_extract_memory：先匹配不保存短语，再匹配显式记忆或长期信息线索；函数只做本地预筛选，不访问 LLM 或数据库。
- Codex 按代码注释规范移除已完成 TODO，补充函数契约、有限匹配边界、不否决混合意图的原因与严格布尔断言说明，未修改用户的触发逻辑。
- 目标测试为 4 passed，全量离线回归为 55 passed。纯函数实现与回归已验证，用户对优先级和预筛选职责的复述待收口；不能据此记为完整提取器或阶段 7 完成。

2026-10-21 轻量触发规则复述收口：

- 用户正确解释不保存优先，return False 后不再执行正向匹配；正确复述触发后由 LLM 生成候选，再交给 Pydantic 校验的主链。
- 用户将 skip 必须为空、upsert 必须非空误归为后续业务规则；已结合 MemoryExtractionResult.validate_action 纠正：它们是现有 Pydantic 的 action/list 关联校验。依赖真实请求上下文的业务规则包括匿名请求不能写用户级记忆、来源消息必须属于匹配的用户或会话；合法 skip 正常结束，不写数据库。
- 本小主题按主干正确、补充具体边界后收口，不重复相同检查题。最近验证基线仍为目标 4 passed、全量 55 passed；下一步明确 LLM 提取调用契约，尚未接通真实提取或写入。

2026-10-21 LLM 提取调用预测与测试准备：

- 用户已正确区分外层响应 JSON、正文字符串 answer 与解析后的模型对象。用户指出提取失败不应使正常聊天失败；已补充内部失败信号与对外聊天结果是两个边界，合法 skip 与无效提取不能混为一谈。
- 本轮采用异步 extract_memories、专用系统指令、复用 generate_reply、model_validate_json 正文校验；先保留 LLMRequestError / ValidationError，聊天层捕获与安全失败记录待后续接线，不将无效输出静默转为 skip。
- Codex 已准备 tests/test_memory_service.py 的 fake HTTP 样板，覆盖合法候选及 HTTP 200 但正文不是 JSON 的代表性失败。关键结果、出站消息与异常断言待用户手写；只运行 collect-only，2 tests collected，尚未确认本小主题的正确 RED，未修改核心实现。新增样板前最近全量为 55 passed。

2026-10-21 两类模型调用与保存反馈设计澄清：

- 用户已理解正常回答与记忆提取是两个独立任务；提取输出交给应用，第一版提取输入为本轮用户消息，不包含助手回答。规则命中仍可得到合法 skip，不能与非 JSON 正文等提取失败混淆。
- 已分开说明主聊天失败、未触发提取、合法 skip、成功写入、记忆支线失败五种结果；普通聊天先成功保存，再考虑提取。提取器报告失败，由应用调用方捕获并记录，不把已成功聊天改成失败。
- 用户确认无需第三次模型调用生成“已记住”：应用可在实际写入提交成功后追加固定确认。必须防止聊天模型提前承诺，并在聊天接线时保证最终回答与持久化历史一致；这属于后续接线约束，尚未实现。
- 详细设计已写入 Memory V1.1 方案 5.4。本轮恢复到测试关键断言，不重复已澄清的调用次数、skip 和失败检查题；tests/test_memory_service.py 仍为待补断言的样板，尚未运行行为测试或编写核心实现。

2026-10-22 LLM 提取调用关键断言与正确 RED：

- 用户已手写完整候选 model_dump 比较、专用系统指令与原始用户消息断言，以及非 JSON 正文必须抛出 ValidationError 的异常断言。Codex 检查后移除已完成 TODO，并按注释规范保留行为意图说明。
- 运行 `uv run --offline pytest -q tests/test_memory_service.py`，结果为 2 failed，均因 app.services.memory 尚未定义 extract_memories 而抛出 AttributeError。测试正常收集，正确 RED 已确认；核心实现尚未编写，最近通过的全量历史基线仍为 55 passed。
- 已结合真实 generate_reply 与 fake client 演示请求分派：替换 AsyncClient 后，业务代码的 await client.post 进入 fake.post；其 json 参数是出站 payload，observed["messages"] 记录 payload 中的消息列表，configure 返回与闭包修改的是同一个字典。它不记录预设的响应正文，也不代表发起了真实网络请求。
- 下一步用户集中手写 generate_reply 的可选系统指令参数、专用提取指令与 extract_memories 的调用和正文校验；不将本轮扩展为聊天接线或数据库写入。

2026-10-24 LLM 提取调用 GREEN 与回归：

- 用户已手写 generate_reply 的 keyword-only system_prompt 参数、请求 payload 替换、专用提取指令与异步 extract_memories；普通聊天默认指令保持原行为。提取调用只传本轮用户消息和专用指令，再通过 model_validate_json 校验正文，不吞掉网络或结构校验失败。
- 实测目标 tests/test_memory_service.py 为 2 passed，全量离线 pytest 为 57 passed。测试真实执行请求组装、响应解析和 Pydantic 校验，只有外部 HTTP client 被替换；没有访问真实模型，不将预设候选记为真实模型提取质量证据。
- Codex 仅调整 memory.py 模块职责说明、空行与注释措辞，保留用户核心实现。当前代码与回归已验证，参数兼容与测试证据边界的复述待收口；业务校验、数据库写入和聊天失败隔离仍未接通。

2026-10-24 提取调用收口与下一主题准备：

- 用户正确指出星号后的参数必须通过关键字传入；曾将默认值误解为必须使用的固定值，已结合函数签名与 payload 变量引用纠正：不传时使用默认聊天指令，显式传入时使用提取指令。已定位 fake HTTP 为测试中的 FakeAsyncClient，说明本地链路验证与真实模型提取质量的区别；补充具体误区后继续，不重复整组检查题。
- 提取调用单元按正确 RED → 用户手写 GREEN → 目标 2 passed / 全量 57 passed → 具体纠偏收口。后续继续按用户授权范围决定提交，不自行 commit 或 push。
- 下一主题聚焦候选的请求上下文绑定与匿名范围校验：scope_id 与 source_message_id 由应用提供，复用已有 upsert_memory 的来源归属检查。匿名请求混合 user / conversation 候选时，是整批拒绝还是只保留合法候选，属于尚待确认的保存行为；尚未新增业务校验实现或测试样板。

2026-10-24 匿名混合候选策略确定：

- 用户接受整批拒绝：匿名请求含 user 候选时不返回任何待写入项，不保留其中合法的 conversation 候选，不自动改变候选范围。
- 局部接口设计已记入 Memory V1.1 方案 5.5：同步纯函数 prepare_memory_writes，使用内部 MemoryWrite dataclass 表达绑定后的 scope_id 与来源 ID，模型候选 Schema 和数据库结构保持不变。本轮不执行 HTTP 或数据库写入，实际来源归属校验继续复用 upsert_memory。
- 当前下一步为集中预测用户级 / 会话级的 ID 绑定与匿名范围处理，再准备两组紧密相关的正常 / 拒绝测试样板。尚未新增核心实现或测试，不能记为业务校验 GREEN；最近全量基线仍为此前验证的 57 passed。

2026-10-24 候选绑定预测纠偏与测试样板：

- 用户预测 scope_id 按范围使用对应 ID；来源 ID 误写为 43，已按输入纠正为同一来源 42。用户随后明确匿名会话级候选可以返回待写入对象，绑定 conversation-A / 42；此前误把“匿名含 user 时整批拒绝”理解为匿名全部拒绝，已澄清。
- 已用同 key 的 user 中文默认值与 conversation 英文覆盖值解释两条记录共存；准备函数只返回两条待写入项，后续才在独立记忆事务中调用 upsert_memory 并统一提交，不能据此记为写入或读取合并已实现。
- Codex 已准备 tests/test_memory_binding.py：一个参数化正常测试覆盖有用户的混合范围与匿名会话级；一个拒绝测试覆盖匿名混合候选，不增加其他细粒度测试。只运行 collect-only，3 tests collected，关键断言待用户手写；当前尚未确认正确 RED。

本轮实施计划（沿用用户手写核心代码的执行方式）：

- 目标与契约：Memory V1.1 方案 5.5；原生 Python + dataclass + 现有 Pydantic，不新增依赖。只做候选范围检查与请求上下文绑定，不访问 LLM 或数据库。
- 文件：新增 tests/test_memory_binding.py；GREEN 阶段修改 app/services/memory.py，加入五字段内部 MemoryWrite 与同步 prepare_memory_writes。前者字段为 scope、scope_id、key、value、source_message_id；后者接口为 `prepare_memory_writes(extraction: MemoryExtractionResult, *, user_id: str | None, conversation_id: str, source_message_id: int) -> list[MemoryWrite]`。
- [x] Codex 准备候选与字面量预期数据，并验证三例可收集。
- [x] 用户手写 `[asdict(write) for write in writes]` 与 expected 的完整比较，以及 `pytest.raises(ValueError)`；Codex 检查并运行目标测试，确认因缺少 prepare_memory_writes 导致的正确 RED（3 failed）。
- [x] 用户集中实现 MemoryWrite 和绑定函数：按 scope 选择归属、绑定统一来源、匿名 user 拒绝整批、合法 skip 返回空列表；保留候选输入顺序，不改变模型候选对象。
- [x] Codex 运行目标测试和全量离线回归、git diff --check；实际验证目标 3 passed、全量 60 passed 后更新基线。
- [x] 用户复述临时对象与持久化的区别、来源绑定与数据库归属校验的边界，补充具体误区后收口。
- [x] 用户明确授权分类提交，包含本轮三份知识笔记及索引；代码与笔记已分别提交，路线和方案独立归入 docs 提交。编辑器与独立练习保留，不推送。

2026-10-24 候选绑定正确 RED：

- 已检查用户手写的 asdict 完整列表比较与 pytest.raises(ValueError)，关键断言正确。运行 `uv run --offline pytest -q tests/test_memory_binding.py`，结果为 3 failed，均因 app.services.memory 缺少 prepare_memory_writes 而抛出 AttributeError；不是 collection error，也不是候选 Schema 无效。
- Codex 已移除完成后的 TODO，保留检查归属、统一来源与整批拒绝的关键注释。下一步由用户在 app/services/memory.py 手写 MemoryWrite dataclass 与同步绑定函数，GREEN 后再运行目标与全量测试；当前不更新此前 57 passed 的通过基线。

2026-10-24 候选绑定首次 GREEN 检查：

- 用户已写 MemoryWrite 与 prepare_memory_writes。目标测试为 3 failed，均因构造 MemoryWrite 时缺少必填 value 而抛出 TypeError，尚未进入 GREEN；未将此运行更新为通过基线。
- 完整输出与真实 diff 同次定位三处核心问题：key 错取 candidate.value、遗漏 value=candidate.value、return writes 位于 for 循环内而提前结束。后两类行为尚被当前构造异常遮挡，但已从真实源码定位；用户集中修正后再运行目标及全量回归，不拆成逐行试错。
- Codex 仅整理标准库导入位置、签名参数缩进和 docstring 尾随空白，不代写上述核心修正。实际写库、事务与聊天失败隔离仍未接入。

2026-10-24 候选绑定 GREEN 与回归：

- 已核对用户修正：key=candidate.key、value=candidate.value、return writes 移至循环外。实测 tests/test_memory_binding.py 为 3 passed，全量离线 pytest 为 60 passed，git diff --check 通过；不新增额外细粒度测试。
- 已验证不同 scope 的归属选择、每条候选绑定统一来源、匿名会话级通过和匿名混合候选拒绝。函数只构造内存对象，真实来源归属仍由已有数据库函数保护，未将此验证误记为批量写入事务或聊天接线完成。
- 用户已完成关键断言和核心实现手写，正确 RED → GREEN 与回归已完成；当前等待复述临时对象/持久化、来源绑定/真实归属检查两项边界，再收口并继续后续持久化小主题。尚未提交或推送。

2026-10-24 候选绑定复述收口：

- 用户正确判断中途异常不会返回部分列表；已补充精确原因是本函数没有执行 SQL，前面只是临时内存对象，后续真实写入仍需事务保护。
- 用户曾将调用方误认为 LLM，后已明确来源 ID 是应用保存用户消息后从数据库拿到并传入。最后将返回 ID 的函数误称 upsert，已结合真实源码补正为 insert_user_message 返回 cursor.lastrowid；upsert_memory 返回 None。用户所述应用调用数据库检查归属的方向正确，具体复用已有 SQL 来源检查。
- 本单元预测、用户手写关键断言与核心代码、正确 RED → GREEN、目标 3 passed / 全量 60 passed、复述具体纠偏已完成。不重复已回答检查题；下一主题为独立记忆事务中的批量持久化与失败回滚，接口和代表性行为需结合现有数据库调用明确后再进入 RED。尚未提交或推送。

2026-10-24 分类提交前复核：

- 用户明确授权按近期 feat / docs 风格分类提交，范围包含提取调用、候选绑定，以及三份知识笔记和 notes/README.md 索引；编辑器设置与 playground/03_class.py 独立练习不纳入本轮。
- 重新验证提取与绑定目标共 5 passed，全量离线 pytest 为 60 passed，git diff --check 通过。三份笔记的 17 段 Python 示例在本项目环境中执行通过，5 个本地文件链接目标存在；未核验外部网页或所有 Markdown 标题锚点。
- 笔记保留个人原稿和待补充区，示例通过不等于学习者已经全部掌握。本轮不改变正式路线的下一主题，不将实际批量持久化或聊天接线记为完成；提交记录以 Git 历史为准，本轮没有推送授权。
- 已完成本地代码提交 `cac8c2c feat: 新增记忆提取调用与候选上下文绑定`，以及笔记提交 `839cb32 docs: 新增 Python 与 Pydantic 学习笔记`。本段路线与方案另作 docs 提交；提交前审查发现的旧进度摘要与核验日期已同步。

2026-10-24 批量记忆持久化局部契约：

- 当前 Git 核对：上一轮代码、笔记和路线已分别本地提交，工作区原有编辑器设置与独立类练习保留。最近实际全量基线仍为 60 passed，未将本轮设计记录当作新实现或新测试通过。
- 本轮契约见 Memory V1.1 方案 5.6：persist_memory_writes 接收待写入列表、数据库路径和更新时间，自行管理短连接，复用 upsert_memory；全部成功一次提交，失败回滚并报告，最后关闭连接。该函数不执行 LLM 调用、不初始化表，也不处理 HTTP 映射。
- 同一小主题集中掌握连接归属、批次提交和回滚，不拆成机械轮次。先预测跨连接可见性及中途失败恢复旧值，再准备临时文件 SQLite 的成功/失败测试样板，用户手写断言，确认正确 RED 后用户手写核心实现。本轮尚未新增测试或持久化函数。

2026-10-24 批量持久化预测与测试准备：

- 用户正确预测整批成功提交后可从另一连接读到两条记忆；第二条来源失败时回滚，第一条更新前已提交的中文旧值保留。对逐条提交的原因已具体补正：后续 rollback 无法撤销此前 commit，核心风险是部分成功，并非必然重复记录。
- Codex 已创建 tests/test_memory_persistence.py，使用 tmp_path 文件库，准备阶段初始化并提交真实消息；持久化与结果查询使用独立连接。正常测试检查两条记忆完整落库，失败测试先有已提交中文旧值、第一条更新英文、第二条使用其他用户来源，检查旧记忆与已提交消息不变。
- 只运行 collect-only，2 tests collected；用户关键断言尚未补齐，正确 RED 尚未确认，persist_memory_writes 尚未实现。新增样板前最近实际全量通过基线为 60 passed。

本轮批量持久化实施计划：

- 契约：方案 5.6。修改 app/services/memory.py，新增同步 `persist_memory_writes(writes: list[MemoryWrite], *, database_path: str, updated_at: str) -> None`；新测试为 tests/test_memory_persistence.py。复用 create_connection 与 upsert_memory，不新增 SQL、依赖或模型调用。
- [x] 用户完成正常与失败的行为预测，Codex 准备临时文件数据库和快照查询样板，确认两例可收集。
- [x] 用户写完整结果比较 `assert actual == expected`、`pytest.raises(ValueError)` 中的失败批次调用及 `assert after == before`；Codex 检查后运行目标测试确认正确 RED（2 failed，缺少 persist_memory_writes）。
- [x] 用户集中实现空批次返回、创建独立连接、逐条 upsert、整批一次提交、异常回滚并报告、finally 关闭连接，不在业务事务中初始化表。
- [x] Codex 验证目标 2 passed、全量离线 62 passed 与 git diff --check，实际通过后同步基线。
- [x] 用户复述异常回滚后重新抛出、独立事务不撤销已提交聊天记录两项边界，补充具体机制后收口。
- [x] 用户已于 2026-10-26 明确授权整理本地分类提交；推送未获授权，编辑器设置与独立练习继续保留。

2026-10-24 批量持久化正确 RED：

- 用户已写三处关键断言，已核对位置与含义正确。运行 `uv run --offline pytest -q tests/test_memory_persistence.py`，结果为 2 failed，均因 app.services.memory 尚未定义 persist_memory_writes 而抛出 AttributeError；临时数据库准备与测试收集正常。
- 用户追问逐条提交的实际后果，已结合“语言更新提交成功、学习目标保存失败”的独立例子说明：整批失败反馈与部分长期记忆已生效可能不一致。本轮按已确定的整批成功/失败契约实现统一事务，不因该解释扩展部分成功状态或重试主题。
- 已清理完成后的 TODO、测试函数间空行和尾随空白，保留提交、拒绝与回滚的关键注释。下一步用户在 app/services/memory.py 集中手写独立连接的持久化函数；尚未修改核心实现，当前仍为 RED，最近全量历史通过基线为 60 passed。

2026-10-24 批量持久化 GREEN 与剩余范围说明：

- 用户已正确手写 persist_memory_writes 的完整事务管理，Codex 仅整理导入顺序、空行与注释。实测目标 2 passed，全量离线 pytest 62 passed，git diff --check 通过；使用真实临时文件 SQLite，不访问真实模型或业务数据库。该单元待简短复述收口。
- 用户询问还剩多久、几个主题。按当前已确定范围，P0 最小记忆闭环约剩四个集中主题：聊天提取/写入接线、失败隔离及明确保存反馈；范围隔离读取与同 key 覆盖合并；Core/Regular 选择、预算与 Prompt 注入；跨会话记忆及改口更新的端到端验收。调用记录分类与安全失败记录随接线确定，不另扩成新工程化阶段。
- 以上是教学分组估计，不承诺固定小时或轮数。P1 的检查、删除与防重建另约一至两个主题；阶段 7 的原生最小 RAG 是记忆之后的另一部分，不能将 P0 记忆完成记为整个阶段 7 完成。继续每主题一组紧密相关测试，不为机械步骤拆轮次。

2026-10-24 批量持久化复述收口：

- 用户正确说明 rollback 后继续 raise 是为了让调用方知道失败原因并处理；对记忆与主聊天隔离的业务目标理解正确。已补充精确执行机制：主聊天先提交，记忆使用独立连接及短事务，因此记忆回滚不撤销已提交聊天记录。
- 用户所说“不阻塞正常聊天”按失败隔离理解；已明确本版同步按需提取仍会延长请求等待时间，当前没有后台执行。本轮相关问题不再重复要求复述。
- 本主题用户已完成关键断言与完整事务函数手写，正确 RED → GREEN、目标 2 passed / 全量 62 passed、复述纠偏均完成。代码适合整理提交，仍须用户明确授权；当前尚未提交本轮持久化变更。

2026-10-24 主聊天接线反馈选择与局部设计：

- 用户确认每次实际保存成功都追加固定确认，包括自动保存；普通失败只记录，显式保存失败如实反馈。具体接线约束已写入 Memory V1.1 方案 5.7，不再次确认已选定的回复尾部文案方案。
- 既有主聊天先提交正常回答和主 model_call，再运行记忆编排；追加反馈需回写原 assistant 消息，保持 ID 与主调用关联，不新增助手消息，不让提取失败改写主聊天成功记录。反馈回写失败回退为已保存原回答，安全记录失败。
- 本轮包含编排钩子、记忆失败隔离与安全分类日志、固定保存反馈及历史一致性；主 Agent 提示词要求不提前承诺实际保存，测试入口默认 fake 提取以保护旧测试不产生真实模型调用。不改 ChatResponse 字段、数据库 Schema 或引入后台系统。
- 当前先做最终回答/历史和调用记录归属的行为预测；尚未新增接线代码、数据库更新函数或测试样板，最近全量通过基线仍为 62 passed。

2026-10-24 主聊天接线预测与测试准备：

- 用户正确预测最终 answer 追加保存确认、应更新原助手消息；已补充数据库该消息内容也必须包含完全相同的确认。用户按真实两次模型请求预测 model_call 两条，已明确本轮表只存主 Agent 的 result.model_calls，示例为一条 succeeded；提取失败单独分类日志，不改主记录状态，不把这一选择泛化为所有应用的日志规则。
- Codex 已准备 tests/conftest.py，默认只替换路由提取引用为 skip，保护旧 HTTP 测试不会因为新记忆钩子联网；服务层直接解析测试仍保留其 fake HTTP。测试专用 fake generate_reply 的五处签名仅补 keyword-only system_prompt，未改关键断言或生产逻辑。
- tests/test_chat_memory.py 用 fake Agent 和 fake 提取器，HTTP/SQLite 真实执行；覆盖自动保存后返回与历史一致，以及参数化普通/显式提取失败的反馈差异、主记录独立和安全日志。新三例仅 collect-only 为 3 tests collected，关键断言待用户手写；运行排除新文件的旧测试，62 passed，不能将三例记为新 GREEN。

本轮主聊天接线实施计划：

- 契约：方案 5.7。生产修改范围为 app/main.py 的记忆编排/反馈帮助函数及 chat 返回前钩子，app/database.py 的 assistant 内容更新，app/services/memory.py 的“保存”触发线索，app/services/agent.py 的主聊天提示词传递；不改 HTTP 字段或数据库表结构。
- 接口：`process_memory_after_reply(request: ChatRequest, *, request_message_id: int, response_message_id: int, answer: str) -> str`；`persist_assistant_feedback(conversation_id: str, response_message_id: int, answer: str) -> None`；`update_assistant_message_content(connection, conversation_id, message_id, content) -> None`。前两者在 main.py，更新函数在 database.py。
- 教学执行补充（2026-10-26）：上述接口已确定，作为现有约束提供，不重新要求学习者猜函数名。先解释设计与真实链路，可以提供完整局部函数或 SQL 参考；不再强制先完成独立实现练习。直接修改核心实现仍须用户明确请求。
- [x] 用户确认每次实际保存成功提示，完成预测并补充具体误区；Codex 准备测试隔离与样板，确认三例可收集、旧62条回归通过。
- [x] 用户参考示例补齐接线关键断言，Codex 整理键名差异并确认正确 RED；不记为独立测试设计。
- [x] 用户参考局部实现完成消息更新 SQL、Agent 指令、保存触发、反馈事务与编排，并修复遗漏返回值；记忆异常仅在辅助流程隔离，回写失败返回已保存原回答。
- [x] Codex 检查真实 diff，验证接线目标 3 passed / 当时全量 65 passed；用户正确解释独立事务边界，连接归属按源码补充说明。后续读取单元验证全量 67 passed，不重复旧检查题。
- [x] 用户于 2026-10-28 明确授权整理本地分类提交；无推送授权，编辑器设置与独立练习保留。

2026-10-26 导师提示词调整与当前学习证据：

- 用户指出当前多为照着参考代码输入，提出先拆需求、优先自己判断、分层提示、逐步增加独立练习，并明确无需一次纠正全部习惯。已据此更新 notes/Codex学习导师提示词.md 与 notes/README.md 的协作说明，不把该文档当成新的进度来源。
- 当前聊天接线断言已参考 Codex 提供的完整示例补写，并存在尚未修齐的字典键名等结构差异；本轮尚未确认正确 RED，生产接线仍未实现。这些断言不能记为独立测试设计证据，后续可用一个小变式补充验证，不抹去此前真实测试与手写记录。
- 下一次继续时，先让用户用自己的话说明一个局部核心任务的目标、输入输出与必要条件，再共同补齐。修正现有断言后确认正确 RED，核心 SQL/编排先由用户尝试，卡住再给最少必要提示，不重新发送全套答案。
- 本次只调整教学文档，没有修改业务代码或测试，没有运行 pytest，也不新增功能验收；最近实际通过的全量基线仍为 62 passed（2026-10-24），阶段 7 和已确认 Memory V1.1 方案保持原状态。

2026-10-26 当前学习现场整理与提交核验：

- 用户明确要求参考之前风格整理提交，本次按功能、测试准备、导师提示词与路线文档分类；不推送，不纳入原有 .vscode/settings.json 与 playground/03_class.py。
- 已本地提交：`abf48e2 feat: 新增批量记忆持久化与事务回滚`、`9e6544b test: 保存聊天记忆接线草稿与模型隔离样板`、`57ae9ae docs: 调整导师提示词为渐进自主练习`；本段路线与方案随后单独作 docs 提交，最终哈希以 Git 历史为准。
- 归档前实际完整运行为 3 failed、62 passed：保存成功和显式失败场景缺少目标反馈，普通失败场景先遇到字典键名错误。这不是本主题已确认的正确 RED，不为整理提交代写用户的关键断言或生产实现。
- 未完成样板保存在 [聊天接线测试（后续已恢复）](../tests/test_chat_memory.py)，核心断言原样保留；[草稿说明](../tests/drafts/README.md) 记录当前缺口与恢复方法。文件名不匹配 pytest 默认收集规则，只是保存学习现场，不是删除或跳过此前通过的测试。
- 归档后实际执行默认全量离线 pytest：62 passed；显式对草稿 collect-only：3 tests collected。草稿三例不计入通过基线。批量持久化目标两例已包含在这 62 项中；主聊天接线、反馈 SQL、Agent 指令、分层读取和注入仍未实现。
- 下次继续先核对并修正草稿断言，恢复到 tests/test_chat_memory.py，确认正确 RED 后再练一个完整核心片段；不因本次提交回到已收口主题，也不把参考辅助完成写成独立实现。

2026-10-26 教学重心再次调整（最新执行要求）：

- 用户明确表示以理解设计为主，恢复此前讲解与局部参考的节奏。稍早的渐进自主训练记录为历史决定，后续不再强制每主题先独立写、闭卷复现或补变式练习。
- 用户随后提供两张学习/面试经验截图并确认据此校正导师：吸收带问题读开源源码、参考局部实现及追踪失败边界的方法，以四个核心问题组织教学；不把个人面试经历或生产机制清单当作通用要求，不增加后训练等新主线。已同步导师提示词和笔记说明。
- 用户又提供速成路线截图，补充时间不充裕、目标并非从零手搓。导师约定进一步明确投入优先级与项目驱动节奏，允许复用参考、AI 样板和已有验证，取消机械重复；不据此新增复杂 RAG、多 Agent 或改动已确认阶段顺序。此次仍仅调整教学文档。
- 用户随后澄清“不赶时间”：上述效率要求仅指减少无效重复，不是速成或进度优先。后续保持从容、扎实的节奏，必要原理和设计先讲透，不以尽快跑通为由延后关键理解；完成状态与测试基线不变。
- 当前继续解释主聊天接线、事务与失败隔离的设计，再结合草稿断言和局部参考确认正确 RED；实现仍须实际运行目标测试与全量回归。提供参考与直接改核心文件的授权分开处理。
- 本次只修改教学与继续学习说明，不修改生产代码或测试逻辑，不新增功能验收，不重跑 pytest；最近实际基线仍为默认回归 62 passed，聊天接线草稿三例未通过。此前提交记录保留，本次文档调整尚未提交。

2026-10-28 恢复聊天记忆接线与正确 RED：

- 先核验现有默认回归为 62 passed；将归档草稿恢复为 tests/test_chat_memory.py，统一三处字典键名，保留用户原有关键断言和目标行为，并整理已完成 TODO 注释。
- 实际目标为 3 failed，完整回归为 3 failed、62 passed。保存成功用例缺少成功反馈；普通提取失败用例缺少 app.main 的安全失败分类日志；显式保存失败用例缺少未保存反馈。没有 collection error 或 KeyError，符合未实现主聊天接线的正确 RED。
- 当前 main.chat 提交原正常回答与主调用记录后直接返回，尚未调用记忆编排；不将正常回答或原成功 model_call 因记忆失败改成失败。更新助手消息、独立反馈事务、主提示词和编排均尚未实现；本轮只恢复测试与同步事实，不直接代改核心实现。
- 继续讲解已确认的方案 5.7，已答过的事务与模型调用次数问题不重问；结合局部参考推进，不额外生成整套导学/面经文件或重新规划阶段。

2026-10-28 聊天记忆接线 GREEN 与连接归属说明：

- 用户参考局部实现完成 database 的助手内容更新、main 的反馈事务与记忆编排及路由钩子、memory 的保存触发线索、agent 的系统指令传递；属于参考辅助完成，不记为从零独立设计。
- 首次目标为 2 failed、1 passed，根因是 process_memory_after_reply 反馈回写成功后遗漏 return final_answer，隐式返回 None，导致 ChatResponse 校验失败；普通失败分支提前返回原回答所以通过。用户补齐返回值后，实测目标 3 passed、全量离线 65 passed，git diff --check 通过。
- 测试以 fake Agent/提取器隔离真实模型，HTTP、临时文件 SQLite、来源绑定与写入真实执行，验证跨连接落库、回答/历史一致及提取失败隔离；不将其视为真实模型遵守提示词或生产运行证明，也未验证所有反馈回写故障组合。
- 用户正确说明已提交记忆不因后续独立反馈事务失败而撤销；仍追问路由钩子是否需要另开连接。按真实源码说明：process_memory_after_reply 负责编排，persist_memory_writes 和 persist_assistant_feedback 各自在内部创建、提交/回滚并关闭连接；路由不必额外创建，连接关闭不删除同一文件库已提交的数据。先说明这一归属再收口，不提前扩展读取或重试。
- 当前尚未整理代码格式或提交。原编辑器设置与独立练习保留，已有未提交教学文档不覆盖。

2026-10-28 记忆读取与覆盖合并：

- 聊天接线已完成目标 3 passed / 全量 65 passed 验证，连接归属已按真实调用链解释；用户要求继续，进入已确认的范围隔离读取与同 key 会话级覆盖主题，不重复旧事务检查题。
- 用户正确预测 scope_id IN 会返回示例四条，但当前请求只应使用①②；补充 scope + scope_id 决定读取资格，key 用于类别与合并，不必为本轮全量读取先限定一个 key。
- 局部接口、连接归属和失败契约见方案 6.1。只新增 tests/test_memory_reading.py，核心读取/合并函数尚未代写；Codex 准备真实 SQLite 和关键行为断言，符合当前以设计理解与局部参考为主的节奏。
- 实测目标 2 failed、全量 2 failed / 65 passed，均因缺少 database.load_memories。下一步参考实现 load_memories 和 merge_memories，目标与全量 GREEN 后更新基线。当前不接入聊天或注入 Prompt，不自行提交。

2026-10-28 记忆读取与合并 GREEN：

- 用户参考局部实现完成 load_memories 与 merge_memories；目标首次 1 failed、1 passed，范围和会话归属已通过，合并仍返回中文。真实 diff 显示 return merged 位于外层循环内，处理 user 后提前返回，尚未应用 conversation 覆盖；Codex 定位并解释，用户修正缩进。
- 修正后实际目标 2 passed、全量离线 67 passed，git diff --check 通过。真实 SQLite 验证交叉重名 ID 不串范围、同用户另一会话的全局偏好可读、局部偏好不跨会话、归属不匹配拒绝、合并不依赖行顺序且数据库原值不变；未调用真实模型。
- 用户已正确预测错误 SQL 会读取四条、当前范围只应返回①②；补充 key 用于类别和合并。实现及缩进修复在参考/提示下完成，不记为独立设计或独立调试。该集中单元收口，不重复此前范围或事务检查题。
- 下一主题为 Core/Regular 选择、注入预算与 Prompt 接入。先明确 key 分类、普通记忆匹配规则、预算及消息封装，不将读取函数通过等同于模型已经使用记忆；不自行提交，原无关改动保留。

2026-10-28 分类提交前复核：

- 用户明确要求整理当前已完成部分，本次按聊天接线、读取合并、导师约定与正式路线四批本地提交；不推送，不纳入 .vscode/settings.json 与 playground/03_class.py。
- Codex 仅整理本轮新增函数缩进、注释及局部变量 value 的拼写；归一该局部变量并忽略 docstring 后 AST 对比一致，无其他业务改动。清理测试旧“尚未实现”说明，恢复后的测试作为正常回归保留。
- 最终实测接线/读取合并目标 5 passed、全量离线 67 passed，diff 检查通过；审查发现的方案/阶段 7 当前摘要仍称接线与读取待实现的旧表述已同步。测试使用 fake 模型与真实临时 SQLite，不宣称真实模型/生产可靠性验证。
- 当前下一步保持 Core/Regular 选择、预算和 Prompt 注入的局部设计；本次不新增这些行为或完整记忆系统完成标志。提交记录以 Git 历史为准。
- 已完成本地提交：`e581516 feat: 接通聊天记忆写入与独立失败反馈`、`4e46ad7 feat: 新增记忆范围隔离读取与覆盖合并`、`b761227 docs: 校准设计理解与产品源码学习方式`；本段路线与方案另作最后一批 docs 提交，无推送。

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

当前已完成存储、提取结构模型、轻量触发、提取调用、候选绑定、批量持久化、聊天后的写入接线及归属隔离读取/合并；最近全量 67 passed。读取接入聊天、Core/Regular 选择、预算、Prompt 注入及端到端验收尚未完成，检查/删除按 P1 推进，不把局部单元通过记为完整记忆系统完成。

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

### 优秀产品与开源设计的对照学习安排

2026-10-28 用户明确希望吸收此前参考图片中的完整方法：学习基础机制后，实际研究优秀 Agent 产品及源码，参考其设计改进自己的 Agent，再服务于心屿落地。该环节不只是遇到 bug 时临时查资料，也不等同于再学一批框架 API。

- 时机：沿当前记忆闭环继续，不中断已确认下一步；基础机制形成可解释的闭环后，可穿插完整设计专题，不必等所有框架阶段结束。若需重排正式开发阶段，再单独明确，不以本段自动改变完成状态。
- 候选：优先考虑用户提到的 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)，按专题对照 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的记忆/历史机制及 [OpenCode](https://github.com/anomalyco/opencode) 的编程 Agent 产品设计；每轮只选一个主读对象，其他按需对照，不要求全读。
- 2026-10-28 仅核对上述官方仓库与 README：DeepSeek Harness 是插件化 harness，并仍标注 developer preview；OpenCode 是开源编程 Agent；Hermes 提供记忆、会话与历史检索相关能力。尚未完成本轮源码深读、产品体验或生产可靠性验证，不把候选介绍计为学习验收。
- 学习流程：实际体验一个代表性任务 → 产品流程与架构总览 → 核心源码调用链 → 正常/失败行为及设计取舍 → 与 agent-lab 对照 → 选择适合心屿的改进并验证。无法运行时记录证据限制，先做文档/源码阅读。
- 设计范围：上下文、记忆、工具执行、失败恢复与观测，也包括会话组织、任务状态、权限确认、取消/重试和结果反馈。不为覆盖所有维度制造功能；按实际产品与业务需要选择。
- 产出：简短的产品/架构图、一个核心链路说明、设计取舍与代价、可借鉴/不适用的部分、适量改进及验证依据。参考的是机制与设计，不默认复制完整产品、插件系统或编程语言；心屿保持 Java 业务后端 + Python AI 服务方向。

## 13. 阶段 11：以 Java + Python 后端接入心屿

2026-10-28 用户明确：保留 Python 实现 Agent 与 AI 能力，心屿采用 Java + Python 后端。这里的“迁移”指将实验能力整理为可集成的服务，不是改写为 Java；此前“Java 侧迁移”的表述据此修正。该决定不代表服务接入已实现，也不预先锁定框架、部署方式或数据库方案。

职责方向：Java 保留现有业务、登录与权限入口；Python 承接模型调用、Agent 编排、记忆和 RAG 等 AI 能力。Java 向 Python 提供经权限校验的必要业务上下文；内部接口认证、数据归属、持久化职责、超时与错误契约在实际接入前设计，不能依靠模型判断权限，也不默认把实验 SQLite 原样作为心屿存储方案。

迁移原则：

```text
agent-lab 中先理解
→ 写出最小实现
→ 正常 / 错误测试
→ 自己复述
→ 保留 Python AI 实现并整理服务接口
→ 与心屿 Java 业务后端集成
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

阶段 5、阶段 6 已完成第一轮。阶段 7 的归属检查、记忆存储、结构模型、轻量触发、提取调用、候选绑定、批量持久化、聊天后的写入接线和范围隔离读取/覆盖合并均已验证。最新读取目标 2 passed、全量离线 67 passed（2026-10-28），diff 检查通过。已答过的模型调用、来源绑定、事务、连接归属、读取范围和合并顺序不重问。

```text
当前小主题：Core/Regular 选择、预算与 Prompt 注入的局部设计 → 行为预测 → 代表性 RED → 参考实现与验证
```

读取契约见方案 6.1，已实现 database.load_memories 与 memory.merge_memories。用户正确预测了范围读取，参考实现并在提示下修正循环提前 return；属于参考辅助完成，当前单元收口，不强制额外独立重写。读取与合并尚未接入 /chat 的回答前流程，模型仍未获得 memory 上下文。

下一步围绕回答前链路集中确定：固定 key 如何映射 Core/Regular、普通记忆按问题类别如何选择、条数/长度预算及超限处理、独立上下文的角色和封装、读取接线与失败回退。总体选型沿用既定方案，不引入向量库、额外选择模型或新框架。上述局部契约明确后，复用已有 fake HTTP/SQLite 样板完成代表性正确 RED，再提供连贯参考，GREEN 后运行目标与全量回归。

随后完成跨会话/改口更新的闭环验证；检查、删除与防重建按 P1 契约推进。优秀产品设计对照学习，以及心屿 Java 业务后端 + Python AI 服务方向保持不变。当前可按用户明确指令整理已通过单元的提交，不自动 commit 或 push。
