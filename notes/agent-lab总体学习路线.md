# agent-lab 总体学习路线

> 文档角色：这是个人整体学习路线（技术栈主线）中 Python / FastAPI / Agent 部分的详细子路线，不是另一条并行总路线。
>
> 维护位置：本文件是 agent-lab 项目路线的唯一正式版本，与代码和测试一起更新。
>
> 最近核验：2026-08-14。

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

## 2. 当前进度

| 阶段 | 状态 | 完成标志 |
| --- | --- | --- |
| 1. Python 必要基础 | **已完成第一轮** | JSON、推导式、uv、异步、pytest 已做基础练习 |
| 2. 读懂现有 agent-lab | **已完成第一轮** | 能解释核心文件和当前请求链 |
| 3. FastAPI 请求链 | **已完成第一轮** | 完成请求、校验、响应、异常和测试 |
| 4. 真实 LLM 调用 | **已完成第一轮** | 异步单轮调用、错误边界、安全日志和 Token usage 已验证 |
| 5. SQLite 与多轮对话 | **当前进行中** | 会话可持久化、恢复和隔离 |
| 6. 原生 Tool Calling 与 Agent 循环 | 待开始 | 不依赖框架完成工具闭环，并理解 Structured Output 与 MCP 的位置 |
| 7. 轻量记忆与原生最小 RAG | 待开始 | 记忆与检索来源可追踪 |
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

日志精确条数、单个日志字段、缺少 usage 时的具体日志文本、所有异常响应字段组合、跨会话组合外键排列、索引字段顺序和未提交重连等细粒度测试已有部分可以继续保留作为回归保护，但不要求用户全部从零手写，也不再按同样密度新增。重复的 `FakeAsyncClient`、会话/消息插入等样板默认由 Codex 处理；明显影响阅读时再单独抽取 fixture/helper，不让测试重构挤占 Agent 主功能学习。

### 当前代码基线

已经存在：

- `app/main.py`：FastAPI 应用、`GET /health`、真实异步 `POST /chat`，并将 LLM 读取超时映射为 `504`。
- `app/schemas.py`：Pydantic 请求与响应模型。
- `app/config.py`：环境变量配置对象。
- `app/database.py`：SQLite 连接入口，为每个连接开启外键，并初始化 `conversation`、`message`、`model_call` 三表结构；组合外键保证模型调用引用的请求/回复消息属于同一会话，`load_recent_messages()` 按会话读取最近消息窗口并恢复为模型上下文正序。
- `app/services/llm.py`：原生 `httpx.AsyncClient` 异步 LLM service，负责组装请求、调用 DeepSeek OpenAI 兼容接口、提取回答，以及转换超时、连接、上游状态和非法 JSON 异常。
- `tests/test_database.py`：使用内存 SQLite 和 pytest 临时文件验证连接外键、三表写入、模型调用重试、失败调用无回复、无效外键、跨会话消息引用拒绝、消息历史稳定排序与最近消息窗口，以及提交和未提交数据在重新连接后的差异。
- `tests/test_health.py`：TestClient 请求校验、业务异常、LLM 正常返回、超时、连接失败、上游状态错误和非法 JSON 映射测试。
- `pyproject.toml`：Python、运行依赖、开发依赖和 pytest 配置；`httpx` 已是运行依赖。
- `playground/`：JSON、推导式、异步和 pytest 的第一轮练习。

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

尚未存在：

- SQLite 固定文件路径配置与 `POST /chat` 接线。
- 消息历史尚未接入 `POST /chat` 和模型上下文。
- Tool Calling。
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

## 7. 阶段 5：SQLite 与多轮对话（当前进行中）

学习：

- `conversation`、`message`、`model_call` 表。
- 主键、外键、索引和事务基础。
- 根据 `conversation_id` 读取历史。
- 上下文裁剪、最近消息窗口和摘要。
- 数据访问层与 API 层边界。

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

- 从历史对话提取结构化用户信息。
- 保存记忆来源和更新时间。
- 只注入与当前问题相关的记忆。
- 支持修正和删除。

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

阶段 5 已完成逻辑数据模型、SQLite 连接、三表结构、重试关系、跨会话外键隔离、稳定历史与最近消息窗口查询、最小历史读取函数，以及文件持久化与重新连接恢复：

```text
下一小主题：让 LLM service 接受消息历史
```

具体范围：以当前 `generate_reply(message: str)` 和固定 `messages` payload 为锚点，为 service 增加接收既有 `role` / `content` 消息历史的最小参数边界，并保证 system message、历史消息和当前 user message 的顺序正确。只改造一条现有 fake HTTP client 测试观察上游 payload，不新增生产级测试矩阵；本轮不配置 SQLite 固定文件路径，不在 `POST /chat` 中写入消息，也不实现完整 CRUD。完成后再把 `load_recent_messages()` 接入路由的数据读取链。
