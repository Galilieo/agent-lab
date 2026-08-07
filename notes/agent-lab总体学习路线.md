# agent-lab 总体学习路线

> 文档角色：这是个人整体学习路线（技术栈主线）中 Python / FastAPI / Agent 部分的详细子路线，不是另一条并行总路线。
>
> 维护位置：本文件是 agent-lab 项目路线的唯一正式版本，与代码和测试一起更新。
>
> 最近核验：2026-08-07。

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

## 2. 当前进度

| 阶段 | 状态 | 完成标志 |
| --- | --- | --- |
| 1. Python 必要基础 | **已完成第一轮** | JSON、推导式、uv、异步、pytest 已做基础练习 |
| 2. 读懂现有 agent-lab | **已完成第一轮** | 能解释核心文件和当前请求链 |
| 3. FastAPI 请求链 | **已完成第一轮** | 完成请求、校验、响应、异常和测试 |
| 4. 真实 LLM 调用 | **当前进行中** | 完成异步单轮调用和日志 |
| 5. SQLite 与多轮对话 | 待开始 | 会话可持久化、恢复和隔离 |
| 6. 原生 Tool Calling 与 Agent 循环 | 待开始 | 不依赖框架完成工具闭环 |
| 7. 轻量记忆与原生最小 RAG | 待开始 | 记忆与检索来源可追踪 |
| 8. LangChain | 待开始 | 用框架重构已完成的调用、工具和 RAG |
| 9. LangGraph | 待开始 | 完成有状态、分支、循环和人工确认 |
| 10. SSE、评测与工程化 | 待开始 | 可流式、可测、可追踪、可部署 |
| 11. 迁移到心屿 | 待开始 | 成熟模块进入真实业务项目 |

### 当前代码基线

已经存在：

- `app/main.py`：FastAPI 应用、`GET /health`、模拟 `POST /chat`。
- `app/schemas.py`：Pydantic 请求与响应模型。
- `app/config.py`：环境变量配置对象。
- `app/services/llm.py`：异步 LLM service 边界，当前仍返回占位结果。
- `tests/test_health.py`：TestClient 基础测试。
- `pyproject.toml`：Python、运行依赖、开发依赖和 pytest 配置。
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

尚未存在：

- 真实模型请求、响应解析、超时和上游错误处理。
- SQLite。
- 多轮会话。
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

## 6. 阶段 4：真实 LLM 调用

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

## 7. 阶段 5：SQLite 与多轮对话

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

完成标准：不用 LangChain / LangGraph，也能写出并解释最小 Agent 循环。

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

阶段 2 源码走读和阶段 3 FastAPI 请求链均已完成第一轮，当前进入阶段 4：

```text
下一小主题：为 LLM service 准备原生异步 HTTP 调用
```

具体范围：先把 `httpx` 明确为运行依赖，再在现有 service 边界内组装 Base URL、认证请求头、模型名和 `messages`；继续保持 Key 不进入源码和 Git，不提前学习 SQLite、Tool Calling、RAG 或框架。
