# agent-lab 总体学习路线

> 文档角色：这是个人整体学习路线（技术栈主线）中 Python / FastAPI / Agent 部分的详细子路线，不是另一条并行总路线。
>
> 维护位置：本文件是 agent-lab 项目路线的唯一正式版本，与代码和测试一起更新。
>
> 最近核验：2026-11-05；阶段9 LangGraph第一轮核心机制学习与离线验证已收口，相关11 passed（1.20秒）、全量159 passed（2.11秒），diff及离线锁检查通过。覆盖独立计算器图、检查点、人工确认和后续模型超时恢复，正式/chat仍用原生实现；真实模型图联调、进程重启/崩溃及外部动作幂等未验证。失败恢复测试提交38527e6，阶段总结及接续文档随本检查点另作docs提交，不推送；下一主题为阶段10 SSE事件与HTTP流前置。已有图f9b9a20、文档95e16fb、检查点/确认8876380与408fce3。最小顺序图此前已GREEN；LangChain独立机制学习与验收已完成第一轮，流式目标2 passed、阶段8收口基线148 passed；一次真实流式请求收到73个片段（8个含正文）、stop及134 tokens。下一阶段进入LangGraph的State/Node/Edge；流式本批按用户要求保存本地检查点，不推送。此前共享场景6 passed；用户授权真实.env配置后，九组合成场景12次模型调用/8217 tokens，经逐题复核通过有限验收。原生与框架适配的历史、计算器、资料事实/引用和不足说明均符合预期，独立预建Agent计算器亦通过。该批后已完成独立流式入口，正式/chat未迁移。阶段7收口时为116 passed。以下阶段7的12次HTTP记录是此前原生RAG验收，与本次九组模型对照分别记录。用户澄清工具引用说明后，同组合成6题分别关闭/开启知识库，经进程内正式 /chat、真实BGE-M3/Chroma和聊天API完成12次HTTP请求、17次模型调用、16172 tokens。4道可答题事实及对应引用均正确，5道资料题无无效ID；电话未编造、问候不检索，来源快照与原文位置及实际检索一致。原生最小RAG第一轮在该有限范围内收口，首次引用失败和一次连接中断记录保留；不据单轮小样本证明因果或通用可靠性。功能基线c71a713及本次引用说明/验收材料a00e874已本地提交；路线和入口文档随本检查点同步，不推送。关键词工具竞争、部署网络路径及真实记忆效果未验证。

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

### 集中学习时间目标与 P1 协作（2026-10-28 最新补充）

- 用户将 **2026-11-08 前结束 agent-lab 集中学习、开始心屿接入**作为目标。用户说明每天学习时间较长，认为时间充足，不要求赶进度；该日期用于安排阶段节奏，不作为压缩必要理解或核验的理由。
- 保留当前完整主线、LangChain/LangGraph、SSE、优秀产品与开源设计对照的学习安排，不因日期自行跳过、降低验收标准或后移这些内容。按真实进度滚动安排；若确实出现影响目标的阻塞，明确剩余工作与证据后再讨论调整，不预先假定来不及。
- P0 核心链路继续采用设计讲解、行为预测、局部参考、用户参与、实际验证的方式，不自动接管整个阶段。
- 用户授权部分 P1 由 Codex 实现并验证，再结合实际源码讲清需求、设计、执行链与边界；这是减少重复编码，不是跳过理解。此授权不代表所有 P1 都交给 Codex。
- P1 中有学习价值的关键部分仍可由用户参与设计、参考输入或局部修改。例如删除范围与归属条件、删除后从旧消息防重建的关键规则，应先讲清，并结合用户当轮意愿保留核心任务；重复路由样板、数据准备与回归执行由 Codex 处理。参与不等于要求从零独立实现。
- 不为每个机械步骤重复申请授权；涉及新的外部行为、持久化结构或架构边界时集中明确契约。现有不自动 commit/push、保留编辑器设置与独立练习未提交的规则继续适用。

## 2. 当前进度

| 阶段 | 状态 | 完成标志 |
| --- | --- | --- |
| 1. Python 必要基础 | **已完成第一轮** | JSON、推导式、uv、异步、pytest 已做基础练习 |
| 2. 读懂现有 agent-lab | **已完成第一轮** | 能解释核心文件和当前请求链 |
| 3. FastAPI 请求链 | **已完成第一轮** | 完成请求、校验、响应、异常和测试 |
| 4. 真实 LLM 调用 | **已完成第一轮** | 异步单轮调用、错误边界、安全日志和 Token usage 已验证 |
| 5. SQLite 与多轮对话 | **已完成第一轮** | 会话可持久化、恢复和隔离 |
| 6. 原生 Tool Calling 与 Agent 循环 | **已完成第一轮** | 三工具、原生循环和失败边界已验证；完成 Pydantic 参数校验、MCP 接线与 Tool / Resource / Prompt 职责复述 |
| 7. 轻量记忆与原生最小 RAG | **已完成第一轮最小闭环（有限验收）** | 离线116 passed；真实合成固定题12次请求通过，事实/引用/不足说明及按需检索符合预期；真实记忆效果等边界仍保留 |
| 8. LangChain | **已完成第一轮独立机制学习与验收** | 消息/模板、工具循环、检索/RAG、项目契约、回调及独立文本流；离线148 passed，非流式与流式真实合成验收通过，保留预建Agent业务差异 |
| 9. LangGraph | **已完成第一轮核心机制学习与离线验证** | 独立计算器图的State/条件边/循环与预算、内存及SQLite读回、同意/拒绝及后续模型超时恢复已验证；正式/chat未迁移 |
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
- 记忆补充：app/services/memory.py 已提供触发、提取、候选绑定、批量持久化、merge_memories 和 build_memory_context；main.py 回答前独立读取记忆，正常聊天提交后处理提取写入及反馈，database.py 提供助手内容更新和归属隔离 load_memories。memory_context 独立传经 Agent 到 LLM 的每次请求，SQLite 记忆读取错误回退为空；tests/test_chat_memory.py、test_memory_reading.py、test_memory_context.py、test_chat_memory_context.py 及 test_memory_end_to_end.py 提供离线验证，跨会话改口端到端验收已通过，真实模型提取准确性和偏好遵循性仍未验证。

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

当前记忆最小闭环已完成存储、按需提取写入、范围隔离、Core/Regular 选择预算、Prompt 注入和失败隔离，以及 P1 的原始记录查看、明确范围删除、顺序执行下不重扫旧历史及重新明确保存验收；最近全量 78 passed。用户已理解关键请求链和路由职责，记忆单元收口，转入原生 RAG。真实模型提取准确性/偏好遵循性、并发在途任务防重建和自然语言删除未验证，不将最小闭环记为生产完整性或整个阶段 7 完成。

### 原生最小 RAG

2026-10-29 前置环境与选型核对：用户明确希望先准备 Ollama、Embedding 模型和组件选型，再推进切分实现。实际只读核验本机 Apple M5、24 GiB 内存、Ollama CLI 0.40.6，可访问本地模型服务；已有 bge-m3:latest，模型 ID 790764642607、约1.2GB，ollama show 显示566.70M参数、F16、8192上下文、1024维、embedding能力。此次未下载模型、未调用嵌入推理、未变更环境配置。

起步建议（待后续验证，不记为已实现）：复用 Ollama+bge-m3 生成文档与问题向量，回答沿用现有 DeepSeek 调用；先以少量笔记、Python 内存向量和余弦相似度建立可观察基线，再明确持久化方案，不立即引入向量数据库服务或框架。官方候选 Qwen3-Embedding:0.6b 的 Ollama权重约639MB、官方模型卡支持1024维/32K，可作后续对照；本地已有BGE-M3，无需为了开始学习重复下载。不能混用不同Embedding模型的向量，切换模型需重建相应索引；本项目检索效果仍须固定中文问题验证，不能仅据宣传排名判断。官方参考：[BGE-M3](https://ollama.com/library/bge-m3)、[Ollama Embeddings](https://docs.ollama.com/capabilities/embeddings)、[Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)。

2026-10-29 本地 Embedding 实测：用户同意继续此项验证后，Codex 添加独立探索脚本 `playground/rag_embedding_probe.py`，使用已有 httpx 请求本机 `POST /api/embed`，input 为一个中文问题和三个合成段落，显式 truncate=false。脚本检查输入/输出数量、1024维和有限值，原生 Python 计算余弦并保存摘要至 `playground/results/bge_m3_probe.json`。真实执行成功：向量4条、范数约1；问题“为什么请求模型前要释放数据库连接？”对应事务/关闭连接段落0.7232369，记忆范围段落0.4108395，做菜段落0.2160021；本次耗时约1.183秒、prompt_eval_count=82。只是一组探索结果，不是检索效果评测、吞吐基准或得分阈值，不把分数当正确概率；没有调用DeepSeek、下载权重或修改生产接口。本轮是第一次模型API探索，允许先观察真实响应，不强造RED或新增镜像测试；正式嵌入服务接入后仍需fake HTTP的关键验证，pytest保持不访问真实模型。

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

2026-11-02 教学分组估计：先按约6个集中主题推进，单次主题不等于一轮对话或固定时长；实际失败边界可能需要局部拆分，不为凑数量压缩必要讲解。

| 集中主题 | 范围 | 当前状态 |
| --- | --- | --- |
| 1. Chat Model与消息抽象 | 单次请求、AIMessage、fake HTTP与原生机制对照 | 已完成本单元离线验证及测试带读 |
| 2. Prompt template与Runnable组合 | 变量填充、历史消息占位、prompt与model链式调用 | 已完成本单元离线验证与带读 |
| 3. Tool与Agent循环 | 工具声明、执行回传、停止与失败边界 | 计算器适配与预建循环已限定离线验证，完整业务契约仍待对齐 |
| 4. Retriever与RAG链 | 复用原生片段/索引，比较框架检索及回答链 | 异步检索及严格回答链已离线GREEN，普通Agent语义工具尚未适配 |
| 5. 项目契约与原生对照验收 | LLMResult/错误适配、调用记录及同题/同契约验证 | 共享6场景与九组真实合成场景验收完成，预建Agent业务差异已记录，限定范围收口 |
| 6. 回调、日志与流式接口 | 框架观测和流式调用入口；完整SSE仍归阶段10 | 回调及独立文本流已完成限定验证；元数据、中断前缀/资源关闭离线通过，一次真实正常流通过 |

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

2026-11-05第一轮按独立机制范围收口，详见[阶段总结](./LangGraph阶段总结.md)。已完成下列核心主题及代表性正常/失败验证；理解证据来自用户行为预测、参考补写、源码追问和运行核验，不记为脱离参考独立设计。工具前人工确认通过计算器演示，未接入真实高风险业务动作或身份权限。进程重启/崩溃、外部写入幂等、真实模型图联调与正式应用迁移边界继续保留；不因生产完整度要求阻塞阶段10。

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

2026-11-02 教程与题库补充约定：用户同意参考以下四个项目，之后按需补充，现有主线和阶段顺序先保持不变。继续以 agent-lab 的源码、测试和本路线为正式进度；外部资料结合当前主题选读，用于原理对照、设计取舍、效果评估与项目表达，不另开四套并行课程。

- [Hello-Agents](https://github.com/datawhalechina/hello-agents)：对照 Agent 范式、自建框架、记忆检索、上下文与评估，按已有实践定向阅读章节和示例。
- [All-in-RAG](https://github.com/datawhalechina/all-in-rag)：补充分块、检索优化和 RAG 评估；先完成已定原生闭环，优化方案结合固定问题和对照实验选择。
- [AgentGuide](https://github.com/adongwanai/AgentGuide)：作为工程知识地图、项目落地与面试追问参考，使用前核对具体页面是否已完成。
- [AI Agent Interview Guide](https://github.com/bcefghj/ai-agent-interview-guide)：按用户偏好选择 Star 较高的这个同名项目，用题库检查理解，结合 Python 引用解析等源码讨论边界，不照搬模板经历或未经验证的生产能力描述。

本轮已核对四个仓库的目录、维护数据，并抽读部分正文与代码，未运行它们的项目。补充资料不自动改变当前下一步：仍继续回答引用的程序校验与显式 RAG 空资料兜底，再做 /chat 接线和端到端验收；LangChain、LangGraph、SSE 及心屿 Java + Python 接入安排沿原路线推进。本轮仅记录补充参考约定，不新增功能完成标志或测试通过数。

2026-11-02 引用处理设计与 Harness 定向对照：用户同意先将检查与处理策略分开；当前计划由检查函数返回合法引用（按出现顺序去重）和无效 ID，不在函数内直接拒答。学习助手保留回答，将无效引用明确标注、不生成来源链接并提示问题；自动修正重试暂不加入本单元。显式 RAG 无可用资料的生成前兜底保持独立。引用存在不代表资料支持结论，无引用也不能直接判定为编造；上述仍是待实现设计，不计为 GREEN。

本轮局部实现计划：新增 app/services/rag_citations.py 的 CitationCheck(valid_sources, invalid_ids) 与 check_citations(answer: str, sources: list[DocumentChunk]) -> CitationCheck；sources 只取预算后的 RagContext.sources。函数识别方括号中带 `::` 的本项目引用标记，合法来源和无效 ID 各自按首次出现顺序去重，普通 [1]、[示例] 不视为本协议引用；当前不扩展为完整 Markdown 解析器。Codex 准备数据类、占位和 tests/test_rag_citations.py，确认代表性 RED 后提供完整局部参考，用户实现核心解析与映射；之后检查真实文件、运行目标与全量回归。此单元不修改回答正文、不接入 /chat、不实现自动重试；无资料兜底及无效标记展示在上层接线时继续完成，不把纯函数通过记为整个回答链已完成。

2026-11-02 引用检查正确 RED：已新增上述数据类、函数占位及两条代表性测试，覆盖合法/未知/重复引用、同文件不同片段、未引用资料不返回、普通方括号与空来源。实测目标 2 failed、全量 2 failed / 93 passed，失败均为 check_citations 内的 NotImplementedError，无收集错误，diff 检查通过；没有访问真实模型。核心解析与映射尚未实现，下一步用户参考局部函数输入后再验证；不提交或推送，编辑器设置与独立练习保留。

2026-11-02 引用检查 GREEN：用户参考实现 check_citations，首次将 return 放在 for 内，导致仅处理首条引用、无引用时隐式返回 None；依据两条真实失败输出定位后，用户将 return 移到循环外。实测目标2 passed、默认全量95 passed、diff检查通过，不调用真实模型。用户已理解 by_id 为本轮真实切片的 ID 映射，并指出同一来源在多段正文中仍应保留每处角标；已明确当前仅来源列表去重，函数不改正文。此单元属于参考辅助实现，验证来源映射而非语义忠实，不记为完整 RAG 回答闭环；无效引用标注、空资料短路与 /chat 接线继续待实现。未提交或推送，编辑器、独立练习及新增的其他笔记保持原样。

2026-11-02 上层 RAG 回答编排局部计划：新增 app/services/rag_answer.py，复用 retrieve → build_rag_context → run_agent → check_citations，不另建 Agent 循环。接口 answer_with_rag(message: str, persist_directory: Path, history=None, *, memory_context="", top_k=3, max_chars=4000) -> RagAnswer；输出 answer、实际合法引用 sources、invalid_ids 和原始 model_calls。预算后无来源时返回明确缺少可用片段的应用文本、空来源及空调用记录，不请求回答模型；有片段不代表足以回答，允许模型如实说明不足而不要求固定短语。合法角标逐处保留，无效标记每处替换为 [引用未找到]、末尾追加一次提示；原始 LLMResult 不被展示文本覆盖。检索/Agent 异常原样传播；若返回的最终正文不是非空字符串，RagAnswerError 携带已完成调用，后续 /chat 需接住并保存，不能将真实调用丢失或当作空资料。此层只处理既有方括号 ID 协议，不是完整 Markdown 或事实核验器。

分工与验证：Codex 准备 RagAnswer、RagAnswerError、文案常量、函数占位与 fake 检索/Agent 测试，用户参考实现核心编排。正常样例同时验证预算排除后的引用无效、合法重复角标保留、未知角标逐处标注、来源去重、历史和原始模型记录不改；关键分支验证空检索/零预算跳过 Agent、检索/Agent 故障不冒充无资料、无有效正文时保留调用。先确认 RED，再由用户实现，目标与全量 GREEN 后更新基线；本单元暂不改 /chat、不做真实模型调用、不自动提交或推送。

2026-11-02 上层回答编排正确 RED：已准备上述模块及 tests/test_rag_answer.py，目标6 failed，全量6 failed / 95 passed；四例直接遇到函数内 NotImplementedError，两例故障传播断言因占位异常并非预设异常而失败，均源于核心尚未实现，无收集错误，diff检查通过。测试使用 fake 检索与 fake Agent，不接触本地/云端模型或实际索引。下一步用户参考完整局部函数实现后检查目标与全量，不把占位提交为已完成功能。

2026-11-02 严格回答编排 GREEN 与检索策略调整：用户参考实现 answer_with_rag，初次 context.sourcess 拼写错误使目标1 failed / 5 passed，修正后默认全量101 passed。已解释类型/空白正文检查、生成后处理和真实调用保留。用户指出应先结合案例确定整体策略，不应把 use_rag 开关及“无片段跳过 Agent”直接推广为普通聊天默认流程；讨论后用户同意普通对话由 Agent 按需调用检索工具，当前 answer_with_rag 保留为明确限定知识库的严格路径。严格路径的生成前无资料兜底、生成后无效角标标注和来源映射已离线验证；尚未接入路由，不能记为完整 RAG 验收。

普通 Agent 检索接线计划：保留经 MCP 执行的字面关键词 search_notes；新增语义工具 search_knowledge，直接复用当前 Python retrieve/build_rag_context。模型只给 query，应用指定专用索引目录、TopK 和每次结果字符预算，避免模型指定文件路径。Agent 将 content 作为对应 tool_call_id 的 tool 消息回传，同时登记同次返回的 sources；本轮多次调用累积实际交付片段，最终引用检查以该白名单为准。空结果是正常工具结果，允许模型调整查询或解释资料缺失，不在该工具内直接结束整轮或生成固定拒答；服务异常沿现有 AgentToolError 保留已完成调用。最终来源响应与标注策略继续复用已确认规则。各次工具预算并非整轮总上下文预算，不扩大已有保证。

当前工具边界单元：Codex 已添加 tools.py 的 SearchKnowledgeArguments 与 SEARCH_KNOWLEDGE_TOOL（尚未加入 AVAILABLE_TOOLS，等待 Agent 接线），新增 rag_tools.py 的 execute_knowledge_search(tool_call, persist_directory, *, top_k=3, max_chars=4000) -> RagContext 占位及 tests/test_rag_tools.py。测试验证查询去空白、应用参数传递、预算选择后的 content/sources 对应、模型不能夹带索引路径、空结果与真实故障分开。实测目标2 failed、默认全量2 failed / 101 passed，均因占位 NotImplementedError，无收集错误，diff检查通过；下一步用户参考实现参数校验、检索和预算选择，验证后再集中接 Agent 循环。未调用真实模型、未提交或推送，原无关内容保留。

2026-11-02 工具补写检查与注释纠偏：用户已参考补写适配函数，目标2 failed，均因把工具名写成 search_konwledge 导致合法请求在名称检查时被 ValueError 拒绝；错误文案也有同一拼写，待用户统一改为 knowledge 后再验。该失败替代此前占位失败，不记作 GREEN；最近全量全绿仍是新增工具测试前的101 passed。用户要求每次补写讲清核心链路及 Codex 新增部分，已同步导师约定。Codex 只修正文档与注释：RagContext 表达预算内准备传递的资料，不冒充已发模型；工具声明不等于执行注册；源码不写“尚待接线”等进度；answer_with_rag 明确为严格知识库路径；引用检查只做本轮 ID 映射、保留正文重复角标，不做语义核验。未更改用户核心实现或既有模型提示词，diff检查通过，没有真实模型调用或提交推送。

2026-11-02 工具适配 GREEN 与 Agent 接线 RED：用户修正工具名后全量103 passed，Codex 顺手统一不影响逻辑的错误文案 knowledge 拼写。适配层已验证参数、预算、空结果与故障传播；空结果交给调用方，不结束 Agent。下一单元契约为 run_agent 新增 keyword-only knowledge_directory: Path | None = None：配置目录时使用 AVAILABLE_TOOLS 的本轮副本并追加 SEARCH_KNOWLEDGE_TOOL，None 时不声明也不执行该工具，不修改全局基础列表。遇到工具请求时调用 execute_knowledge_search，content 进入现有 tool 消息并保留 call_id 关联；sources 以知识工具本轮资料列表累积，空内容换成明确的空结果工具文本，允许下一次模型判断。最终 AgentResult 新增 knowledge_sources（独立默认空列表，可重复，不表示实际引用），原始 answer/model_calls 保持原职责；外部 rag_context 的来源仍由其调用方保留。本单元不在 Agent 内提前标注最终引用，也不修改 /chat 或给所有请求强制检索。

Codex 已准备上述返回字段、导入和 tests/test_agent_knowledge.py，核心签名、工具清单选择、执行分发与来源累积由用户参考实现。测试覆盖三次模型调用内两轮语义检索＋真实计算器、预算排除、来源累积、历史不改；直接回答不检索、空结果后继续；未启用或检索故障按 AgentToolError 保存已完成调用。目标5 failed、全量5 failed / 103 passed，均因缺少 knowledge_directory 参数的 TypeError，正确 RED，无收集错误，diff检查通过。fake 模型与检索隔离网络，不宣称模型实际会选择正确工具；本轮未提交推送。

2026-11-02 Agent 语义工具接线 GREEN：用户参考补全 knowledge_directory 参数、每轮能力副本、语义工具执行、knowledge_sources 累积和返回。实测目标5 passed、默认全量108 passed；Codex 仅补参数尾逗号、去一处行尾空格、更新执行分支和返回值注释，业务实现保留，diff检查通过。真实执行 Agent 循环、语义工具适配/预算和计算器，只有生成接口与检索底层用 fake，验证多轮资料交付、call_id 关联、跨调用来源累积、空结果继续、直接回答不检索、禁用/检索失败保留调用；未改 history/global AVAILABLE_TOOLS。尚未启用 /chat 的语义工具或将 knowledge_sources 变成实际引用响应，未访问真实模型。此单元适合整理提交，仍需用户授权；原设置、独立练习与其他未提交笔记保留。

Agent 接线独立只读复核：限定检查工具适配与循环接线，无当前契约下阻碍问题；复核了能力副本/禁用边界、调用 ID、预算内来源累积、空结果和错误原因/调用保留。复核者仅静态阅读，未运行测试或模型；目标及全量证据来自上述主流程实测。不因可选补测建议扩展当前单元，原有预算和独立 rag_context 回归继续保留。

2026-11-02 共用回答收尾局部计划与 RED：将 answer_with_rag 末尾已有的正文检查、引用校验、无效标记替换和 RagAnswer 返回提取为同步 finalize_rag_answer(result: AgentResult, sources: list[DocumentChunk]) -> RagAnswer。严格路径生成后传 context.sources；普通按需工具路径由上层传 result.knowledge_sources。函数不调用检索或模型，不修改原 AgentResult/model_calls/sources，不凭空读取索引；sources 为空也允许正常无引用回答，不套用严格路径生成前的 NO_MATERIAL_ANSWER。RagAnswerError 仍保留真实调用；合法正文角标全部保留，输出来源按首次引用去重，未知 ID 标注并提示一次。Codex 已补 AgentResult 导入、函数占位、职责注释及 tests/test_rag_answer_finalization.py 两条纯函数测试；用户参考提取核心函数，并将严格路径 run_agent 之后的整段收尾替换为一次调用。实测目标2 failed，均为新占位 NotImplementedError，无收集错误，diff检查通过；未改原有严格路径行为或 /chat，不调用真实模型。后续目标/全量通过后再接 HTTP。

2026-11-02 共用收尾 GREEN 与分类提交：用户在提出整理提交时已补完 finalize_rag_answer，并将严格路径末尾改为调用它；核对真实文件后执行默认全量110 passed（包含新收尾2例和原严格问答6例），diff检查通过。独立只读复核检查引用检查器、共用收尾、严格路径及对应测试，无当前契约下阻碍问题；复核者只静态阅读，测试由主流程执行。新收尾验证工具资料含重复时按正文首次引用输出来源、保留重复合法角标、标注无效引用且不改原始回答/调用；普通 Agent 未检索的正常回答原样保留，不触发严格路径兜底。没有真实模型或业务资料调用。

2026-11-02 /chat 按需知识库接线契约与 RED：沿用已确认策略，不增加 use_rag 请求开关或强制检索。应用配置 rag_index_path 读取 RAG_INDEX_PATH，默认 None/示例留空，不自动索引或修改真实 .env；配置目录时路由给 run_agent 传 knowledge_directory，未配置时不额外传该参数，保持旧调用替身和普通路径兼容。Agent 返回后调用 finalize_rag_answer(agent_result, agent_result.knowledge_sources)，再保存收尾文本与 model_calls，后续既有记忆反馈可继续追加并回写，HTTP 回答与最终会话正文一致。

响应契约新增 ChatSource(id, source, chunk_index, start, end, text) 片段快照，以及 ChatResponse.sources 和 invalid_citation_ids 两个默认空列表；来源仅取通过引用检查的真实片段，由应用生成 id，不接受模型自行构造出处对象。这是本次 HTTP 响应中的快照，本单元不新增来源持久化表，不保证以后从历史消息恢复当时完整证据。RagAnswerError 表示已完成模型调用但缺少有效最终正文，路由应保存 completed_model_calls 并返回502，不伪造额外失败模型调用；检索故障继续沿 AgentToolError 返回502并保存此前调用，归属409必须先于检索与新消息副作用。其余模型503/504/502边界沿用。

分工：Codex 已补 config/.env.example、ChatSource/响应字段、main必要导入、测试隔离和旧成功响应的两个空字段预期；用户参考补写路由能力参数、共用收尾、RagAnswerError 捕获及来源返回。新增 tests/test_chat_knowledge.py 使用真实 HTTP、临时 SQLite/Chroma 和原生 Agent，只 fake 模型HTTP及问题嵌入，覆盖有资料/未知引用与历史一致、归属拒绝、直接回答、空索引继续、嵌入故障与空正文调用保留、未配置能力。最初六例因缺少路由接线/响应字段失败；样板加入后全量实测4 failed / 112 passed：有资料与空索引请求因工具未启用返回502，嵌入故障尚未真正进入嵌入，空正文仍返回500。两个无检索成功场景因响应默认字段已通过，不能记为整个接线已完成。无收集错误，diff检查通过，没有真实模型请求、索引业务数据或提交推送。

2026-11-02 /chat 接线 GREEN：用户参考完成可选 knowledge_directory 传入、finalize_rag_answer 调用、RagAnswerError 捕获保存调用并返回502、ChatSource 与 invalid_citation_ids 响应。实测目标6 passed、默认全量116 passed，Codex 仅去一处行尾空格和补 `) from exc` 空格，diff检查通过。验证真实临时Chroma查询与SQLite持久化：工具按配置提供且不强制使用、未知引用标注先于助手落库、重复合法角标保留、合法实际引用来源快照返回、同会话错误归属409在新副作用前拒绝、空索引仍交回模型、嵌入故障和空正文返回502且保存已发生调用。限定范围独立只读复核无阻碍问题；复核者未运行测试或模型，运行证据由主流程产生。当前未提交，不宣称真实模型会正确选择或依据资料回答，不保证历史来源快照持久化、多租户知识权限、并发或整体预算。

用户追问 HTTP 状态码，按当前源码区分接口处理结果与模型回答质量、请求侧4xx与服务侧5xx，以及上游HTTP状态与本服务状态。现有502也覆盖工具失败和调用预算耗尽，是当前统一边界的简化选择，不能当作所有内部异常都必须502的通用规则；状态码讨论本轮不改变既有契约。正常资料不足或标注无效引用仍可200，空正文/依赖失败与正常空检索分开。

2026-11-02 /chat 本地提交检查点与 RAG 剩余范围：用户明确要求整理提交本单元并询问剩余内容。提交前重新执行全量116 passed、diff检查通过，沿用已完成的限定独立复核，未新增业务逻辑。功能提交 c71a713 包含配置示例/读取、响应模型、路由及代表性端到端测试、旧响应预期同步；本段路线另作 docs 提交，不推送。编辑器设置、独立练习、其他来源的设计复核笔记保持未提交。

原生最小 RAG 的核心代码与 fake 外部接口的 HTTP 链路已打通，剩余按两个集中验收主题安排：一是少量固定问题（明确可答、跨片段、资料未包含答案和普通闲聊），分别观察检索、回答、引用及不足说明，并与未启用知识库的结果对照；二是合成资料通过真实 Ollama 嵌入和聊天 API 走正式 /chat 链路，检查模型实际工具选择、来源/回答一致性及可复现记录，形成简短收口。两项可以共用问题和资料，不重复造两套工程。真实调用仍按已授权范围使用合成资料，默认 pytest 继续 fake，不将旧组件探针当作正式路径证据；发现真实问题则修复并复验后再结束阶段7。混合检索、reranker、结构化切分等按评测需要与后续对照安排，不自动扩为当前必修。完成后按原主线进入 LangChain，之后仍会用框架对照已有 RAG。

用户提醒应先整理已完成检查点，再推进新单元，本次按依赖顺序完成本地提交：b0e57f0（语义检索工具与参数边界）、3ed2d69（Agent 按需工具接线与来源累积）、f785d8f（引用校验、严格问答及已验证的共用收尾）。学习路线与导师约定随后单独归入 docs 提交，实际哈希以 Git 历史为准；不推送。未提交 .vscode/settings.json、playground/03_class.py 和其他来源的 notes/设计复核-2026-11-02.md。本次不新增 /chat 功能，下一步先确定应用索引配置、来源响应及异常映射，再写路由接线的代表性测试，不自行提交未完成占位。

- 用户指定 [liuup/claude-code-analysis](https://github.com/liuup/claude-code-analysis) 作为补充阅读。仓库自述为 2026 年 3 月公开流传源码的第三方静态分析，不能直接代表当前官方版本。本次沿其 src/tools/WebSearchTool/prompt.ts、WebSearchTool.ts 与 src/query.ts 阅读：工具说明要求来源列表，工具结果追加引用提醒；结束路径的 Stop Hook 可把 blockingErrors 加回消息后继续循环。这些证据不等于内置逐条引用真实性校验，也不证明所有插件或服务端路径都没有校验。
- DeepSeek Harness：读取本机官方仓库快照 c36a83ff6b（2026-09-22），未拉取更新。packages/web/tool-web/src/search.ts 分别保存结构化来源、渲染引用提示；packages/core/agent-loop/src/agent.ts 的已读完成分支在无工具请求时返回 completed，未见该分支内正文引用逐条核验。不将此局部结论泛化到全部插件或最新版本。
- Hermes Agent：核对官方仓库快照 e8639fd4312e5102d6f10c76b56406cb01c19092 的 skills/research/grounded-citations/SKILL.md 及 scripts/sources.py。技能采用来源登记表、程序生成来源列表和 verify 检查；verify_draft 返回退出码、错误与警告，技能要求修正后重验；可选 evidence 检查附带原文摘录，但文本匹配不等于语义支持。它是本次定位到的专门技能流程，不能表述为全部普通对话强制经过该脚本。

本轮仅静态阅读，没有运行上述项目、安装技能、调用真实模型或修改 agent-lab 核心代码；不改变学习阶段顺序与既有测试完成数。

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

### 阶段9第一轮收口；接续阶段10 SSE前置（2026-11-05）

- 用户明确要求整理提交，并询问LangGraph是否结束。对照第11节主题与完成标准，按独立核心机制学习及离线验证范围收口：State/Node/Edge与reducer、条件分支/循环、预算、内存及SQLite检查点、人工确认同意/拒绝、后续模型超时后显式恢复均有源码与证据。用户已解释状态更新/路由标签/任务编号/确认与失败节点重入；引用参考补写及测试通过不记为独立设计或生产掌握。
- 新增notes/LangGraph阶段总结.md，整理主链图、原生职责对应、文件证据、成功记录与失败日志区别、当前限制及可口述项目表达；README/索引/阶段表同步第一轮收口。保留计算器范围、原生/chat、业务审计/权限未接线、无真实模型图联调、未验进程重启/崩溃/历史重放/外部幂等等边界；不将这些扩为进入下一阶段的额外前置任务。
- 提交前LangGraph相关11 passed（1.20秒），默认全量159 passed（2.11秒），diff及离线锁检查通过。失败恢复测试已本地提交38527e6；阶段总结与文档另作docs提交，准确哈希见Git。不推送，编辑器设置、独立练习和其他设计笔记保留；上一检查点/确认功能8876380、文档408fce3保留。
- 当前下一步阶段10的第一个小主题：先区分模型chunk、异步生成器、HTTP响应流与SSE事件，带读现有langchain_streaming及原生/chat，再讨论增量/完成/错误事件契约、断开取消与最终保存边界。现有Python流不等于已具备HTTP SSE，图收口也不授权自动替换原生/chat。先前置解释与行为预测，再提供局部参考和用户参与；本轮不新增SSE实现、测试或真实模型请求。优秀产品与开源设计对照专题继续按正式路线安排。

### 最新验证：模型超时后从SQLite检查点继续（2026-11-05）

- 用户确认节点失败只重试该节点，另询问历史重放及失败model_calls；已结合源码解释最新进度继续与旧checkpoint重放的区别，以及State成功LLMResult列表和业务调用表失败日志的区别。原生路由持久化失败的能力不等于独立图已接入该日志。
- Codex仅新增test_model_timeout_resumes_saved_tool_result_after_reopen，复用已有HTTP fixture、计算器请求与临时SQLite；没有修改生产核心或新建恢复API。现有框架已支持None继续，属于既有行为回归验证，未强造占位RED。prepare顺序提供工具请求、timeout、最终答案，真实适配器/节点产生LLMTimeoutError→AgentRunError。
- 实测首次退出HTTP两次、成功记录一条、工具一次；失败快照next为model，tool结果5已保存。关闭后重开同文件/同thread读取同状态，ainvoke(None, config)恢复后next为空、成功记录两条、HTTP累计三次、工具仍一次；出站第二/三次messages相同，首次成功记录及工具交互保持不变。
- 定向1 passed / 9 deselected（1.28秒），图目标10 passed（1.16秒），全量159 passed（2.04秒），diff及离线锁检查通过。模型HTTP预设，图/SDK/适配器/SQLite/计算器真实运行；同进程重开连接不记作进程重启，未验证崩溃、外部动作幂等、自动重试或生产日志。当前测试和说明未提交，旧检查点/确认功能8876380及文档408fce3已提交且main已由用户同步origin。
- 当前下一步完整带读新增测试的pytest.raises、失败快照、None继续及出站消息比较，再核对用户理解并整理阶段9有限结论；不因测试通过写成独立设计或生产完整，也不自动提交或跳入SSE。现有max_model_calls按成功结果计数，不是跨恢复的所有请求尝试总预算。

### 已整理提交；下一主题失败恢复前置（2026-11-05）

- 用户明确要求先整理提交。核验main、HEAD 95e16fb、origin及全部工作区后，仅收本批内存/SQLite检查点、共用序列化、人工确认、测试和依赖，已本地提交8876380；README/笔记/路线另作docs提交，不推送。提交前全量158 passed（2.34秒），diff和离线锁检查通过。编辑器设置、playground/03_class.py及其他设计笔记保留。
- README及索引同步158 passed与实际边界，清理模块及测试说明中不适合当前接线的旧描述；历史RED保留。内存/SQLite同进程重开连接与人工确认均为离线验证，不改成真实模型、进程重启或生产权限验收。
- 当前下一步按阶段9带读失败恢复：工具节点完成并保存后，第二次模型超时，再由调用方用原文件/原thread_id执行graph.ainvoke(None, config)，不加历史checkpoint_id，不当作Command人工回答或新任务输入。先解释失败节点重入、已提交步骤复用、外部动作幂等及成功model_calls与HTTP尝试计数的区别，给一次行为预测，再准备集中失败恢复测试；不提前实现自动RetryPolicy或重复模型预算。
- 已读官方checkpointers与fault-tolerance对应说明，结合本机已有节点/异常契约整理到notes/LangGraph检查点与恢复.md；没有新增失败恢复生产实现、测试或运行证据。当前预测场景应保留一个成功记录和工具结果，恢复只重试后续模型；通过前不记故障恢复GREEN，也不将max_model_calls按成功结果计数描述为跨恢复的所有HTTP尝试限额。

### 当前局部实践：工具前人工确认与SQLite恢复（2026-11-05）

- 最新GREEN：用户已将is None改为is True，核对实际函数后目标9 passed（1.15秒），全量158 passed（2.25秒），diff及离线锁检查通过。同意/拒绝两例均验证暂停前一次HTTP零工具，重开SQLite后确认节点进入两次，原模型不重跑；同意追加一次工具和模型请求，拒绝保留原工具请求记录、零工具且无伪造回答。真实图/SDK/适配器/SQLite/计算器与预设HTTP，不证明真实模型行为、生产权限或进程重启。路线已同步，本批未提交；下一步可整理检查点/人工确认批次，后续失败恢复先解释重试节点/已保存状态与外部副作用边界，未自动新增代码。以下失败记录保留为历史。
- 补写后核验：request_tool_approval已完整补写；choose_after_approval把is True误写为is None，导致同意/拒绝均走finish、未决定反而会选工具标签。已解释None不是False，指出应只允许明确True进入工具，并留用户修改。人工确认定向1 failed / 1 passed / 7 deselected（1.18秒），拒绝通过，同意在成功调用应为2但实际1处失败；未重跑全量、不记GREEN。以下占位RED为历史。
- 用户预测正确：暂停前不执行计算器，恢复从被中断确认节点开始；已补准恢复时节点从头执行，但再次遇到该interrupt取到本次resume值，不会因同一确认自动无限暂停。不给相同概念重复出题，进入局部接线。
- 新增langgraph_approval.py：ApprovalCalculatorState继承当前图字段/reducer，只新增tool_approved为最近一次人工决定（初始None）。Codex已写build_approval_calculator_graph机械连线，要求调用方提供checkpointer；复用call_model/call_tools/choose_next，模型后预算允许才走approval，同意才走tools，拒绝映射END。不替换原图、run入口或/chat，不将暂停/拒绝原始状态转成正常AgentResult。
- 用户参考补写request_tool_approval与choose_after_approval：从最新模型调用整理全部工具请求的call_id/name/原始arguments，interrupt展示问题及请求列表；恢复值必须为bool，再更新tool_approved；路由返回use_tools或finish。确认本步请求整体，不沿用上一工具轮的决定，拒绝不执行工具/不重调模型/不虚构最终回答。
- 新增一个参数化测试（approve/reject两例）到现有test_langgraph_agent.py，复用offline_graph及calculator_request，无新fake；observed_approval仅记录进入次数后调用真实确认函数。第一次暂停验证一次HTTP、零工具、确认负载/待执行approval及原模型记录；关闭SQLite连接后重开同文件/同thread，用Command(resume=approved)恢复。同意共两次HTTP和一次工具，拒绝仍一次HTTP和零工具，两者确认节点进入两次且最终next为空，保留真实成功记录。
- 正确RED：目标2 failed / 7 passed（1.84秒），两例均为request_tool_approval的NotImplementedError，无收集错误，diff检查通过。当前等待用户补两处核心，随后目标/全量；最近全绿156 passed仍为本主题新增测试前基线。没有真实模型请求、没有进程重启/权限前端验收，不自动提交。新增State、构建函数、观察包装、参数化与断言均须带读。

### 当前前置：人工确认与动态interrupt（2026-11-05）

- 用户修复yield缩进后，核对SQLite连接范围及旧占位注释已清理；目标7 passed（1.24秒），默认全量156 passed（2.21秒），diff与离线锁检查通过。证明真实临时SQLite文件关闭连接后新连接/新saver可读回完整状态及记录类型，任务隔离与读取不新增模型请求成立；同进程测试不记为进程重启或故障恢复验收。当前检查点批次未提交。
- 下一主题按阶段9进入human-in-the-loop，先解释interrupt负载、暂停返回、Command(resume=...)、同存储同thread恢复及中断节点从头执行，再安排工具执行前确认的局部图/测试。计算器仅作为无外部副作用的教学载体，不据此要求普通计算都人工审批；用户同意/拒绝通过调用方提供，不交给模型自行决定。
- 已读本机langgraph.types.interrupt/Command与官方interrupt文档，并运行一次纯本地单节点探索（不加入产品源码或pytest）：第一次ainvoke返回__interrupt__中的问题，snapshot.next为approval；Command(resume=True)使interrupt取得True，节点入口执行计数由1变2，最终next为空。没有模型、工具、HTTP或数据库调用；不冒充现有计算器图已接入人工确认。
- 当前先给工具前确认的流程与两个API示意，并让用户预测暂停时工具尝试次数、恢复时从哪个节点开始；随后再设计局部核心和正常同意/拒绝验证，不一次引入前端、身份鉴权、并行审批或SSE。尚未修改图核心或新增该主题测试，不自动提交。

### 当前局部实践：SQLite检查点与重开连接（2026-11-05）

- 最新GREEN：yield saver已移入内部async with，与saver赋值同级，旧占位注释已移除。目标7 passed（1.24秒），全量156 passed（2.21秒），diff及离线锁检查通过。此处以下失败记录保留为历史；下一步人工确认的前置见本节最新条目。
- 补写后核验：用户已正确概括serde是把序列化/反序列化组件交给saver。实际文件已构造SQLite saver，但yield saver缩进在内部async with之外，先关闭连接才交给调用方；旧占位注释也尚未移除。目标1 failed / 6 passed（1.44秒），首次graph.ainvoke在读取检查点时触发已关闭连接重启工作线程，报RuntimeError: threads can only be started once。根因是资源范围而非图节点或线程策略；已提供将yield移入连接块并删除旧注释的完整局部参考，核心留用户修正，目标未通过暂不跑全量，不进入下一机制。
- 用户表示完成并继续，不再纠结prepare/fixture。核对实际文件后目标6 passed（1.12秒）、全量155 passed（2.02秒）。内存接线保留，未自动提交。
- 下一主题为持久化与连接生命周期：复用当前图及一轮任务一个编号，使用独立SQLite检查点文件，不迁移业务数据库。已核验官方扩展及本机安装源码，新增langgraph-checkpoint-sqlite 3.1.3、aiosqlite 0.22.1及其sqlite-vec 0.1.9依赖，更新pyproject/uv.lock，既有包未升级，离线锁检查通过。
- Codex新增langgraph_checkpoint.py中的共用create_checkpoint_serializer，将原内存工厂配置原样抽出供两种存储复用；准备open_calculator_checkpointer的导入、装饰器/类型与核心占位。用户参考补写打开连接→构造AsyncSqliteSaver并传serde→yield saver。完整解释async with资源范围、asynccontextmanager、AsyncIterator、yield交出资源与退出清理；本机saver会按需setup，不新增业务建表SQL。
- 新增一条集中测试，复用已有假HTTP/真实图和计算器：pytest临时文件写入A任务两次模型结果，退出上下文后用新连接/新saver重建图并读回相同快照、嵌套类型/调用ID/最终回答；新任务B读取为空，总HTTP两次且计算器一次。仅验证同进程重开连接，不能写成进程重启或故障恢复已通过。
- 目标RED：1 failed / 6 passed（1.57秒），唯一失败为open_calculator_checkpointer的NotImplementedError，无收集错误；diff及锁检查通过。数据库核心未代写，尚未新增全量GREEN，最近全量155 passed为该新增场景前的基线。当前下一步提供完整局部参考、解释辅助函数及测试，再核验用户补写与目标/全量回归；无真实模型请求、不提交。

### 当前局部实践：内存checkpoint接线与任务隔离（2026-11-05）

- 最新GREEN：用户表示误撤diff，检查确认图的checkpointer参数及compile接线已由用户补好，saver工厂仍在；仅新增测试及相关导入丢失。Codex恢复原测试和LLMResult/LLMToolCall导入，保留用户核心及导入排版。目标6 passed（1.17秒），全量155 passed（1.94秒），diff检查通过。真实图/SDK/适配器/计算器与内存存取验证，HTTP响应预设；没有真实模型请求。未提交本单元。以下RED记录保留为历史，下一步可复述读回/隔离主链后进入数据库持久化前置与实践。
- 用户已正确解释新内存saver没有旧状态、读取不执行节点，并强调新任务分配新编号、同任务内部和恢复沿用原编号。已校准同存储内编号误复用对内存和数据库均有影响，不一定是重复键异常；本例一条thread对应一轮任务，不混用会话与单轮预算。
- Codex新增create_calculator_checkpointer机械配置：JsonPlusSerializer显式支持LLMResult/LLMToolCall，InMemorySaver由调用方持有并复用；已导入BaseCheckpointSaver供参数类型标注。一次性序列化往返确认两个类型和值完整还原且未再有未注册类型提示，不冒充图接线GREEN。
- 用户任务：仅给build_calculator_graph增加可选关键字参数checkpointer，并传入builder.compile；原节点/路由复用，默认不配置时原run_calculator_graph独立入口保持现有行为。完整参考及新类型、serde参数、生命周期和测试步骤须解释，核心两处不代写。
- 新增一个集中测试到tests/test_langgraph_agent.py，复用已有HTTP fixture与工具请求函数：A计算两次HTTP后同saver重建图可读取嵌套记录/工具结果；读取及已结束图None继续不新增请求；B独立编号只有一次调用且不污染A；新saver同A编号读取为空。目标1 failed / 5 passed（1.04秒），明确是build_calculator_graph不接受checkpointer关键字，无收集错误。全量最近全绿仍为前单元154 passed，本轮待用户补写后再跑目标及全量，不记155 passed。
- 本轮不安装依赖、不改/chat、不接数据库或人工确认，不验证进程重启或失败恢复，不自动提交。接线验证后再进入数据库持久化、人工确认和失败恢复的后续边界。

### 当前带读：checkpoint与跨次状态（2026-11-05）

- 用户要求整理提交后进入下一步，并明确先讲前置知识。已完成本地提交f9b9a20（模型/工具图与测试）及95e16fb（说明/笔记/路线），提交前默认全量154 passed（2.35秒），diff检查通过，不推送，保留无关工作。
- 新增notes/LangGraph检查点与恢复.md并加入索引：先解释State/检查点/存取组件/thread_id、StateSnapshot.values与next、内存与业务SQLite的区别，再区分读状态、新输入、None继续及后续人工确认。新输入仍按reducer合并，[]不能清空add列表；下一实践以一条thread对应一轮任务，不将现有model_calls预算跨聊天轮次直接累积。
- 核验本机langgraph 1.2.19相关源码及官方检查点文档。一次性内联探索复用当前State/节点/路由，仅模型入口替为预设LLMResult：同saver同thread重建图可读回问题/调用，结束快照next为空，读取及已结束图None继续均不增加模型次数；不同thread或新InMemorySaver读取values为空。自定义LLMResult反序列化出现未显式注册类型提示，下一接线需讲序列化并明确支持LLMResult/LLMToolCall，不放开任意类型。
- 本轮没有修改图核心、安装依赖、真实模型请求或新增pytest；不把探索计为正式接线、持久化/重启恢复或失败恢复已完成。当前下一步先让用户预测同thread但换新内存saver、以及读取快照会不会请求模型；然后设计checkpointer参数传递/复用与序列化，解释全部辅助代码和测试，再给局部核心参考完成RED→GREEN。

### 当前实现任务：模型/计算器图与条件边（2026-11-05）

- 最新GREEN：用户修正两处后，实际文件确认call_tools使用AgentToolError，langchain_adapter恢复parse_tool_calls调用且已无该文件diff。目标5 passed（1.10秒），默认离线全量154 passed（1.97秒），diff检查通过。验证直接结束、计算器执行后回模型、后续模型超时、非法工具参数及预算耗尽前零工具执行；图/SDK/适配器/计算器真实运行，仅模型HTTP使用预设响应，无真实模型请求。参考补写及修正不记为独立设计；用户随后明确授权整理提交；提交前全量154 passed（2.35秒），diff检查通过，代码及测试已本地提交f9b9a20，文档另作docs提交，不推送；编辑器设置、独立练习及其他设计笔记保留。下一主题按阶段9学习checkpoint/跨次状态恢复，先解释单次State、检查点与业务会话历史的区别，再安排局部实践。以下失败记录保留为历史。
- 补写后核验：用户已写四个核心函数；目标测试5 failed（1.33秒）。集中发现两处：langchain_adapter将parse_tool_calls(message_data)误改为(message_data)，导致tool_calls成为整条消息字典、直接回答也误走工具分支；call_tools将工具异常包装为AgentRunError，应为AgentToolError。已给出具体位置与修正参考，留用户修改；目标未通过，暂不重跑全量、不记GREEN、不提交。CalculatorState名称说明本例范围，现有字段可复用于多工具Agent；仅计算器限制来自工具声明和执行分发，不来自类名，暂不扩大架构。
- 用户已正确解释finish是路径标签而非State字段，path_map将其映射END；trace需要节点主动返回更新而非框架自动日志。两点不再重考，进入实际模型/工具图。
- 新增app/services/langgraph_agent.py。CalculatorState由入口初始化question/history、additional_messages与model_calls两个Annotated列表追加字段，以及max_model_calls。模型节点复用generate_langchain_result+CALCULATOR_TOOL及AGENT_SYSTEM_PROMPT，工具节点执行真实计算器并提交assistant/tool消息；不存重复last_result，使用model_calls[-1]作为最新结果。
- 分工：Codex已写_execute_calculator_requests机械执行/消息转换帮助函数，仅允许calculator，保留原始arguments/call_id；已写run_calculator_graph入口校验、状态初始化、graph.ainvoke及AgentResult映射。图调度保护recursion_limit=2*max_model_calls+1留足模型/工具交替步骤，模型次数预算仍由条件路由判断，不能把图步数当作模型请求数。用户参考补写call_model、call_tools、choose_next、build_calculator_graph四个核心函数，沿用AgentRunError/AgentToolError/AgentModelCallLimitError及成功调用快照。
- 设计要求：START→model；model后条件边根据最新工具请求走finish→END或use_tools→tools，tools固定回model。无工具请求即使达到模型次数上限也允许正常结束；有请求且预算耗尽则在工具执行前抛预算异常。首次模型失败原样传播，后续失败携带之前成功调用；工具失败保留本次成功模型调用，不虚构失败模型调用。正式/chat、原生Agent、检索/记忆和持久化不改，不运行真实模型。
- 新增tests/test_langgraph_agent.py，真实图/SDK/适配器/计算器配合fake HTTP。两个测试函数参数化为直接结束、计算器两轮、第二次超时、非法参数、仅一次预算五个场景。fixture只替HTTP客户端，execute_tool观察包装仍调用原函数，tool_attempts记录执行尝试而非成功结果；预设响应由真实HTTP请求到来时消费，不按列表长度驱动图。检查声明/历史/当前问题、call_id回传、model_calls累计、异常原因/成功快照及预算不足时零工具尝试。
- 正确RED：目标5 failed（1.45秒），均指向build_calculator_graph的NotImplementedError，无收集错误；全量5 failed / 149 passed（2.34秒），diff检查通过。当前下一步完整带读状态、两个帮助函数、图步数限制及五种测试，再给四个函数连贯参考供用户补写；核心占位不代写，不自动提交新单元。

### 当前设计带读：模型/工具节点与条件边（2026-11-04）

- 顺序图已本地提交97a69f9，配套前置笔记/索引/路线提交12bb0e5，不推送。提交前全量149 passed（2.32秒），当前开始下一主题，不自动提交新单元。
- 设计复用langchain_adapter.generate_langchain_result返回项目LLMResult、现有CALCULATOR_TOOL及execute_tool；模型节点实际调用模型入口并提交本次model_calls更新，工具节点执行计算器并提交assistant请求/tool结果消息。State保留question/history、additional_messages及model_calls追加字段、max_model_calls；不再引入纯演示preview/trace。model_calls最后一项可作为最新结果，不需要额外重复保存last_result。
- 计划结构START→model，条件边在model后读取最新tool_calls，无请求映射END，有请求且预算允许映射tools，tools完成后固定边回model；应用路由函数选择流程，不让模型直接提供图节点名。预算在执行工具前检查，避免用尽最后模型预算后继续执行无法回传的动作。图调度限制不等于模型次数预算，后续实现须区分。不改/chat、不接检索或持久化；先讲路由函数/返回标签/path_map，再准备局部核心及针对性验证。
- 当前先检查新增概念：条件边函数返回路由标签，与节点返回State更新字典不同；path_map将标签映射到节点或END。本轮仅设计带读，不新增生产图或测试、没有真实模型请求，前一检查点149 passed不记作新图验证。

### 已验证：最小两节点顺序图；下一步模型/工具流程（2026-11-04）

- 最新GREEN：用户已将两处trance改为trace、prepare_questrion标签改正，并将中间连线改为add_edge。核对实际文件后目标1 passed（0.75秒），默认全量149 passed（1.99秒），diff检查通过；参考补写及修正不记为独立设计。正常图依次运行两个节点，原question保留，normalized_question与preview正确，trace按input/prepare_question/render_preview追加，调用方输入与快照一致。没有实际问答/计算业务或真实模型请求。
- 本地文本演示按当前范围收口，不继续增加预览功能。当前下一步转与Agent有关的模型调用/工具步骤及条件边，复用已验证的单次模型适配与计算器，先解释状态字段、路由选择和停止边界，再准备集中参考与用户任务；不一次迁移整个Agent，不把已有原生Agent成功记录误记为LangGraph图已具备。用户已明确要求整理提交后继续：提交前重跑全量149 passed（2.32秒），diff检查通过；已本地提交97a69f9（顺序图/状态合并示例及测试），前置笔记、索引、README和路线另作docs提交，其哈希以Git历史为准。不推送，编辑器设置/独立练习/其他设计笔记保留。以下占位及失败记录保留为历史。
- 前次补写/注释核验：用户指出两个演示节点缺乏实际用途，并要求检查注释。已明确它们仅用于观察字段派生、跨节点读取及reducer，不承担问答/计算业务；Preview只是本地拼接输出。Codex按注释规范更新模块、状态类、三个函数和测试模块说明，不改用户核心语句，不把演示描述成实际业务能力。
- 前次目标实测1 failed（0.81秒），由build_preview_graph把中间连线误写为add_node导致prepare_question重复注册。另集中发现两个返回键写成trance而非trace，及轨迹标签prepare_questrion拼错。三类问题一次指出留给用户修正，不自动接管核心；本轮不重跑全量。仅在临时内存图用正确连线运行现有两个节点，正文派生正确但trace仍为[input]，证明误写字段没有更新声明的trace；这不是修改源文件或GREEN。注释调整不宣称测试通过，当前下一步用户统一修正API调用和字段/标签后再验。
- 用户前置反馈主干正确：节点便于复用/workflow；默认model_calls仍为1，未返回question保留。已澄清count只是中间业务节点、initial不是默认参数、Annotated元数据由LangGraph读取，以及调度/同次状态与跨次持久化的区别，不重考这些内容，进入实践。
- 新增app/services/langgraph_basics.py，Codex准备PreviewState结构：question/normalized_question/preview/trace，调用方初始化全部字段，trace使用Annotated[list[str], operator.add]。prepare_question、render_preview、build_preview_graph留核心占位供用户参考补写。契约为START→prepare_question→render_preview→END，先去两端空白，再基于新状态生成预览；原question保持，轨迹只提交本步名称，不带旧列表重复追加。纯本地同步图，不调用模型或改原生Agent/HTTP/数据库。
- 新增tests/test_langgraph_basics.py一条真实内存图测试，无fake模型/HTTP。输入question含两端空格、两个派生字段为空、trace=[input]；预期原问题保留、normalized_question清理、preview为预览：计算2+3、trace按input/prepare_question/render_preview追加，原始输入与deepcopy快照一致。测试通过最终状态检查节点执行顺序、部分合并、reducer及不直接修改输入；不为本单元加空输入/失败重试等新契约。
- 正确RED：目标1 failed（1.01秒），明确由build_preview_graph的NotImplementedError失败，无收集错误；全量1 failed / 148 passed（2.17秒），diff检查通过。当前下一步完整讲清状态字段、两个节点分别读写什么、builder注册/连接/compile与实际invoke，再提供三个函数完整局部参考，由用户补写并统一核验。无真实模型调用或自动提交，编辑器设置/独立练习/其他设计笔记保留。

### 当前主题：LangGraph前置知识（2026-11-04）

- 用户要求先讲明白前置知识。本轮使用project-guide的源码带读方式，对照真实agent.run_agent的局部数据、模型/工具步骤、if/for与错误边界，解释State/Node/Edge；补充函数对象、字典、TypedDict与Annotated/reducer，并区分StateGraph构建器、compile生成可运行对象及invoke/ainvoke的执行职责。不直接迁移整个Agent或新增模型调用。
- 本机安装langgraph 1.2.19，已读StateGraph的State→Partial<State>、默认LastValue字段更新、add_messages按ID合并等源码。纯内存探索实测：节点只返回model_calls更新时question保留、计数0→1，原输入字典仍为0；普通列表字段更新从旧列表替换为新列表，Annotated[list[str], operator.add]则追加。该节点只是演示计数，不算真实模型调用。并行写默认字段可能冲突，不将顺序更新规则推广为任意最后写入获胜。
- 新增notes/LangGraph前置知识.md并加入索引，记录每个新API/类型的来源、输入输出、构建与执行顺序、状态/长期记忆/持久化边界；我的理解待用户补充。正式学习路线顶部一处旧的“下一主题流式”已同步为该批后已完成流式，当前仍从本小节接续。
- 当前下一步：先完成前置讲解及一次默认字段更新的行为预测，再围绕不联网的最小顺序图给局部参考和用户任务；类型声明不冒充运行时Pydantic校验，compile不冒充执行或模型调用。先顺序图，后条件边/循环、checkpoint及人工确认。无新业务行为，不强造RED，本轮未重跑既有148 passed，不自动提交；编辑器设置、独立练习与其他设计笔记保留。

### 最新检查点：流式独立入口提交，接续LangGraph（2026-11-04）

- 用户明确要求整理提交，并指出stream入口尚未接入应用。范围已澄清：函数已经真实调用模型服务并接受离线/真实验收，当前仅供Python消费者；尚未接入/chat、浏览器展示、取消交互或流式持久化。阶段8完成指第一轮独立机制学习与验收，不表示主应用已完成LangChain迁移或流式产品接入。
- 用户已按参考补齐stream_langchain_reply。实测目标2 passed（1.12秒）、默认全量148 passed（2.07秒），diff检查通过；核心按async with/aclosing/async for/yield原样交付chunk，正常正文、stop及usage保留，中途超时前缀保留且异常传播，两个场景均仅一次请求并关闭资源。Codex仅清除一行末尾空白，不改变用户核心逻辑；参考实现不记为独立设计，测试GREEN不等于所有概念已完全掌握。
- 沿用用户此前明确确认的.env真实验收方式，Codex新增playground/langchain_stream_probe.py：固定合成三行短语，HTTP请求钩子只计数、最多一次，不读取响应正文；消费端逐个记录合成片段、到达时间及finish/usage，用+聚合，并用aclosing管理外层生成器；失败时记录类型和已有前缀，不记录密钥/上游异常正文或推理正文。报告保留执行时HEAD f6153cb及源文件指纹。
- 实际一次HTTP请求成功，收到73个片段，其中8个含正文；结果准确为青榆/流式/验收完成三行，收到stop及134 tokens（input63/output71）。约2.54秒是单轮观察，不是性能基准。报告playground/results/langchain_stream_probe_2026-11-04.json经Codex复核为reviewed_pass_synthetic_scope，非独立人工评审；指纹匹配，未含当前配置API Key。真实只测正常流，中断与关闭边界来自离线流测试；未实现工具流式执行、服务SSE端点或数据库接线。
- 限定独立静态复核检查streaming服务、对应测试及真实探针，未发现当前明确契约下有意义的问题。复核者未读.env、联网、执行测试或改文件；运行与报告复核由主流程完成。README、notes/README与对照笔记已同步。用户本轮明确授权本地提交服务/测试、真实探针/报告及文档，不推送；编辑器设置、独立练习及其他设计笔记不纳入。提交前再次全量148 passed（2.21秒），diff检查通过，真实报告指纹与当前源码一致；已本地提交1d29d95（独立流入口与中断测试）、069a93c（真实探针及报告）；配套文档另作docs提交，其哈希以Git历史为准。
- 阶段8以第一轮限定实现/验收完成收口：消息/模板、工具和循环机制、检索/严格RAG、项目模型契约、回调、离线同场景及真实合成对照、独立文本流均有对应证据。正式/chat仍用原生实现，预建Agent返回结构/预算时机等差异保留，不宣称全量业务迁移或生产就绪，也不把所有功能写成用户独立实现。
- 当前下一步进入阶段9 LangGraph，先学习State/Node/Edge如何对应原生Agent中的消息/调用记录、模型与工具步骤、继续/结束选择。首先核验本机已装版本和代表性源码，讲一个不联网的最小状态图与状态更新，给一次行为预测，再安排局部参考及用户任务；不重写整个Agent、不另起并行路线。之后依既有路线推进条件分支/循环与预算、checkpoint、人工确认及失败恢复，完整HTTP SSE仍在阶段10。

### 当前实现任务：单次模型流与失败前缀（2026-11-04）

- 用户正确预测多个片段仍是一次模型调用、中途超时不能算完整成功回答；其“应该不保留”已补充为：已交付前缀可以留在界面或内存作为未完成内容，整轮仍失败，不冒充成功最终回答或自动入库。不要求重答同一边界，进入参考补写。
- 新增app/services/langchain_streaming.py独立入口，复用build_chat_prompt；Codex准备_open_streaming_chain异步上下文管理器，为本次模型链创建并关闭HTTP客户端，cache=False/max_retries=0/stream_usage=True，不复用会aread缓冲响应的适配器钩子。stream_langchain_reply(message, history=None, *, system_prompt=...) -> AsyncIterator[AIMessageChunk]保留核心占位，由用户参考使用async with、aclosing和async for逐个yield原始chunk；不筛掉空content、不吞SDK异常、不收集成假成功结果。调用方提前停止时须关闭外层生成器，资源清理边界随上下文退出。
- 新增tests/test_langchain_streaming.py两条测试。offline_stream只替换客户端工厂，EventStream继承httpx.AsyncByteStream逐段产出模型上游SSE字节，真实SDK/框架解析成chunk；这与阶段10的本服务→浏览器SSE接线分开。正常场景先空角色片段，再计算结果是/437，再stop、空正文usage与DONE；检查首段文字在结束事件发出前可见、仅一次请求、消息/stream/include_usage、合并正文与usage、HTTP资源关闭。中断场景在计算结果是后抛ReadTimeout，检查APITimeoutError继续传播、消费者前缀仍在、最终usage未伪造、只一次请求且资源关闭。
- 正确RED：目标2 failed（1.42秒），全量2 failed / 146 passed（2.32秒），均为入口NotImplementedError，无收集错误，diff检查通过。另直接离线探索已写帮助函数：正常两段文字在finish_sent=False时到达，合并437结果/stop/12 tokens，异常分支为OpenAITimeoutError且前缀保留；两种探索均仅一次请求且关闭资源。这是帮助函数探索，不是用户核心GREEN。没有真实模型调用、生产SSE/数据库改动或自动提交。
- 当前下一步：完整说明AsyncIterator、yield、@asynccontextmanager/aclosing的来源与职责，给出替换核心函数体的完整局部参考；带读fixture的SSE编码、按需迭代与两条测试，再由用户补写，随后检查实际文件并运行目标/全量。保留既定LangChain→LangGraph→完整SSE的阶段顺序。

### 当前主题：框架流式接口的执行方式（2026-11-04）

- 用户确认进入下一步，开始主题6剩余流式接口。已核验当前HEAD f6153cb、工作区及本机BaseChatModel.astream、ChatDeepSeek继承的异步流实现和AIMessageChunk源码。astream提供异步迭代，SDK设置stream=True并逐事件解析；支持的模型会逐段产出AIMessageChunk。不能仅凭所有Runnable都有astream就认为每个组件都能实时输出，本轮所用ChatDeepSeek有实际流式实现。
- 本轮先带读ainvoke一次返回与astream异步迭代的区别、async for等待下一片段、消息片段不等于完整回答或固定一个Token，以及空content片段可能承载结束/usage信息。流中途失败时已交付片段与整次请求成功必须区分；先围绕片段数量/请求数量和前缀后失败做一次行为预测，再准备正常与中断的离线HTTP流、函数骨架和用户局部任务。
- 保持范围：先做Python侧单次普通文本模型流与消费，不接工具流式执行、HTTP SSE或数据库；现有模型适配器的aread缓冲钩子不直接复用。此前真实九组12次模型调用已在d119fbe保存，文档提交f6153cb；本轮未新增模型调用、生产代码或测试，也未重跑既有146 passed基线。编辑器设置、独立练习与其他笔记继续保留，不自动提交。

### 最新检查点：真实模型对照与本地提交（2026-11-04）

- 用户明确要求使用.env中的配置跑真实模型测试，再整理提交。Codex新增playground/langchain_live_acceptance.py，通过uv --env-file加载进程环境，不读取/打印配置文件内容或密钥；原生与框架适配各跑history/calculator/rag_facts/missing_phone四类问题，另跑独立预建Agent计算器，共九组。只发送脚本及固定fixture中的合成数据，真实配置/数据库/索引不改，计算器限定与意外MCP调用阻断均落实在脚本；全局最多27次模型调用。
- 实际运行一次完成，报告playground/results/langchain_live_acceptance_2026-11-04.json：12次模型调用、8217 tokens、约27.22秒。两种入口均准确复述青榆7314，实际请求calculator计算23*19并得到437；苍鹭5836及先rollback再继续抛出原异常分别引用service/recovery且ID合法；电话缺失均说明资料没有而未编造号码。预建Agent亦有真实工具请求和437结果。框架跨文档答案将两句合为分号表达，作为输出格式观察保留，不阻断事实/引用验收。
- 已逐条对照合成原文、回答、来源ID、计算器参数/轨迹及调用元数据，由Codex将报告标记reviewed_pass_synthetic_scope；非独立人工评审。源码SHA256与执行时工作区一致，报告保留执行前基线HEAD 3f1804d，不倒写后续提交版本。报告未包含当前配置API Key。原生/框架各5次模型调用，预建Agent2次，所有调用成功；SDK重试关闭，本轮无额外真实复验。
- 证据边界：RAG题共享由应用直接构造的上下文，此次未验证Embedding/检索、业务数据库、HTTP路由或部署；没有真实注入超时/非法参数，这些边界由已有离线测试证明。单轮小样本不证明所有输入等价、通用稳定性或性能。预建Agent仅单独计算器验证，未冒充项目AgentResult适配。新增脚本中make_cases负责合成输入，run及observed_generate执行并记录真实调用，calculator_only限定工具，预建Agent复用ModelCallRecorder；报告及笔记保留上述职责和边界。
- 提交前验证：默认全量146 passed（2.12秒），脚本编译、diff检查通过；限定独立静态复核检查脚本/适配器/两份测试及调用路径，未发现当前契约下有意义的问题。复核者未读取.env、联网、运行测试或修改文件；真实运行和逐题复核由主流程完成。
- 用户已授权本批本地提交：模型工具/上下文契约适配、共享离线验收、真实合成验收脚本/报告和文档分别保存，不推送。编辑器设置、playground/03_class.py及notes/设计复核-2026-11-02.md继续保留。已本地提交59df0e6（工具/上下文与Agent调用契约）、7c0e51e（共享离线场景验收）、d119fbe（真实验收脚本/报告）；本路线、README、索引及对照笔记另作docs提交，其哈希以Git历史为准。
- 当前下一步仍为主题6的框架流式接口。先讲ainvoke与astream、异步迭代和消息片段/最终结果的关系，再用正常及中断场景给参考和用户任务；完整HTTP SSE归阶段10。继续保持用户核心参考补写、Codex样板/验证和完整新增内容带读，不将已验证记为独立设计或全部掌握。

### 最新接续：共享场景对照完成，准备流式接口（2026-11-04）

- 用户确认继续集中对照。Codex新增tests/test_model_backend_contract.py：一份场景测试由backend_run fixture的native/langchain参数分别运行，再组合success/second-timeout/invalid-arguments三个scenario，共6例。两种模型入口共用真实原生Agent及计算器，只fake外部HTTP；本轮验收已有行为，不修改业务核心或为形式强造RED。目标6 passed（1.27秒），全量146 passed（1.87秒），diff检查通过。
- 同组验收检查输入参考顺序、历史/当前问题各一份、工具声明与call_id回传、原始工具参数、LLMResult元数据及AgentResult/部分失败异常。正常两次模型调用/两条成功记录；第二次超时两次请求/一条成功记录及LLMTimeoutError；参数非法一次请求/一条成功记录及JSONDecodeError。耗时只检查非负，不比较性能；底层SDK异常链与JSON序列化空白不要求逐字等同。预设响应不能证明真实模型选择能力或输出质量。
- 测试新增fixture的SimpleNamespace只替换原生llm模块引用的httpx对象，保留需要的异常类，避免修改SDK使用的全局AsyncClient。模型入口选择只在测试替换agent.generate_reply；同一run_agent管理循环，不将本轮验收写成预建create_agent已适配项目业务。每次真实HTTP请求才消费pending下一项，不由预设列表长度驱动循环。
- 已新增notes/LangChain与原生实现对照.md并加入notes/README索引，明确正式原生链路、原生循环+框架模型组合、预建Agent三种入口，以及工具JSON、计时、异常原因链、预算停止时机和非流式aread缓冲边界。主题5按本阶段独立机制对照及可复用模型适配的有限范围收口，不宣称所有输入等价、主路由已迁移、预建Agent业务契约已全量对齐或生产就绪。用户个人理解仅保留已有实际回答，其余待补，不把Codex验收记为用户独立测试设计。
- 当前下一步是主题6剩余的框架流式接口：先比较ainvoke一次返回与astream逐段产出，说明异步迭代、消息片段及最终结果的区别，预测产生部分内容后失败能保留什么；再核验本机接口、准备一个正常和一个中断场景、给局部参考供用户补写。完整HTTP SSE仍归阶段10。当前适配器aread会缓冲整段响应，流式入口应单独处理，不能套用后声称已有实时输出。本轮未调用真实模型，不自动提交或推送。

### 当前主题：Agent契约验证与参考上下文对齐（2026-11-04）

- 最新GREEN：用户已补齐memory_context/rag_context签名、参数转发及参考消息构造，实测目标10 passed（1.12秒）、全量140 passed（2.06秒），diff检查通过。两轮真实原生循环调用框架入口均携带同一份参考消息，返回两条LLMResult；第二次模型超时由AgentRunError保留第一条成功调用及LLMTimeoutError原因，参数非法由AgentToolError保留一次成功调用及JSONDecodeError。全部外部HTTP仍为fake，未读取真实记忆数据库或调用模型；参考输入不记为独立设计，测试通过不记为全部掌握。
- LangChain剩余范围明确为：主题5做共享固定场景的原生/框架结果与失败契约对照并解释已知差异；主题6完成框架流式调用入口与分块消费（回调已做）；随后整理阶段结论进入LangGraph。预计约2～3个集中单元，非固定对话轮数或截止承诺。完整HTTP SSE仍归阶段10；预建Agent的工具预算时机与业务返回结构差异需在对照结论保留，不将本轮原生循环组合写成预建Agent已完全迁移。用户本轮只要求核验与剩余量说明，不自动提交或新增下一主题代码。
- 用户已正确补写parse_tool_calls、原始content/工具请求读取及LLMResult返回。重新实测目标7 passed（1.21秒）、全量137 passed（1.88秒），diff检查通过；原始参数空白与None正文保留、工具声明/回传、非法参数留给工具层均已GREEN。未改用户核心，仅观察到错误文案Mssing少字母但不影响行为，不要求额外修正轮次；未提交推送。
- 下一小单元先验证原生run_agent与框架单次入口组合的项目契约。只在测试用monkeypatch.setattr(agent, "generate_reply", generate_langchain_result)替换模型入口，生产原生Agent、/chat及此前create_agent实现均不改。本轮不将该组合称为预建框架Agent的业务适配；预建Agent仍保留独立机制对照及预算差异。原生Agent已有AgentResult、AgentRunError及AgentToolError负责正常与部分失败记录，无需先复制循环。
- 新局部任务：用户给generate_langchain_result的keyword-only参数补memory_context=""及rag_context=""并转交帮助函数；帮助函数已添加这两个参数及reference_messages占位，用户参考构造Memory→RAG两条独立user参考消息。Codex已在新建模板的system后插入可选reference_messages占位，并在ainvoke传入；history/当前问题/额外交互的顺序保持，空参考不增加消息。参考内容由调用方准备，此单元不读取记忆数据库或执行RAG检索。
- 新增测试为同文件两个函数、三个场景，复用现有真实SDK与fake HTTP fixture。正常原生循环调用框架模型两次，真实计算器执行，检查每次模型请求均带Memory/RAG、历史/当前问题各一份，返回AgentResult含两条真实LLMResult。失败参数化分别预设第二次模型超时或第一次工具参数非法：预期AgentRunError携带一条成功调用及LLMTimeoutError原因，或AgentToolError携带一条成功调用及JSONDecodeError；分别仅有2/1次HTTP。不新增数据库或预建Agent断言，也不把预设工具请求视为模型选择能力。
- 前次正确RED：目标3 failed / 7 passed（1.14秒），三个新场景均由缺少memory_context参数的TypeError阻断，无收集错误；全量3 failed / 137 passed（1.86秒），diff检查通过。旧工具转换已通过，不能把新RED倒写为此前工具单元未完成。该次下一步完整带读临时入口替换、参考消息插入及三个场景，再提供签名/转发/参考列表三处局部修改供用户补写。无真实模型调用、不自动提交。

### 当前主题：工具请求与交互消息契约适配（2026-11-04）

- 用户正确预测：HTTP响应整体协议合法但工具arguments中的JSON非法，应保留一次成功模型调用，错误由工具处理层承接。继续主题5，不把框架invalid_tool_calls直接等同于HTTP模型调用失败，也不忽略这些工具请求。
- 本轮局部范围：generate_langchain_result新增tools及additional_messages，与原生单次调用前四个参数位置对应；本轮不新增memory_context/rag_context、不改原生Agent或/chat、不运行自动Agent循环。Codex机械接通输入参数、bind_tools(tool_choice="auto")、在新建模板末尾append可选MessagesPlaceholder；原始工具响应在现有HTTP钩子中aread缓冲并提取message字典，存入本次_HttpObservation.raw_message，SDK仍解析同一响应。原始消息不写日志/完整响应持久化；HTTP错误或畸形正文的提取失败不在钩子中向SDK伪装连接故障。
- 核心分工：已添加parse_tool_calls(message_data) -> list[LLMToolCall]占位，用户参考提取id、function.name及原始function.arguments，不调用json.loads；同时用户替换generate_langchain_result原文本限制，按raw_message转换工具请求、保留原始content（含None），返回真实tool_calls。未提供tools却收到工具请求仍拒绝；缺少协议字段仍按LLMResponseError处理。未自动替换用户核心判断或结果组装。
- 新增两条测试及RED：tests/test_langchain_adapter.py现有fixture支持按实际HTTP请求消费预设message迭代器。正常场景由测试显式调用两次适配器，中间真实execute_tool计算2+3，检查原参数空白保留、声明与auto传递、回传call_id、历史/当前问题各一份、输入列表不变；这不是框架或原生Agent自动循环。失败参数场景返回整体合法的HTTP200响应、arguments="{bad json"，预期先得到带usage的LLMResult，随后execute_tool真实抛JSONDecodeError；不在本轮声称已验证AgentToolError或中途失败记录封装。目标2 failed / 5 passed（1.25秒），全量2 failed / 135 passed（1.90秒）；两例均由现有普通文本检查抛LLMResponseError，属于新工具契约尚未接通的正确RED，diff检查通过。
- 帮助函数离线探索：仅直接运行已写帮助函数，正常工具请求→回传→最终文本的两次请求均完成，原始参数空白保留；非法参数时框架tool_calls为0、invalid_tool_calls为1，而观察对象保留HTTP200和原字符串。探索不是核心转换GREEN。无真实模型调用、自动提交或推送。
- 当前下一步：完整带读新增raw_message、aread/缓冲、模板append与optional、bind_tools及新增两条测试，提供三个明确修改位置供用户参考补写，再核验实际文件和目标/全量。GREEN后继续Agent结果与中途失败记录对齐，不重考已答对的模型/工具失败归属。

### 最新检查点与新会话接续（2026-11-03）

- 当前在main，用户明确要求复验并整理提交。已核对工作区、HEAD 9c046f9及origin=https://github.com/Galilieo/agent-lab.git；按近期feat/docs中文提交格式分批保存：69af168（异步检索与来源转换）、bf2b3f3（严格RAG与引用校验）、ead968d（普通调用结果与异常）；README、notes/README及本路线随后作docs提交，其哈希以Git历史为准。不推送；编辑器设置、playground/03_class.py和notes/设计复核-2026-11-02.md不纳入。
- 最新实测：用户已修正两处response拼写和条件末尾逗号，适配目标5 passed（1.12秒），全量135 passed（1.75秒），diff检查通过。超时/连接/429/格式错误四种失败转换与正常LLMResult均通过，成功状态实际来自HTTP钩子。与前检查点124条相比，本批新增检索2例、严格RAG4例、普通适配5例；人工向量/fake聊天和Embedding隔离真实模型，没有新增云端或真实Ollama验收。
- 限定独立只读复核：检查三份新增服务及三份对应测试，并对照原生检索/预算/引用/LLM契约与本地SDK源码，未发现当前明确契约下有意义的bug。复核者未改文件、运行测试、联网或读取真实.env；运行证据来自主流程。README与notes/README本地链接核验通过，不扩成生产就绪结论。
- 普通适配真实调用顺序：外层创建状态观察及计时→帮助函数创建客户端并注册响应钩子→模板/ChatDeepSeek/SDK→返回AIMessage或抛异常→外层组装LLMResult或转换项目异常。异常由raise ... from exc保留原因；适配层不决定本服务HTTP状态，现有路由未切换到框架。本次不新增核心实现或改变用户逻辑，参考补写不记为独立设计。
- 下一步仍在主题5：把工具声明、原始工具参数与结果/调用记录接到项目契约，明确Agent正常结束及中途失败的记录保留，再做同场景原生对照。首先带读原生LLMToolCall与框架tool_calls/additional_kwargs的差异，讨论适配边界后给局部参考和用户任务；不直接替换/chat或一次接管整个Agent。普通文本入口尚不接收tools/additional_messages/memory_context/rag_context，不应当作原生generate_reply的完整替身。主题6已完成回调，流式接口待开始；完整HTTP SSE仍在阶段10。
- 工具适配源码带读（提交后开始）：当前已安装集成的_convert_dict_to_message会将合法工具arguments字符串解析到AIMessage.tool_calls的args字典，将解析失败项放入invalid_tool_calls，并将content=None归一为""；该实现没有在additional_kwargs中保存原始tool_calls。因此不能照搬旧版本示例从additional_kwargs取原始调用，也不能只读合法tool_calls后丢掉解析失败项。先比较LLMToolCall的JSON文本与框架规范化结构，再预测“HTTP响应整体合法但工具arguments非法JSON”应归属的调用/工具失败边界。为保持原生原始参数及失败归属，后续考虑在已有HTTP观察处保留本次原始工具请求，只在内存转换，不记录正文或扩大日志。本轮只读源码和同步路线，未新增行为/测试，也未重跑135条既有基线，不提交新改动。
- 继续沿用导师提示词：用户核心参考补写，Codex准备样板和回归；所有新增helper/fixture/fake/断言均须解释。测试GREEN不代表全部理解或真实模型效果。以下为学习过程记录，其中旧RED、旧“下一步”和未提交表述属于当时状态，当前接续以本小节为准。

### 正在学习：普通模型调用的项目契约适配（2026-11-03）

- 最新补写核验：目标1 failed / 4 passed（1.23秒），正常分支因两处resopnse拼写产生NameError；同段条件末尾另有逗号，会把布尔表达式变成非空元组，即使表达式为False也被if判真。两种问题一次指出，留给用户修正；四种失败映射已离线通过，不能据此宣称正常返回已通过。本轮未重跑全量或改核心，diff检查通过，无真实模型调用。
- 用户正确说明SDK异常须转换为项目自定义异常，随后明确要求继续。局部范围为新增langchain_adapter.generate_langchain_result(message, history=None, *, system_prompt=...) -> LLMResult，先仅支持普通文本，不声明工具或替换/chat；原AIMessage教学入口保持不变。完整工具协议、AgentResult/部分失败记录、memory/rag参数及路由接线留在后续同主题，不把这个局部入口称为完整替换。
- 设计与执行安排：复用build_chat_prompt与真实ChatDeepSeek，Codex准备_HttpObservation及_invoke_observed_chat；每次独立HTTP客户端以异步response hook记录实际状态，禁止从AIMessage推断或将成功状态硬编码为200，关闭缓存及SDK重试。用户参考补写外层计时、结果/usage映射与异常转换；耗时包含客户端创建/关闭和框架处理，非纯网络耗时。超时先于连接异常判断；HTTP状态异常保留实际status_code；响应解析错误只有观察到HTTP响应时才转换，无响应的本地配置错误继续抛出。空字符串沿原单次调用契约保留，非字符串或意外工具响应拒绝，不吞掉工具请求。
- 测试计划与RED：新增tests/test_langchain_adapter.py，真实运行模板/SDK/HTTP响应钩子，只有传输为MockTransport。正常响应故意用201，检查实际状态、消息、Token、耗时与原history；参数化超时/连接/429/choices为null四种失败，检查项目异常、实际状态、cause及仅一次请求。目标5 failed（1.18秒），全量5 failed / 130 passed（2.04秒），均指向用户核心入口NotImplementedError，diff检查通过。另直接离线探索已写帮助函数，五种场景均只请求一次：AIMessage/201、OpenAITimeoutError/None、OpenAIConnectionError/None、OpenAIRateLimitError/429、TypeError/200；这是帮助函数探索，不是核心适配GREEN。无真实模型调用，不提交或推送。
- 当前下一步：完整讲解新增HTTP钩子、客户端别名替换和参数化测试，再由用户参考补写generate_langchain_result，检查实际文件并跑目标/全量；不代写核心，不把测试RED写成旧130条回归失败。

### 正在学习：框架严格RAG回答链（2026-11-03）

- 最新GREEN：用户已修正answer关键字、isinstance(response.content, str)及[引用未找到]标记。重新实测目标4 passed（1.20秒）、全量130 passed（1.71秒），diff检查通过；没有修改用户核心实现或调用真实模型。正常分支实际只交付预算内A片段，B引用被标注，原始AIMessage、usage及成功回调保留；空索引/零预算跳过回答HTTP，空白正文抛异常并保留真实响应。引用中括号是项目文本协议，合法性由本轮实际交付片段白名单判断，不由括号外形或磁盘存在性决定。测试GREEN不记为独立设计或全部掌握。
- 当前下一步：进入主题5的项目契约与原生对照，先比较AIMessage/消息轨迹与原生LLMResult/AgentResult，解释缺少的调用元数据和异常边界，再确定局部适配位置；不凭模型正文推断上游HTTP状态，不自动替换/chat。检索与严格回答单元适合整理为检查点，但仍需用户明确要求才提交；编辑器设置、独立练习与其他笔记保留。
- 前次补写检查（历史失败）：用户已写answer_with_langchain_rag。目标4 failed、全量4 failed / 126 passed；正常/空白响应分支由isinstance(response,context, str)的三个参数TypeError阻断，两个空资料场景由asnwer关键字拼错阻断；另从源码发现无效引用标记写成{引用未找到}而非[引用未找到]。三处集中定位，留给用户修正；retriver局部名虽拼写不同但引用一致，不是功能错误，未额外要求改名。该次尚未GREEN，通过基线为126 passed。
- 用户追问asyncio.run(run(...))：外层是Python标准库在同步pytest函数中启动/等待协程的入口，内层是offline_rag fixture中自定义的async辅助函数。可拆为scenario=run(seeded_index, " \n ", max_chars=250)，随后asyncio.run(scenario)；调用内层async函数先产生协程对象，外层驱动它运行，不是将RAG执行两次。该第二参数是模拟模型回答文本，真正用户问题由辅助函数传何时释放连接；预设空白回答用于检查无有效正文的异常。用户上一条引用替换追问仍一并解释：逐处替换无效角标并追加一次总体提示，不篡改原始AIMessage。
- 用户认可“只按实际交付片段检查引用”的边界。曾将检索理解为LLM自行读取超额片段，已区分普通聊天模型提出检索请求与严格路径应用先检索，以及TopK命中数量与字符预算筛选；应用检索和预算后仅交付入选片段，不依据模型是否“知道”某ID推断其生成原因。
- 本轮局部契约：answer_with_langchain_rag(message, persist_directory, history=None, *, top_k=3, max_chars=4000, callbacks=None) -> LangChainRagAnswer，复用已实现Runnable检索、原生build_rag_context预算、AGENT_SYSTEM_PROMPT和check_citations。检索/预算后无片段返回原NO_MATERIAL_ANSWER且response=None，不调用回答模型；有资料时使用RAG_PROMPT | ChatDeepSeek，仅传预算内上下文，保留history原值。非空字符串回答按原协议保留合法重复角标、逐处标注无效引用并追加一次提示，来源只返回实际合法引用且去重的片段。原始AIMessage单独保存于response，不被展示文本覆盖；空白或非字符串正文抛LangChainRagAnswerError并携带原响应，其他异常传播。原生/chat、记忆、SQLite和LLMResult适配不改，当前不接工具Agent。
- 分工：Codex新增langchain_rag.py的RAG_PROMPT、结果数据类、携带响应的异常类、documents_to_context机械转换帮助函数及核心函数占位；用户参考实现核心编排。documents_to_context仅接收本项目检索适配器产生且有完整metadata的Document，将其转回RetrievedChunk以复用原有整片预算，不复制预算算法；后续可评估更统一的领域边界，本轮不改原生结构。
- 测试与RED：新增tests/test_langchain_rag.py，真实临时Chroma/框架检索/预算/模板/SDK/引用检查，只fake问题Embedding与聊天HTTP。seeded_index准备短片段A和500字符片段B，max_chars=250只交付A；预设回答同时引用A/B，验证B无效、重复合法角标保留、原始AIMessage及Token/回调不丢、history不改。另验证空索引和零预算都跳过回答HTTP，以及空白正文报告异常仍保留响应；3个测试函数、4个场景。目标4 failed，全量4 failed / 126 passed（1.76秒），均为核心入口NotImplementedError，无收集错误，diff检查通过。本轮新增内容含fixture/fake、参数化、数据类及帮助函数必须完整带读。下一步用户补写核心后核验目标及全量；新检索与回答单元均未提交，无真实模型调用。

### 正在学习：异步检索适配（2026-11-03）

- 最新验证：用户已参考补齐retrieve_documents和build_notes_retriever，目标2 passed（0.77秒），本轮完整离线回归126 passed，diff检查通过。原生retrieve与真实临时Chroma配合fake问题嵌入，验证来源/原文位置/距离及排序保留、空索引跳过嵌入、故障传播；未访问真实模型。用户已说明ainvoke为框架统一方法、具体行为取决于实现，补充仅Runnable类组件通常提供该接口，Document等数据类型不提供。已解释RunnableLambda类与retriever变量名、传入search函数后由ainvoke调用的关系，不能将Runnable包装本身当作检索算法。
- 当前下一步：严格知识库回答的框架链。先明确Document→预算内RagContext→Prompt→Chat Model→引用检查的数据流，继续复用build_rag_context及既有来源ID/引用规则；检索TopK与实际交付来源不能混为一谈。空索引或预算后无片段仍在生成前短路，资料存在但不足以回答由模型说明。先围绕预算排除片段是否可被引用作一次行为预测，再给完整局部任务/参考、准备RED与用户补写；本轮未新增回答链或自动提交检索单元，不重做原生RAG、不替换/chat。
- 前一检查点四批提交为444ec2c、313f8bf、d44061a、9c046f9；新单元未提交或推送。用户已正确预测检索只返回资料，仍需组织参考上下文再交给聊天模型；补充检索会调用问题Embedding，但不生成聊天回答。本轮复用原生retrieve、BGE-M3/Chroma索引与来源ID，不重做阶段7，不直接替换/chat或知识库工具。
- 局部设计：新增app/services/langchain_retrieval.py的retrieve_documents(question, persist_directory, *, top_k=3) -> list[Document]，将原生RetrievedChunk转换为Document，正文保存在page_content，ID沿source::chunk_index，metadata保留source/chunk_index/start/end/distance；不strip、重排或把距离当置信概率。build_notes_retriever(persist_directory, *, top_k=3) -> RunnableLambda通过内部异步search绑定应用目录/TopK，只接收问题字符串，ainvoke时执行检索。选择Runnable适配原有async函数，不继承BaseRetriever、不承诺同步invoke或专属retriever回调事件，后续再组合预算/Prompt/模型/引用收尾。
- 分工与测试：Codex准备导入、签名、占位及tests/test_langchain_retrieval.py，用户参考补写两个核心函数。正常测试使用真实临时Chroma、人工向量及fake问题嵌入，验证Document原文含CRLF、ID/字符位置/距离及排序、只嵌入问题一次、索引条数不增加；第二条测试验证空索引跳过嵌入返回[]，有片段时Embedding故障继续抛出。输入向量人工指定，不证明语义检索质量；没有真实Ollama或聊天API调用。
- 正确RED：目标2 failed、默认全量2 failed / 124 passed（2.01秒），均为build_notes_retriever占位NotImplementedError，无收集错误，diff检查通过。最近全绿仍124 passed。当前下一步由用户参考补写适配与Runnable构建，再检查实际文件、目标和全量GREEN；本轮必须完整解释Document、RunnableLambda、内部函数捕获参数及两条测试的数据准备/真实执行/断言，不仅报目标或数量。

### 前一批本地检查点：单次调用、工具循环与回调（2026-11-03）

- 用户要求参考近期风格整理本地提交。本轮已分批保存 `444ec2c`（LangChain依赖、单次模型调用与消息模板）、`313f8bf`（计算器工具适配与参数校验）、`d44061a`（Agent工具循环与模型回调记录）。README、notes/README、导师提示词和本路线随最后一批文档提交同步，不推送；文档提交哈希以Git历史为准。
- 代码与测试：四个 `app/services/langchain_*.py` 和四个对应测试文件，共新增8例；整理后重新实测全量 `124 passed`（1.88秒），diff检查通过。只清理未使用导入、导入顺序和一处空格，未改用户的计算、模板、Agent或回调核心逻辑。依赖锁定主包1.4.7、core 1.7.2、DeepSeek集成1.1.1，新增23个依赖包，原有依赖版本未变。
- 独立只读复核固定范围 `a5d75afba66b76e94587c8a0b18500cf1bea5cc8..d44061a24777d1f2412dc7437b1975c79f32bb4e`，未发现当前范围内需修改的问题。复核者只读源码、测试、依赖与入口文档，没有运行测试、网络或模型；测试证据由主流程产生。只复核本轮有限学习实现，不将审查结果写成生产就绪。
- 能力与边界：单次调用/模板链、真实计算器工具、预建Agent循环、三次模型限额、成功和中途超时的模型观察记录已离线验证。原生 `/chat`、数据库、记忆与RAG主链保持原实现；框架版尚未提供完整 `AgentResult/LLMResult`、上游状态、异常HTTP映射和调用持久化适配。回调计时是模型步骤耗时；框架预算在下一次模型请求前检查，最后工具可能已执行；当前仅无外部副作用计算器。不据fake响应证明真实模型工具选择或真实接口效果。
- 教学记录：用户参考补写核心函数，Codex负责样板、验证与完整带读；不记为独立设计。已讲解新增fixture、回调、数据类及断言。测试响应列表由实际请求到来时 `next(pending)` 按需取用，不按列表长度驱动Agent；已用“准备2条响应、首条直接回答、实际只发1次HTTP”的离线例子校准，不能仅因测试通过就宣称全部理解。新增内容含测试都须按导师约定讲明白。
- 下一主题按阶段8继续 Retriever 与 RAG 链：先对照现有原生检索及片段结构，再讨论框架输入输出，不重做阶段7或自动替换主链。完整结果/失败记录适配和流式内容保留在后续安排。保留 `.vscode/settings.json`、`playground/03_class.py`、`notes/设计复核-2026-11-02.md` 未提交；本轮没有读取真实 `.env` 或调用真实模型。

以下为本轮学习过程记录；其中旧RED、占位及待实现表述保留为历史证据，当前状态以上述检查点与真实源码为准。

### 新会话接续（2026-11-02）

- 最新验证（2026-11-03）：用户已修正self._started_at、移除多余self,并将callbacks空值改为[]。目标4 passed（1.12秒）、全量124 passed（1.90秒）、diff检查通过；成功两次及第二次模型超时后的外部记录保留均已离线GREEN，未调用真实模型，不提交或推送。
- 当前理解卡点：用户将测试run(responses)理解为逐项执行响应列表；此处仍是核心控制流误区，不记为已理解测试或直接进入新主题。已使用真实offline_agent fixture做离线反例：预备两条直接回答响应，Agent只发一次HTTP并结束，第二项未使用。应区分整轮run一次、Agent按tool_calls决定模型请求次数、HTTP处理函数在实际请求到来时next(pending)取一条备用响应；不是响应列表长度驱动运行。先讲清这一方向，再进入Retriever与RAG链；不新增机械测试或闭卷练习。
- 回调补写失败记录（现已修正）：用户已写回调并接入config，但on_chat_model_start使用self.__started_at，初始化实际是self._started_at；框架记录AttributeError后继续，on_llm_end/on_llm_error再因缺失起点抛KeyError，records为空。目标2 failed / 2 passed，全量2 failed / 122 passed（1.99秒），旧循环测试通过；这次失败已不是未接线，不能记为GREEN。另发现错误回调有多余self,表达式（self,self.records.append），以及callbacks默认值写成{}而不是[]；前者在Python中会形成无用元组、不阻止append本身，后者当前空值分支未导致测试失败，但应按列表契约修正，不能误称它们是记录为空的根因。三处一次指出，核心修正仍由用户参考完成。
- 用户再次提醒所有新增内容必须讲明白，包括测试。导师提示词已进一步写明完整带读路径与覆盖范围。本轮暂停新主题，按外部recorder对象→callbacks配置→框架事件→run_id计时→记录对象→测试fixture与迭代预设响应→正常/超时断言及实际失败输出完整说明；区分测试预设的外部响应与真实记录生成。讲解及修正不等于GREEN或用户已掌握全部细节，不自动提交或推送。
- 当前下一步（2026-11-03）：用户已修正agent.ainvoke输入为messages列表，原Agent目标2 passed（1.11秒）、全量122 passed（1.57秒），消息回传及限额单元GREEN。依用户上一轮关心的调用日志，先穿插主题6的模型回调观察：执行时收集每次模型步骤的耗时、结果分类、可用Token数及异常类名；原生/chat、持久化与错误映射不改，完整LLMResult适配仍待接线前处理。模型步骤回调计时不等同于纯HTTP网络耗时，也不承诺上游HTTP状态。
- 本轮局部设计与分工：新增langchain_callbacks.py的ModelCallObservation数据类、ModelCallRecorder继承AsyncCallbackHandler及三个方法占位。on_chat_model_start按run_id保存perf_counter起点；on_llm_end从框架LangChainLLMResult.generations[0][0].message的usage_metadata记录成功；on_llm_error仅记录异常类名及耗时，SDK异常仍向外传播。每轮由外部调用方独立创建recorder，records保存在该对象中，不依赖Agent正常返回。Codex准备数据类/初始化/签名与样板，用户参考补写三个回调核心，并在agent.ainvoke的config中传callbacks。新增可选keyword-only callbacks参数已准备，当前旧调用兼容但尚未接入回调配置。
- 回调测试：复用test_langchain_agent.py的offline_agent，不重造HTTP样板；fixture仅增加callbacks透传和按预设httpx.RequestError模拟失败。正常场景检查真实两次模型回调记录和Token，失败场景检查第二次ReadTimeout由SDK抛超时异常，外部recorder保留成功及失败两条。已离线探索确认start/end与start/error分别按run_id配对，无真实模型调用。实测目标2 failed / 2 passed，全量2 failed / 122 passed（1.62秒），新两例均因records为空失败，是回调未接入的正确RED，旧循环回归通过，diff检查通过。用户关于外部recorder在异常后是否仍可读取的预测待回复，核心补写尚待；不自动提交或推送，原无关改动保留。
- 前次Agent检查（历史遗漏已修正）：用户已保存框架Agent实现，但agent.ainvoke({"messages": message})传入当前问题字符串，遗漏已组装的历史列表；框架接受字符串，循环与限额场景能运行，正常场景在第二次请求角色断言失败。目标1 failed / 1 passed、全量1 failed / 121 passed（1.87秒），diff检查通过。下一步用户改为agent.ainvoke({"messages": messages})，再验目标与全量；Codex没有代改核心行。
- 用户询问为何只返回消息轨迹、是否应该包含完整日志。已对照原生AgentResult/LLMResult及持久化源码说明：当前list[BaseMessage]是观察预建循环的独立学习入口，AIMessage可有usage/response metadata，但没有完整实现逐次耗时/状态/失败记录、原生异常携带已完成调用及数据库接线；限额异常仅带计数/限额，不含原生completed_model_calls。消息轨迹、结构化调用记录和运行日志职责不同，运行日志通过logger/回调/中间件采集，接回/chat前必须对齐原有结果和失败记录契约，不据当前实验宣称框架迁移完成。该问题属于设计说明，本轮未自动增加日志系统或更改核心返回契约。
- 当前下一步（2026-11-03）：用户参考补齐calculate_numbers与build_calculator_tool。实测工具目标2 passed（0.71秒）、全量120 passed（1.75秒），diff检查通过；复用真实原生参数模型和计算器，工具包装单元GREEN。用户概括为框架包装原生工具后供模型使用，已补充实际计算仍在本地原生函数中执行，模型只提出请求，框架负责声明/校验/执行/回传的接线，不把工具代码移到模型端。
- 已准备框架Agent循环单元：新增app/services/langchain_agent.py的run_langchain_agent(message, history=None) -> list[BaseMessage]占位，核心由用户参考实现；ChatDeepSeek配置沿用当前无自动重试，create_agent(model, tools=[build_calculator_tool()], system_prompt=...)创建预建循环，middleware=[ModelCallLimitMiddleware(run_limit=3, exit_behavior="error")]限制单轮模型调用，agent.ainvoke接收messages状态，返回状态中的完整messages轨迹。原生/chat不改，不接数据库/LLMResult；不使用线性prompt|model代替Agent循环。已读取本机API并以fake HTTP探索正常两次请求及持续工具请求后的框架异常，无真实模型调用。框架限额在下一次模型请求前检查，第三轮工具可能已执行，区别于原生预算耗尽后在工具执行前停止；当前仅无副作用计算器，不宣称二者边界等价。
- 新增tests/test_langchain_agent.py：offline_agent fixture通过迭代预设上游响应及MockTransport保留真实框架/SDK/计算器，正常检查第二次请求含工具结果和call_id、最终消息轨迹、历史不变；失败检查三次模型后抛ModelCallLimitExceededError且没有第四次HTTP。实测正确RED为目标2 failed、全量2 failed / 120 passed（1.92秒），均为新函数NotImplementedError，无收集错误，diff检查通过。下一步用户补写函数，再检查目标、全量并完整带读测试新增部分。不提交或推送；旧未提交配置、练习及其他笔记保留。
- 2026-11-03 工具适配开始时记录：用户在模板与Runnable/ainvoke/返回类型的带读答疑后要求继续，进入主题3的计算器工具适配。用户已正确描述链式执行顺序，补充通过本机源码说明ChatPromptValue及AIMessage由内部函数构造；不重复此前问题。新增app/services/langchain_tools.py的calculate_numbers(left, operator, right) -> int | float与build_calculator_tool() -> StructuredTool签名/导入/占位，核心由用户参考补写，复用既有CalculatorArguments与run_calculator，不重写计算规则。工具通过StructuredTool.from_function绑定函数、名称、描述及args_schema；工具ainvoke接收完整ToolCall时真实执行并返回带相同ID的ToolMessage，bind_tools仅向模型绑定声明不执行工具。后续再接框架Agent Loop，原生/chat和LLMResult契约不改。
- 本轮测试与证据：新增tests/test_langchain_tools.py，真实执行工具包装、参数模型和计算器，无模型/HTTP；正常用2+3检查ToolMessage正文为字符串5且call_001关联，失败用2÷0检查原有参数模型ValidationError，不伪装正常结果。关闭工具追踪，预设工具请求不代表真实模型会选工具。目标2 failed，默认全量2 failed / 118 passed（1.65秒），均为build_calculator_tool占位NotImplementedError，无收集错误；正确RED已确认。用户正确预测bind_tools暴露能力、具体使用由模型提出请求，应用必须检查参数；对“模型先处理一遍”补充模型可以自行推理但不构成可依赖的校验，CalculatorArguments才是实际执行前的应用校验。核心补写尚待；Codex负责样板、回归与完整带读，不提交或推送，原无关改动保留。
- 上一模板单元状态：用户已修正system_prompt键。实测模板与HTTP目标2 passed（1.03秒）、全量118 passed（1.50秒），diff检查通过；真实模板/Runnable/SDK加fake HTTP已验证，未调用真实模型。用户明确表示部分函数仍不理解，本轮按generate_langchain_reply的输入、ChatDeepSeek构造、build_chat_prompt/from_messages、MessagesPlaceholder、变量字典、prompt | model、ainvoke及ChatPromptValue→AIMessage顺序逐项带读；旧HumanMessage/SystemMessage/convert_to_messages导入当前未直接使用，暂未代为整理。代码与测试GREEN，理解答疑仍在进行，不因通过便进入下一主题或宣称全部掌握；不提交或推送。
- 前次补写检查（错误现已修正）：用户已参考实现build_chat_prompt与prompt | model接线。模板测试通过，HTTP接线测试因变量字典将system_prompt写成sytem_prompt，在本地模板校验阶段抛KeyError；尚未进入模型HTTP请求。实测目标1 passed / 1 failed，默认全量1 failed / 117 passed（1.80秒），diff检查通过；不能记为GREEN。下一步用户修正该键，Codex再核验目标与全量，不代改核心行。用户追问ChatPromptValue及测试中的old_key/literal，本轮结合实际本地格式化输出说明：ChatPromptValue保存已填好的messages，模板填充无需网络；链将它交给模型SDK转换为HTTP请求，测试仍用MockTransport；old_key/literal/unknown是输入值内的普通测试文本，不是本模板声明的新变量。该概念答疑不扩展新主题。
- 当前小主题：Prompt template、MessagesPlaceholder与Runnable组合。用户正确预测普通文本占位不能保留多条历史角色；已补充实际行为是将列表字符串化成一条HumanMessage，通常不会抛错，专用占位则展开保留角色。Codex已读取本机core 1.7.2相关实现，离线探索确认ChatPromptValue、RunnableSequence与缺少必填变量时的KeyError；探索只用fake模型，不代表正式链已接通。
- 局部计划：新增build_chat_prompt() -> ChatPromptTemplate，声明(system,{system_prompt})、MessagesPlaceholder(history)、(human,{message})；用户参考补写模板，并将generate_langchain_reply中手工拼messages及末尾调用替换为build_chat_prompt() | model后传三项变量。模型配置、AIMessage返回和异常传播沿现有契约，原生/chat不改。Codex已添加模板导入、函数占位与tests/test_langchain_prompts.py；新测试本地格式化并检查角色/顺序、输入值花括号原样保留和history不变，现有fake HTTP测试继续验证组合后的真实SDK请求与响应，不重复造传输样板。
- 本轮正确RED：合并目标1 failed / 1 passed，默认全量1 failed / 117 passed（1.71秒）；唯一失败是build_chat_prompt内NotImplementedError，无收集错误，diff检查通过。当前默认全量不是全绿，最近全绿基线仍117 passed。下一步由用户参考完成模板及链式接线，再由Codex读取实际代码、运行目标与全量、讲解新增测试与链路；不代写用户核心部分，不提交或推送。
- 上一单元收口：用户将最后一行修正为return await model.ainvoke(messages)。实测目标1 passed（1.05秒）、默认全量117 passed（1.79秒），diff检查通过。真实ChatDeepSeek与SDK配合fake HTTP验证系统指令/历史/当前问题的顺序和单份传递、原history不变、AIMessage正文与标准化usage；无真实模型调用。本轮代码与测试已GREEN。用户正确说明检查请求中的messages才能确认传入预期history；对“回答可能瞎猜”补充精确边界：本测试回答由respond固定返回，缺少历史也能收到相同正文，因此必须检查真实出站消息。已解释MockTransport来自httpx，SDK请求经其进入测试自定义respond，响应仍由真实SDK解析为AIMessage。用户随后指出Codex编写的测试也必须完整带读；此前仅解释MockTransport便宣布收口、准备进入下一主题，讲解不充分。本轮回到tests/test_langchain_llm.py，补齐配置覆盖与还原、respond记录请求/固定响应、两类HTTP客户端、create_model与模块引用替换、asyncio.run执行及各组断言的职责和证据边界；测试代码不改，不重跑已有GREEN，也不把讲解等同于用户已掌握所有细节。完整测试带读后，用户概括为用预设输入/响应和预期结果检查函数行为；补充区分：实际出站请求及AIMessage由真实函数和SDK运行产生，测试验证该场景下的输入输出契约，不证明所有场景正确或真实模型质量。测试带读与本单元理解按主干正确、具体边界补充后收口，不追加闭卷实现或重复检查题。当前下一步为阶段8的Prompt template与消息占位，继续保持用户参考补写核心、Codex处理样板与验证。LLMResult及错误适配在实际接线前处理，不把独立调用入口记为/chat框架迁移完成。
- 本单元失败记录：先由NotImplementedError确认正确RED；用户首次参考补写时将message字符串传给ainvoke，导致系统指令/历史未发送。目标1 failed、全量1 failed / 116 passed（1.70秒），失败位于出站消息顺序断言，无收集或配置错误。Codex按实际输出定位，用户修正；属于参考辅助实现与调试，不记为独立设计。
- 重试说明：用户询问为何max_retries=0。已核验已安装底层SDK默认重试上限为2（首次失败后最多再试两次，总共最多三次，是否重试取决于错误类别等条件），本轮显式设0用于保持原生无自动重试的对照条件；SDK对一次逻辑模型调用的HTTP重试不同于Agent Loop执行工具后再次请求模型。用户仅提问，未据此变更配置或提前实现阶段10的重试策略；主聊天调用记录当前也没有逐次记录SDK内部尝试。
- 本轮局部设计与计划：沿用原生配置，ChatDeepSeek设置timeout=60、max_retries=0，按SystemMessage→转换后的旧历史→HumanMessage组织输入，await ainvoke后返回原始AIMessage；不修改history，不执行工具或写库，SDK异常原样传播，不将其直接接回旧Agent的LLMResult契约。接口与调用顺序已确定，用户要求按原方式参与，Codex负责样板、运行和路线同步；不新增并行设计文档或形式确认。已通过先行离线API探索确认构造参数、POST路径与usage转换。测试保留真实ChatDeepSeek/SDK，仅以httpx.MockTransport替代外部HTTP，使用占位配置并关闭追踪；检查消息顺序、当前问题只出现一次、历史不变、正文与input/output/total tokens。正常回答预设不证明真实模型理解或接口可用，后续错误适配与LLMResult接线另行处理。
- 执行清单：[x] 核验源码及Git、[x] Codex准备测试和函数占位并确认正确RED、[x] 用户参考完成并修正核心函数、[x] Codex检查目标与全量GREEN并带读执行链、[x] 简短复述测试证据并补充MockTransport来源后收口。本轮没有真实模型调用、提交或推送。
- 最新接续进展：用户要求先安装框架后，已用 uv 添加 langchain>=1.4.7,<2 与 langchain-deepseek>=1.1.1,<2，实际安装主包1.4.7、core 1.7.2、DeepSeek集成1.1.1；锁文件新增23个包，原有依赖版本不变。安装后的离线全量116 passed（1.41秒），diff检查通过。ChatDeepSeek只用占位配置验证导入与构造；禁用追踪并阻断socket联网后，用GenericFakeChatModel实测ainvoke返回正文为空、含calculator请求的AIMessage，没有执行计算器或调用真实模型。此为框架消息/调用探索，不代表DeepSeek接口或生产链路接通。
- 用户正确说明未附带历史不能保证知道旧信息，并自行指出仍需Agent Loop、内部模型结果不一定直接返回用户；已补充区分“单次模型调用的完整结果”与“整轮Agent最终回答”。当前下一步：沿已安装ChatDeepSeek追踪消息到请求、响应到AIMessage的转换，用fake HTTP验证局部行为，再安排参考与用户参与；原生/chat保持现有实现，未完成模型调用替换、框架工具循环或RAG重构，不重复旧理解检查题。本轮只改依赖与本路线，不提交或推送，原无关文件保留。
- 阶段7的记忆与原生最小RAG已完成第一轮限定闭环。最近全量为116 passed；真实合成同题复验的12次HTTP、4道可答题事实及对应引用、电话缺失说明与问候不检索均通过。首次引用失败、连接中断和成功复验报告分别保存在 playground/results/，不必为了恢复上下文重跑付费模型实验。
- 本轮引用修订与验收材料已本地提交 a00e874，文档提交为a5d75af，不推送。交接时下一主题是阶段8 LangChain：先对照原生 llm.py 的 messages→模型请求→LLMResult，理解框架消息与Chat Model封装，再安排局部参考和用户参与；该交接检查点没有安装框架或自动改写原生链路。此后用户要求安装及当前进展见本节记录。继续保留LangGraph、SSE及开源产品设计学习，不改变主线。
- 正式进度以本路线为准，教学方式看 Codex学习导师提示词.md，记忆设计看 Memory-V1.1轻量分层长期记忆方案.md，注释看代码注释规范.md；先核验真实Git状态和源码。本文其后的RED、待实现、旧测试数均为历史阶段记录，不代表当前仍缺失这些实现。
- 用户写核心逻辑或参考修改，Codex处理样板、测试、运行与文档；每次补写后讲清用户代码及Codex新增支持部分。结合设计、执行链和证据教学，不把参考输入记成独立设计，不自动继续提交或推送。
- 编辑器设置 .vscode/settings.json、独立练习 playground/03_class.py 和单独设计复核笔记 notes/设计复核-2026-11-02.md 保留未提交，不纳入本次RAG检查点。真实记忆效果、关键词/语义工具竞争、知识权限、历史来源恢复、抗注入与部署网络路径等边界仍保留。

已确认方案为 [`Memory V1.1：轻量分层长期记忆方案`](./Memory-V1.1轻量分层长期记忆方案.md)。新会话先完整读取本路线、导师提示词和该方案，再核验真实源码与 Git 状态，不重新猜测已确认选型。

阶段 5、阶段 6 已完成第一轮。阶段 7 的 P0/P1 记忆最小闭环已离线收口（2026-10-29 全量 78 passed），随后文档处理与 Embedding 服务加入后，已完成部分增至 83 passed。2026-10-28 的 72 passed 是历史 P0 串联基线，保留作证据，不作为当前最新结果。已答过的模型调用、来源绑定、事务、连接归属、读取范围、合并顺序和读取失败边界不重问。

```text
当前小主题：阶段7已按限定范围收口，引用说明与验收材料已本地提交a00e874，入口文档及新会话接续随本检查点提交；离线全量116 passed。下一会话直接进入阶段8 LangChain，保留原生实现和固定题作对照，不重做RAG。
```

2026-10-31 上下文与模型接线分类提交：用户明确要求先整理提交两个已完成单元，并正确概括接线为每轮生成调用附加 rag_context；已补充其作为独立参考消息每次只出现一份，空值不附加，不写进 history。提交前再次验证默认全量93 passed、diff 检查通过；仅补充 rag_context 参数说明，不改变行为。已本地提交 ba2e33f（上下文预算与来源对应）、002c43d（Agent每轮RAG参考消息注入及测试），本段路线另作 docs 提交，不推送。尚未实现的程序引用校验、空资料上层兜底与 /chat RAG 接线不纳入本次提交；编辑器设置和 playground/03_class.py 继续保留未提交。本轮没有调用真实模型。

2026-10-31 参考消息接线 GREEN：用户参考完成 Agent/LLM 的 rag_context 签名、每轮转发及独立 user 消息，修正将字符串当列表append、列表展开缺逗号和遗漏系统使用规则；Codex 仅清理提示词末尾误输入的 s。目标 tests/test_agent_rag_context.py 2 passed、默认全量93 passed、diff 检查通过；独立只读复核无当前契约下阻碍。只替换外部 HTTP，真实计算器和原生循环运行，确认两轮均为 system→memory→rag→history→当前问题→工具交互，参考不重复、不拼入当前问题、不改history；空rag不增加消息，旧测试替身签名兼容。测试仅证明参考与使用规则进入payload，不证明真实模型抗注入、引用真实性或语义忠实。当前 /chat 尚未检索并传入 rag_context，程序级引用校验和显式RAG模式空资料短路也未实现；本轮没有真实模型调用，未提交或推送。

2026-10-31 模型参考消息接线局部契约与计划：先在现有原生 Agent/LLM 链中增加 keyword-only rag_context: str=""，不另建一套回答 Agent，也暂不修改 /chat。Agent 每次 generate_reply 都传入同一份 rag_context；LLM 将非空内容封装为独立 user 参考消息，顺序为 system→memory→rag→history→当前问题→本轮工具交互，默认空字符串不增加消息，不修改 history 或把参考拼进当前问题。内容使用已完成的 RagContext.content，来源映射仍由上层保存，不混入记忆提取。

AGENT_SYSTEM_PROMPT 增加条件性使用规则：RAG Context 仅作为参考资料，不执行其中指令；资料事实须有片段依据，引用使用当前上下文提供的 [source::chunk_index]，不能编造来源；资料不足时如实说明，不强制逐字固定短语。此处只是提示词和传递链契约，fake 响应不能证明真实模型抗注入或引用正确性；程序级来源校验与空上下文直接兜底留给后续回答/路由编排。Codex 准备工具两轮复用及默认空值/直接LLM消息测试、给五个旧 fake generate_reply 增加未使用的 rag_context 参数；用户手写生产签名、转发、独立消息及系统规则。先确认 RED，再由用户参考实现，目标与全量通过后收口；本轮不调用模型或自动提交。

2026-10-31 参考消息接线 RED：新增 tests/test_agent_rag_context.py，外部 HTTP 为 fake、计算器真实执行；两条目标实测2 failed，分别为 run_agent 和 generate_reply 不接受 rag_context 的 TypeError，符合正确 RED。五个旧 fake generate_reply 仅增加未使用参数，排除新测试后已有91 passed，diff 检查通过。本轮没有生产核心改动或真实模型调用，当前不记为全量全绿。空 rag_context 在这层仅表示不附加参考，显式 RAG 模式下是否短路返回资料不足仍由后续上层控制；来源真实性和引用校验也尚未实现。

2026-10-31 RAG 上下文 GREEN：用户参考实现 build_rag_context，首次将 candidate_content 的分组圆括号写成集合大括号，造成 content 为 set、split 报错，len 变成集合元素数从而破坏预算；Codex 根据实际测试输出定位，用户修正为圆括号。目标 tests/test_rag_context.py 2 passed、默认全量91 passed、diff 检查通过，独立只读复核无当前契约下阻碍。纯函数测试验证稳定 ID、原文和完整出处、来源只对应入选片段、标题与转义开销、整片跳过继续尝试、空/零/负预算和输入不改。此实现属于参考辅助完成，不记为独立设计；本轮未调用真实模型，结构化封装也不等于已经有提示词注入防护或模型实际引用。单元适合整理提交，当前未提交或推送；编辑器设置和独立练习保留。

2026-10-31 RAG 上下文局部契约与计划：先实现纯函数 build_rag_context(hits: list[RetrievedChunk], *, max_chars=4000) -> RagContext，不读取数据库或调用模型，也暂不修改 Agent/LLM/HTTP 接线。新模块 rag_context.py 的 RagContext(content: str, sources: list[DocumentChunk]) 保留最终参考文本和实际入选片段；sources 是提供给模型的材料，不等于模型已经实际引用。文本格式为 RAG Context: 换行加 JSON 数组，每项含稳定 id=source::chunk_index、source/chunk_index/start/end/text，便于后续引用追溯；不向模型灌入未经校准的距离作为可信概率。

预算沿用记忆单元的整条试装规则：按检索顺序处理，每次计算含标题/JSON/转义的完整字符长度；超限跳过整片并尝试后续项，禁止截断原文或让 sources 混入未进入上下文的片段。预算是本段参考文本的字符限制，不等于整个请求的 token 限制。无入选片段返回空文本和空来源，负预算抛 ValueError，零预算允许但返回空结果。结构化封装本身不能保证模型不执行资料中的恶意指令；后续还须系统使用规则和独立参考消息。计划为 Codex 准备数据对象/函数占位及两条上下文/来源/预算测试并确认正确 RED，用户参考实现核心，GREEN 后才记录完成；不提交未完成内容或调用模型。

2026-10-31 RAG 上下文 RED：已添加 rag_context.py 的 RagContext 与 build_rag_context 占位、tests/test_rag_context.py 两条测试。目标实测2 failed，均因 NotImplementedError，无收集错误；验证目标为原文/稳定ID/来源对应、整片跳过与JSON转义/标题预算、空输入及非法预算。仅纯 Python 数据，不调用数据库或模型；本轮不重跑全量，89 passed 为新增本单元前基线。核心实现留给用户，未提交新单元。

2026-10-31 TopK 检索提交检查点：用户明确要求将已完成检索单元单独整理提交后继续下一步。提交前再次验证默认全量89 passed、diff 检查通过；既有独立复核结论保留，无新增行为改动。已本地提交 788ddb8（问题向量 TopK 检索与片段还原，含检索结果模型和两条测试），路线验收另作 docs 提交，不推送。尚未实现的 RAG 回答上下文与路由接线不纳入本次提交；编辑器设置和 playground/03_class.py 继续保留未提交。本轮未调用真实模型，下一步先设计检索片段到上下文与来源引用的对应关系，再安排核心参考与测试。

2026-10-31 TopK 检索 GREEN：用户参考完成 query_chunks 与 retrieve，首次 query_embeddings 参数后漏逗号导致 SyntaxError、测试收集停止；Codex 依据完整输出指出该处，用户修正。目标 tests/test_rag_retrieval.py 2 passed、默认全量89 passed、diff 检查通过；独立只读复核无当前契约下阻碍。真实临时 Chroma 与人工1024维向量验证按 cosine 距离升序、TopK 截断/超过条数、完整原文出处及距离还原；fake Embedding 记录只接收当前问题，空索引不请求模型，空白问题/非正top_k拒绝，有索引时的嵌入错误继续传播。问答检索不调用 build_index 或重新嵌入文档，本轮没有真实 Ollama/云端请求。不将参考实现记为独立设计；TopK 不设置未经验证的相关性阈值，也不保证每条返回项能回答问题。单元已适合整理提交，当前未提交或推送；编辑器设置与独立练习继续保留。

2026-10-30 TopK 检索局部契约与计划：输入一个非空问题、索引目录和正整数 top_k（默认3），只嵌入当前问题，不调用 build_index 或重新嵌入文档。输出 list[RetrievedChunk]，每项复用 DocumentChunk 保存原文与完整出处，并增加 cosine distance；不把 Chroma 原始嵌套结果传给上层。距离越小越相关，TopK 是相对排序，当前不凭空设置阈值或承诺返回项都能回答问题。

模块分工：rag.py 增加 frozen dataclass RetrievedChunk(chunk: DocumentChunk, distance: float)；vector_store.py 增加 query_chunks(collection, query_vector: list[float], *, top_k=3) -> list[RetrievedChunk]，按 min(top_k, count) 查询一条问题向量并还原片段对象；rag_retrieval.py 增加 async retrieve(question: str, persist_directory: Path, *, top_k=3) -> list[RetrievedChunk]，先校验输入并打开已有本地笔记集合，空集合直接返回[]，否则调用 embed_texts([question]) 和 query_chunks。沿用 open_notes_collection：路径/集合尚不存在时会建立一个空集合并返回[]，不自动索引。存储层重复查询 count 用于实际查询时限制结果数；编排层预先检查空集合用于避免无意义的嵌入请求。错误不降级成“未命中”。

计划：Codex 准备数据结构、两个函数占位和 tests/test_rag_retrieval.py（人工向量+真实临时Chroma+fake Embedding），验证排序/数量/出处、问题单独嵌入、空索引/非法输入跳过嵌入及嵌入失败传播，先确认正确 RED；用户参考实现核心；通过目标和全量回归后更新完成状态。不调用模型或提交未完成内容，不接入回答路由。

2026-10-30 TopK 检索 RED：已添加 RetrievedChunk、query_chunks/retrieve 占位及两条检索测试。目标实测2 failed，完整输出均因 retrieve 的 NotImplementedError，属于正确 RED，无收集错误。测试只用人工向量、真实临时 Chroma 和 fake Embedding；本轮没有调用模型，也未重跑全量，87 passed 为新增本单元前基线。下一步用户参考实现数据库查询和结果还原、问题嵌入编排，再验证 GREEN；不自动提交。

2026-10-30 索引同步提交检查点：用户明确要求整理提交本单元。提交前重新验证默认全量87 passed、diff 检查通过；仅整理 vectors 赋值处的空格，不改变行为。已本地提交 41e89f3（笔记索引全量同步与过期片段清理，含两条索引测试），本段验收和路线记录另作 docs 提交，不推送。尚未开始的 TopK 检索实现不纳入本次提交；.vscode/settings.json 与 playground/03_class.py 继续保留未提交。本轮没有重新调用真实模型。

2026-10-30 索引同步 GREEN：用户参考完成 sync_chunks 与 build_index，自述大体理解设计。核验实现先读取/切分并成功生成整批向量，再打开专用集合，upsert 当前记录成功后按 ID 差集删除过期片段，空目录不请求嵌入并清空集合。目标 tests/test_rag_index.py 2 passed、默认全量87 passed、diff 检查通过，独立只读复核无当前契约下阻碍。临时文件、真实 Chroma 与 fake Embedding 验证文件缩短/删除/新增、空目录同步、返回片段数及 Embedding 失败时旧记录快照不变；没有实际 Ollama 或云端请求。不据参考实现和自述理解宣称独立设计，也不为本轮追加重复闭卷检查。upsert/delete 仍非一个事务，写库阶段失败可能部分更新，该限制不因模型失败保护已测而消失。此单元已适合单独整理提交，当前未提交或推送；编辑器设置和独立练习继续保留。

2026-10-30 索引同步局部设计与计划：用户正确判断 Embedding 失败必须保留旧索引，不能先清空。本单元采用显式调用时全量同步单一受信任笔记目录，日常问答不重建索引；暂无内容哈希增量优化。接口为 app/services/rag_index.py 的 async build_index(notes_dir: Path, persist_directory: Path, *, chunk_size=500, overlap=80) -> int，以及 vector_store.py 的 sync_chunks(collection, chunks, vectors) -> None。前者先读取/切片并成功生成整批向量，再打开专用 notes-bge-m3-1024-v1 集合并调用同步，成功返回本次片段数；空目录跳过 Embedding 并同步为空，缺失目录/读取错误/Embedding 错误向上传播且不动旧记录。后者读取现有 ID，复用 upsert_chunks 成功写入当前记录后，只删除 existing_ids-current_ids；片段编号与 source 继续沿用既有规则，不能用于混放多个目录或其他业务的共享集合。

该顺序只保证进入写库前的失败保留旧记录，不承诺 Chroma upsert/delete 之间的原子性或并发快照一致性；写入失败不继续删除，但可能已有部分写入，删除失败也会向上传播。当前是单进程顺序构建的学习基线。计划：Codex 准备正常同步（新增、缩短、删除、空目录）和 Embedding 失败保留旧记录的临时文件/真实 Chroma/fake Embedding 测试样板并确认正确 RED；用户参考实现两个核心函数；Codex 检查目标与全量 GREEN 后再更新完成状态。此计划尚未记为实现或验收，不提交未完成内容、不调用模型。

2026-10-30 索引同步 RED：Codex 添加 rag_index.py/build_index 和 vector_store.py/sync_chunks 占位及 tests/test_rag_index.py 两条测试。目标实测2 failed，均因 build_index 尚未实现；失败例捕获了 NotImplementedError（RuntimeError 子类），但错误消息不匹配预期的 fake Embedding 失败，根因仍是占位。无收集错误或真实模型调用，diff 检查通过。正常例串联初次建库、文件缩短/删除/新增及空目录清理，失败例比较已有记录快照，核心实现继续留给用户。本轮未重新运行全量，85 passed 为此前已完成部分的历史通过基线，当前新单元尚未 GREEN。

2026-10-30 正式存储层提交检查点：用户明确要求整理提交已完成单元后进入下一步。提交前重新核验默认全量85 passed、diff 检查通过；仅为配置字典参数补末尾逗号，不改变行为。已本地提交 bcde4cf（Chroma 片段持久化与向量入库，含跨进程测试），本段路线另作 docs 提交，不推送。提交范围不含尚未实现的索引构建/更新及正式检索模块；编辑器设置与 playground/03_class.py 保留未提交。下一步先解释为何 upsert 不会删除已消失的片段，再明确索引更新策略，核心代码继续由用户参考实现。

2026-10-30 正式存储层 GREEN：用户参考实现 open_notes_collection 和 upsert_chunks。首次输入中 ids 缺少等号、metadatas 重复赋值导致 SyntaxError，测试在收集阶段停止；Codex 根据完整输出集中指出两处，用户修正。实测 tests/test_vector_store.py 2 passed、默认全量85 passed、diff 检查通过；独立只读复核无当前契约下阻碍。测试使用真实临时 Chroma 和人工1024维向量，确认写入进程退出后可重新打开、原文与出处及 cosine 检索正确、重复 upsert 不增加条数、数量不匹配时零写入；本轮没有实际模型调用。此实现属于参考辅助完成，不记为用户从零独立设计；旧片段清理仍未实现，upsert 不等于完整文档同步。该单元已适合单独整理提交，当前仅更新学习路线，尚未提交或推送；编辑器设置与独立练习继续保留。

2026-10-30 Chroma 前置准备分类提交：用户要求先整理已完成的 Chroma 前置工作，并明确未完成内容先不整理提交。本轮核验 uv lock --check --offline、uv pip check 均通过；已完成部分离线83 passed（排除未完成的 tests/test_vector_store.py）、diff 检查通过。独立只读复核确认锁文件未升级既有包、探针不会被默认 pytest 收集、报告保留严格短语失败及人工语义复核，未发现提交阻碍。本地已提交 ed1da1b（Chroma 依赖、锁文件和索引忽略规则）、9d6d6fd（真实模型联调探针与实测记录），本段路线再单独提交；本轮没有重新调用模型或推送。app/services/vector_store.py、tests/test_vector_store.py 原样保留未提交，不把未实现占位记为完成；.vscode/settings.json 和 playground/03_class.py 继续保留。

2026-10-30 语义验收与正式存储层：用户确认真实探针负例按业务语义是正确回答，未输出固定短语只是更严格的格式条件，不因此阻断当前学习；保留原始严格检查结果与人工语义复核，不把逐字文案要求作为当前产品必需行为。本轮未再次调用模型。已核验当前 Chroma 1.5.9 的 get_or_create_collection/upsert 源码签名，运行 tests/test_vector_store.py 得到 2 failed，完整输出均指向 open_notes_collection 的 NotImplementedError，属于正式存储接线的正确 RED。下一步提供两个函数的完整局部参考，由用户实现；随后验证跨进程保留数据、重复 upsert 不增殖、数量不匹配拒绝，以及默认全量回归。不会代写核心、提交或推送。

2026-10-30 Chroma 环境和真实模型联调：本项目虚拟环境确认 chromadb 1.5.9 可导入。先使用人工 1024 维向量在临时目录写入两条记录，由独立写入进程退出后重新打开并检索，数量、原文、出处和 cosine 距离检查通过，未调用模型。用户随后明确要求加上真实模型和 API 测试；Codex 新增独立 playground/rag_live_probe.py，用三个合成 Markdown、现有 load_markdown_chunks 和 embed_texts、临时 Chroma 直接 API、现有 generate_reply 串联。通过标准 uv --env-file 复用现有配置，未输出密钥，未发送业务文档，也未代写 vector_store.py 的核心占位。

本轮实际结果保存于 playground/results/rag_live_probe.json：3 个片段生成 1024 维向量，2 次本地 Embedding 请求、2 次 deepseek-flash 聊天请求；API 均200，共640 total tokens，整段联调约5.51秒。正例检索首位为 notes/index.md，回答“青柠7429”并带 [notes/index.md::0]，三项严格检查均通过。负例回答参考资料未提供负责人联系电话并引用来源，没有编造号码，但系统要求逐字输出“资料不足”的检查为 false；保留原 status=failed，另附人工复核说明，不把语义拒答等同于逐字遵循，不通过放宽断言伪造全绿。该结果说明所测组件可协作，不能证明一般检索质量、确定性兜底、正式 /chat 接线或记忆效果。已完成部分离线回归仍83 passed（--ignore=tests/test_vector_store.py），diff 检查通过。探针和报告未提交，当前没有新增提交或推送授权。

2026-10-29 分类提交与独立复查：用户要求分批整理提交已完成内容。独立只读检查发现 Path.read_text 默认将 CRLF 规范成 LF，会破坏保留原文的字符位置契约；Codex 增加真实 CRLF 文件回归先确认正确 RED，再用 open(encoding="utf-8", newline="") 保留换行，已完成部分回归 83 passed（忽略工作区未完成的 tests/test_vector_store.py），diff 检查与独立复查通过。该边界修复由 Codex 完成，不记为用户独立实现。已本地提交 0fc4bd8（读取与切片）、f91cae8（Embedding 服务）、7e28d50（合成示例探索与实测摘要）；本次路线同步另作 docs 提交。编辑器设置、playground/03_class.py，以及正在准备的 Chroma 依赖、忽略规则、vector_store.py 和测试继续保留未提交；不推送。提交后的已完成代码默认回归应为 83 项，当前工作区新增 Chroma 测试处于未完成学习现场，不据此称整个工作区全绿。

2026-10-29 Embedding GREEN 与 Chroma 设计：用户参考完成 embed_texts，数量、维度和有限值校验及错误向上传播均保留；最新全量离线 pytest 82 passed、diff 检查通过，不代表本轮实际访问了 Ollama。用户接受 Chroma 本地持久化选型，故后续存储直接接入 Chroma，不再新增一套长期使用的内存持久化方案。选用 PersistentClient，集合 notes-bge-m3-1024-v1；显式 embedding_function=None，只接收已有 BGE-M3 向量；configuration.hnsw.space=cosine，查询返回距离=1-余弦相似度，越小越相关。每条记录保存 source::chunk_index 作为稳定 ID、text 作为 document、source/chunk_index/start/end 作为 metadata，以及对应 embedding；重复 ID 用 upsert 更新。upsert 本身不删除文档缩短后的旧片段，清理/重建规则留给索引编排，不承诺完整文档更新同步。已准备 vector_store.py 两个占位与 tests/test_vector_store.py，目标为写入进程退出后的重新打开与检索、重复写入不增殖，以及数量不匹配时拒绝写入；只用人工向量和临时目录，不调用模型。默认本地索引规划为 .cache/chroma/，已加入 gitignore。依赖安装与存储测试的实际结果待随后记录；不提交或推送。

2026-10-29 Markdown 读取 GREEN：用户参考实现 load_markdown_chunks，初次误将循环中文件检查写为 notes_dir，导致所有文件被跳过、返回空列表；依据真实失败输出定位后，用户改为 note_file。修正后全量离线 pytest 80 passed，diff 检查通过；文件筛选、顺序、UTF-8 原文与出处在临时目录中验证，尚未批量嵌入项目真实笔记。下一主题先明确 embed_texts 的文本输入/向量输出与片段按顺序对应，以及文档索引和在线问题嵌入的两条链，再由用户参考实现核心 HTTP 和解析，Codex 负责 fake HTTP 样板与验证。本轮未调用真实模型、未提交或推送。

2026-10-29 Embedding 服务 RED：用户准确说明文档向量应保存复用以避免每次提问重复计算；已澄清当前尚未接入向量库，先用内存片段/向量建立原生链路，进程重启后的持久化另行实现。新增 app/services/embedding.py 常量与 embed_texts 占位，以及 tests/test_embedding.py 的 fake HTTP 样板。局部契约：文本列表输入，按输入顺序返回向量；空输入不发请求；复用本地 BGE-M3 /api/embed，truncate=false；检查数量、1024 维和有限值，错误向调用方传播，不伪装为空结果；暂不接入聊天路由的错误映射。目标实测 2 failed，均因 NotImplementedError，正确 RED；测试不连接真实 Ollama/DeepSeek，最新全量通过基线仍为此前 80 passed。下一步用户参考实验代码实现函数，再运行目标与全量回归；不自动提交或推送。

读取契约见方案 6.1，已实现 database.load_memories 与 memory.merge_memories。用户正确预测了范围读取，参考实现并在提示下修正循环提前 return；属于参考辅助完成，当前单元收口，不强制额外独立重写。回答前接线现已完成，模型请求实际包含预算内选中的 memory 上下文，详见方案 6.3。

2026-10-28 本轮进度：用户正确说明 history 与结构化记忆的区别、同 key 会话覆盖、Core 优先及超限整条跳过；已澄清当前明确偏好覆盖历史默认，但不自动改写长期记录。局部选择/预算接口见方案 6.2。Codex 已准备 tests/test_memory_context.py 两条测试：目标 2 failed、全量 2 failed / 67 passed，均因缺少 build_memory_context 的 AttributeError 失败，无收集错误。生产代码未修改，下一步提供完整局部函数参考供理解与输入；此后仍需接线和模型请求证据，不记作完整记忆闭环。编辑器设置与独立练习保持未提交，未 commit/push。

2026-10-28 选择/预算 GREEN：用户参考实现完成 build_memory_context，目标 2 passed、全量离线 69 passed，diff 检查通过。Codex 仅清理一处行尾空格；normalized_message_message 名字重复但引用一致，不影响行为。用户已解释参数合法性、Core 先进入候选列表和超限跳过；补充 is_regular 检查负责限制普通记忆条数，不是重复保证排序。参考辅助实现不记为独立设计。结果仍未进入模型请求。

当前下一步：用户已授权并完成本地收口提交，功能与验收记录为a00e874，文档同批同步；新会话进入LangChain。原生最小RAG在本次限定范围收口，首次失败、连接中断与成功报告分别保留；不因一次通过宣称生产质量。应用控制能力、模型按需调用、严格路径空资料短路及精确引用白名单策略均保持原契约；默认pytest继续隔离真实模型，不扩展业务资料云端测试或推送。

2026-10-29 切分主题开始：用户已带读本地 API、HTTP Response、向量数量检查与余弦计算，准确说明下一片起点按 chunk_size-overlap 前进。本次探索脚本由 Codex 提供，不能记为用户独立实现；后续核心切分继续由用户参考实现，Codex 负责数据结构和测试样板。新增 app/services/rag.py 的 DocumentChunk 与 split_document 占位，字段为 source/chunk_index/start/end/text；start/end 对应原始字符串左闭右开字符位置，不先 strip 原文。切分约定为正 chunk_size、0<=overlap<chunk_size、空文本返回空列表、到达文末立即停止。新增 tests/test_rag_chunking.py，验证重叠、出处与到达文末不重复产生尾片；实测目标 1 failed，失败明确为 NotImplementedError，属于正确 RED，diff 检查通过。最近全量通过仍为此前 78 passed，本轮未重跑全量；新增占位使默认全量预计包含这一待实现失败，不记为当前全绿。下一步用户实现 split_document，再运行目标和全量回归；尚未读取实际 Markdown、生成新向量或接入生产聊天，未提交或推送。

2026-10-29 切分 GREEN 与读取 RED：用户参考实现 split_document，并理解 while 起点条件、min 限制终点及文末 break。实测切分目标 1 passed、全量 79 passed、diff 检查通过；另以本地调用检查空文本、短尾片和非法窗口参数，均通过，不记为新增持久化测试。之后 Codex 添加 load_markdown_chunks 占位与临时目录测试，读取契约为按文件名排序、仅本层普通 *.md、忽略符号链接与目录、UTF-8 读取、保留文本和 source 后调用现有切分；source 为目录名/文件名，当前仅用于单一笔记目录，chunk_index 在每个文件内从零编号。实测两个 RAG 目标 1 passed、1 failed，失败为新读取函数的 NotImplementedError，属正确 RED；79 passed 是新增读取测试前的全量基线，不表示当前默认全量已绿。下一步用户参考实现读取接线，目标与全量通过后再推进嵌入服务；未调用模型或提交推送。

2026-10-29 RAG 顺序补充（环境核对时的历史记录，嵌入探索结果见上）：用户已理解文档处理/切分/嵌入与在线检索两条链，指出应先完成向量模型和Ollama选型准备。后续以环境/模型→少量示例的本地Embedding验证→文档切分/索引→检索与回答接线推进；不要求用户先猜模型或下载已存在模型。复用已安装BGE-M3，单问题真实嵌入输出与排序已在随后探索中验证，更广泛中文检索质量仍未评测；不计为RAG已实现，不自动切换现有聊天模型。

2026-10-28 P1 管理数据库 RED：用户已正确说明同用户全部用户级/会话级同 key 删除，局部契约见方案 7.2。Codex 新增 tests/test_memory_management.py 两条真实 SQLite 测试，首次均因缺少 list_memory_records 失败。随后按 P1 分工补齐查看和抽取既有归属检查 validate_conversation_owner，保留原 load_memories 行为；当前全量 2 failed、72 passed，两例都因尚未定义 delete_memory_records 失败，查看结果和归属拒绝先行断言已通过。下一步给出完整删除函数参考，由用户结合已理解的 scope/scope_id/key 和用户会话子查询实现；尚未新增管理 HTTP 路由或删除真实数据库，未 commit/push 本轮 P1 改动。

2026-10-28 Prompt 接线 RED：接口与消息顺序见方案 6.3。Codex 新增 tests/test_chat_memory_context.py，真实 HTTP/SQLite/计算器配合 fake 模型 HTTP；两例分别因模型请求缺少 Memory Context、缺少记忆读取失败日志正确失败，全量 2 failed、69 passed。旧测试替身仅补 memory_context 参数兼容。当前核心接线尚未修改，下一步为 main.py、agent.py、llm.py 的局部参考输入与实际验证；用户已理解上下文由应用管理、无状态模型请求仍需携带上下文，不重复考问。

跨会话/改口更新已完成离线闭环验证；检查、删除与防重建按 P1 契约推进。优秀产品设计对照学习，以及心屿 Java 业务后端 + Python AI 服务方向保持不变。2026-10-28 用户提出整理当前部分提交，本次按本地提交处理，编辑器设置与独立练习排除；不自动 push。

2026-10-28 Prompt 接线 GREEN：用户参考代码完成 main.py、agent.py、llm.py 的读取与参数传递；目标 2 passed、全量 71 passed、diff 检查通过。测试真实执行 HTTP 路由、临时 SQLite 与计算器，fake 外部模型接口；证明两次模型请求各包含一份记忆/当前问题、顺序正确、系统使用规则入参存在、记忆文本不写入 message 表，以及缺失临时 memory 表时分类记录错误并保留成功聊天与调用记录。已有无记忆、归属拒绝和模型失败测试回归通过。实际模型遵循偏好优先级仍未验证；新增读取边界的简短复述待收口，不把参考实现记为独立设计。当前未 commit/push，编辑器设置和独立练习保留。

2026-10-28 接线复述与 P0 串联验收：用户准确说明空记忆正常、记忆读取故障可降级、归属冲突应由 chat 返回 409 并停止模型调用，读取失败边界已收口。Codex 新增 tests/test_memory_end_to_end.py：恢复真实提取器，只有外部模型 HTTP 为预设，真实执行 Pydantic 解析、来源绑定、持久化与 Prompt 注入。A 保存用户中文和会话级风格，B 新会话读取中文后改口保存英文，C 新会话读取英文，D 另一用户无记忆；同一 memory_id 更新、来源改为 B 的真实 user message、A 的风格不跨会话、保存反馈与历史一致、两次提取不混入五次主调用记录均通过。目标 1 passed、全量 72 passed、diff 检查通过。验收既有行为不强造 RED，未修改生产实现。P0 最小闭环已离线验证；不证明模型能自行正确提取或遵循语言要求，不将 Codex 编写验收记为用户独立测试设计。尚未 commit/push。

2026-10-28 测试带读收口与提交整理：已按真实源码讲解 fake HTTP 分流、observed 请求记录、A/B/C/D 串联、SQL 来源查询、消息切片断言与 JSON 编解码；用户正确说明 encode_extraction 用于避开 fake post 的 json 参数遮蔽模块，不要求重写整套测试。用户正确说明删除需同时限定 scope/scope_id/key；补充会话级 scope 拼写为 conversation，若需清除当前用户全部会话的同 key 偏好，还须通过 conversation.user_id 限定会话归属，不能只按 key 删除。P1 语义仍在设计讨论，未实现删除。提交整理仅修正导入/签名格式、更新职责和参数说明，不改变业务规则；本批包含选择预算、Prompt 接线、三份新增测试、旧替身参数兼容及学习说明，不含 .vscode/settings.json 与 playground/03_class.py。

2026-10-29 P1 数据库 GREEN：用户参考实现 delete_memory_records，首次测试因函数名误写 delete_memory_rocords 两例 AttributeError；核对完整函数后指出同一命名问题，用户修正。实际目标 2 passed、全量 74 passed、diff 检查通过。真实内存 SQLite 验证查看原始范围、局部删除恢复用户默认、重复删除为 0、调用方 rollback、同用户全部范围同 key 删除、其他用户/其他 key 保留、归属拒绝及匿名只操作本会话；message 历史保留。用户已解释三种删除范围，不再重复考问。管理 HTTP 与删除后聊天串联未实现，本轮 P1 未提交，编辑器设置和独立练习保留。

2026-10-29 本地提交检查点：用户明确要求先整理提交当前 P1 数据库单元。范围为 app/database.py、tests/test_memory_management.py 和两份路线/方案文档；仅整理删除函数的标点、空格与 SQL 排版，不改变业务规则。HTTP 查看/删除接线和删除后的聊天验证仍为下一步，不记作 P1 全部完成。排除 .vscode/settings.json 与 playground/03_class.py，本次不推送远端；实际提交记录以 Git 历史为准。

2026-10-29 P1 HTTP GREEN：按既有 P1 分工，Codex 实现请求/响应 schemas 及 POST /memories/query、POST /memories/delete。测试先因路由404正确 RED（3 failed），实现后仅串联测试将5次聊天误计为6次，检查完整输出后修正测试计数；目标3 passed、全量77 passed、diff检查通过。真实临时SQLite与HTTP/fake模型验证保存/查看/删除已提交、重复删除0、错误归属409、缺失会话400、非法输入422、删除commit失败503且rollback保留记录；旧保存消息保留在history，但提取只看新消息并skip，后续新会话无Memory Context；重新明确保存后恢复注入。只验证顺序执行下不自动重扫旧消息，不保证并发在途提取或真实模型准确性。HTTP样板由Codex实现，关键代码带读待收口；管理操作未添加自然语言删除分支，当前服务仍无新增身份认证。本轮未提交，编辑器设置和独立练习保留。

2026-10-29 HTTP 检查修正：独立检查发现管理请求自动 strip ID，而 ChatRequest 原样保留，可能操作到另一组不带空格的既有 ID。新增两个相似 ID 并存的测试先确认错误命中 RED，随后移除管理 ID 的 strip，沿用聊天标识符语义。修正后 HTTP 目标4 passed、全量78 passed、diff检查通过；不改已有保存 ID。独立检查无其他阻碍问题。此缺陷定位、测试与修复由Codex完成，带读时可作为契约一致性实例。

2026-10-29 记忆收口与提交：用户准确概括新路由为输入校验、连接、数据库调用、异常处理和返回的常规接线；已补充提交后返回成功及管理故障不能伪装空结果的边界。用户明确要求整理提交后开始 RAG。本次提交范围为 main/schemas、HTTP 管理测试及旧管理测试排版、路线与方案说明，不含编辑器设置与独立练习，不自动 push；实际提交以 Git 历史为准。记忆 P0/P1 仅按已测最小闭环收口，未访问真实模型。原生 RAG 首主题仍是设计与带读，尚未新增 RAG 实现。


2026-11-02 固定问题与真实模型首次验收（尚未通过）：Codex 添加 playground/fixtures/rag_acceptance.json 和 playground/rag_acceptance_probe.py，使用4份合成Markdown、临时SQLite/Chroma、真实本机BGE-M3与已配置deepseek-flash，经进程内TestClient调用正式 /chat。只临时排除关键词MCP工具，避免读取真实项目笔记；普通计算器/时间及按配置启用语义工具保持原生实现，不改真实.env或索引。独立检索观察将4道可答题的预期片段全部召回Top3；没有据距离设阈值或把相似度当正确率。

关闭/开启知识库各6题，共12次HTTP均200、17次聊天模型调用、15598 tokens，本轮约43秒（单轮观察，不是性能基准）。关闭知识库的资料题均明确缺少材料；开启后4道可答题事实正确，5道资料题均主动语义检索，电话缺失题未编造号码，问候不检索。每例均有2条消息落库，调用条数与观察一致；本探针只检查持久化条数，不单独宣称已比对每条保存正文。

关键失败：批次标签、超时、跨文档、电话缺失4例把真实 notes/service.md::0 等ID写成 source::notes/service.md::0，校验器正确标注未知引用；恢复流程题引用合法，但加入无关做菜资料说明，简洁性不足。事实正确与HTTP成功不能覆盖引用失败。工具描述的 [source::chunk_index] 可能被误读为固定前缀，这是原因推断，待说明修订后对照；不修改校验器白名单，不增加强制拒答或重试。结果 playground/results/rag_acceptance_probe.json 已逐条由Codex对照原文、答案及工具轨迹复核，状态 reviewed_changes_required，非独立人工评审。首次记录保留；脚本新增 --output 便于后续复验另存，不覆盖失败证据。

本轮生产实现未改；仅新增验收样板、合成材料/报告，修正历史组件探针说明，并同步路线。实际默认全量116 passed、脚本编译与diff检查通过；没有下载模型、使用业务资料、提交或推送。原生RAG尚不能收口：用户下一步参考修改工具描述中的引用示例，再用相同问题另存复验；实测通过后才更新阶段状态。小样本不证明通用质量、模型抗注入、多租户权限、来源历史恢复或真实记忆效果，且尚未测试关键词/语义工具竞争及部署服务器的网络路径。


2026-11-02 引用说明修订与真实同题复验通过（限定范围）：用户参考修改 app/tools.py 的语义工具说明，明确把返回id原样放入方括号，并给出 notes/example.md::0 → [notes/example.md::0] 的具体例子；Codex仅补回替换时遗漏的“无可用片段时可调整查询或说明资料缺失，不编造知识库来源”原句。没有改变检索、ID生成、引用白名单或收尾算法，没有加入自动修正重试。

首次复验在关闭知识库的第二题发生模型API连接错误，HTTP503；脚本按既定策略停止，结果另存 playground/results/rag_acceptance_recheck.json，不代表引用修订失败。该次尝试2次聊天请求，其中1次成功（726 tokens），失败调用usage未知；没有猜测网络根因或修改网络/模型配置。随后仅重跑一次完整同题验收，另存 playground/results/rag_acceptance_recheck_2.json：12次HTTP均200、17次模型调用、16172 tokens，约39.24秒；真实BGE-M3索引4片，4道可答题的独立Top3预期来源召回均为1.0。

Codex逐条对照合成原文和实际回答：关闭知识库的5道资料题均说明缺少资料，不编造事实/来源；开启后5道均主动语义检索，4道可答题事实正确且引用对应来源，跨文档两条结论分别指向service与recovery。电话缺失题如实说明、未编造号码，允许重复合法角标；问候不检索、不引用。5道资料题无无效ID（首次运行4道），本地断言确认响应中每个来源均实际检索过、id与source/chunk_index一致、text等于合成原文[start:end]；各例2条消息、落库调用数与观察一致。跨文档仍有简短额外说明，电话题仍有重复解释，作为输出质量观察，不扩大为本轮功能修复。

成功报告状态 reviewed_pass_synthetic_scope，复核由Codex执行，非独立人工评审。说明修订与改善同时出现，单轮随机模型输出不证明因果、稳定准确率或性能；仍排除关键词MCP工具，使用进程内TestClient，不代表部署网络、多租户知识权限、抗注入、历史来源持久化或真实记忆提取/偏好遵循效果。实际离线全量116 passed、diff检查通过。原生最小RAG按该学习范围完成第一轮，当前准备解释与提交检查点，不把参考修改记作用户独立设计或新增生产经验；只有用户明确要求才提交，不推送，编辑器设置、独立练习与其他来源设计复核笔记保留。下一主题按既定路线进入LangChain，用同题及原生链路作机制对照。


2026-11-02 收口提交与新会话交接：用户明确要求整理提交并更新文件，准备换会话。核验main与原HEAD bbba4ee、工作区及远端后，按限定范围完成本地提交a00e874（引用格式说明、固定合成题、验收探针、首次失败/连接中断/完整复验记录及历史探针职责说明）；README、notes/README与本路线作为后续docs提交，不推送。README已从旧51条测试与未接通记忆的描述同步为阶段7第一轮收口、116 passed、下一主题LangChain；本节提供新会话接续，导师约定与记忆设计保持原职责。

提交前限定只读复核发现：仅移除工具声明不足以保证探针不读取真实笔记，模型意外返回未公布search_notes时原生分发仍可能进入MCP。仅在验收脚本增加reject_keyword_search守卫并替换该执行入口，生产Agent不改；离线用真实run_agent/fake生成返回该名字，确认在MCP读取前由AgentToolError阻断并保留一次已发生调用。三份历史报告均无search_notes调用；守卫是提交前后加的离线保障，不倒写成历史真实运行已包含此保障，也不为此追加云端实验。最终限定复核无阻碍，复核者只读未运行测试；提交前主流程实际全量116 passed（1.39秒）、脚本编译、文档本地文件链接与diff检查通过。

本次保留 .vscode/settings.json、playground/03_class.py、notes/设计复核-2026-11-02.md 未提交，未读取或提交真实.env。新会话以第14节接续：阶段7不重做，先读已有llm请求链再开始LangChain机制对照；核心业务仍由用户参考参与，Codex负责样板与验证，不因本轮提交授权自动提交后续新功能。
