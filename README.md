# agent-lab

用于学习和验证大模型调用、多轮对话、Tool Calling、记忆、RAG、SSE 流式输出等 AI 应用开发能力。

> agent-lab 是学习与验证仓库，xinyu 是后续承接成熟能力的正式项目。这里优先保证理解原理，不追求一开始就做成完整产品。
>
> 当前进度（2026-11-03）：阶段 5～7 已完成第一轮最小闭环，阶段 8 LangChain 进行中，当前离线全量为 `135 passed`。框架单次调用、模板、计算器 Agent、回调、检索和严格 RAG 已独立离线验证；新增普通文本调用的 `LLMResult` 与异常适配，`/chat` 仍使用原生实现。下一步继续工具协议、Agent 结果和中途失败记录的项目契约对齐，再做原生对照及框架流式接口。真实记忆效果、知识权限及部署验证等边界仍保留；正式进度与新会话接续位置见 [agent-lab 总体学习路线](notes/agent-lab总体学习路线.md#14-当前下一步)。

## 为什么创建这个仓库

这个仓库是个人学习实验场，目标是边学习边手写 AI 应用的核心机制，允许反复实验、推翻和重构。已经理解并验证过的功能，后续再迁移到正式项目 xinyu。这里重点记录学习过程，而不是一开始就包装成完整产品。

## 当前技术栈

- Python 3.12
- FastAPI
- Uvicorn
- Pydantic
- pytest
- uv
- Git 与 GitHub
- SQLite
- HTTPX 与 MCP SDK
- Ollama / BGE-M3（本地 Embedding）
- Chroma（本地向量存储）
- LangChain / langchain-deepseek（独立机制对照）

当前保留原生 Agent、记忆与 RAG 实现；LangChain 已开始机制对照，LangGraph 专题与 SSE 待开始。LangGraph 随 LangChain 作为依赖安装，不等于已完成其学习阶段。尚未接入登录认证，不将学习用 `user_id` 当作可信身份。

## 项目结构

```text
agent-lab/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── schemas.py
│   ├── mcp_server.py
│   ├── tools.py
│   └── services/
│       ├── __init__.py
│       ├── agent.py
│       ├── llm.py
│       ├── langchain_llm.py
│       ├── langchain_tools.py
│       ├── langchain_agent.py
│       ├── langchain_callbacks.py
│       ├── langchain_retrieval.py
│       ├── langchain_rag.py
│       ├── langchain_adapter.py
│       ├── mcp_tools.py
│       ├── memory.py
│       ├── embedding.py
│       ├── vector_store.py
│       ├── rag.py
│       ├── rag_index.py
│       ├── rag_retrieval.py
│       ├── rag_context.py
│       ├── rag_tools.py
│       ├── rag_citations.py
│       └── rag_answer.py
├── playground/
│   ├── 01_basic_syntax.py
│   ├── 02_json_file.py
│   ├── calculator.py
│   ├── home.py
│   ├── message.json
│   ├── mcp_note_client.py
│   ├── use_calculator.py
│   ├── rag_acceptance_probe.py
│   ├── fixtures/
│   └── results/
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_agent_mcp.py
│   ├── test_conversation_ownership.py
│   ├── test_database.py
│   ├── test_health.py
│   ├── test_langchain_llm.py
│   ├── test_langchain_prompts.py
│   ├── test_langchain_tools.py
│   ├── test_langchain_agent.py
│   ├── test_langchain_retrieval.py
│   ├── test_langchain_rag.py
│   ├── test_langchain_adapter.py
│   ├── test_mcp.py
│   ├── test_memory.py
│   ├── test_memory_extraction.py
│   └── test_tools.py
├── notes/
│   ├── README.md
│   ├── agent-lab总体学习路线.md
│   ├── Codex学习导师提示词.md
│   ├── Memory-V1.1轻量分层长期记忆方案.md
│   ├── 代码注释规范.md
│   └── sqlite多轮会话数据模型草案.md
├── .vscode/
│   └── settings.json
├── .editorconfig
├── .env.example
├── .gitignore
├── LICENSE
├── pyproject.toml
├── uv.lock
└── README.md
```

`app/` 保存可运行的 FastAPI 应用，`tests/` 保存自动化测试，`playground/` 保存独立的 Python 学习示例，`notes/` 用于记录实验过程和结论。

## 源码从哪里开始读

按下面的顺序阅读，可以先看清一条聊天请求，再进入协议与数据细节。各 Python 文件开头都有职责说明，关键函数补充输入输出、异常或事务约束。

| 文件 | 主要负责什么 |
| --- | --- |
| [app/main.py](app/main.py) | HTTP 入口、归属检查、短事务、Agent 调用和错误状态映射 |
| [app/schemas.py](app/schemas.py) | 请求与响应的数据结构；字段校验不替代业务规则 |
| [app/config.py](app/config.py) | 从进程环境读取应用和模型配置，不直接解析 .env |
| [app/services/agent.py](app/services/agent.py) | 多轮模型与工具循环、调用预算和中途失败边界 |
| [app/services/llm.py](app/services/llm.py) | 单次模型 HTTP 请求、响应解析和结构化调用元数据 |
| [app/services/langchain_llm.py](app/services/langchain_llm.py) | 独立的 ChatDeepSeek 调用、消息模板与 Runnable 组合 |
| [app/services/langchain_tools.py](app/services/langchain_tools.py) | 将原生计算器包装为框架工具，复用参数校验和计算逻辑 |
| [app/services/langchain_agent.py](app/services/langchain_agent.py) | 独立的框架工具循环、三次模型限额与消息轨迹返回 |
| [app/services/langchain_callbacks.py](app/services/langchain_callbacks.py) | 回调采集成功/失败模型步骤的耗时、可用 Token 与异常类型 |
| [app/services/langchain_retrieval.py](app/services/langchain_retrieval.py) | 将原生异步检索包装为 Runnable，保留 Document 原文与来源 |
| [app/services/langchain_rag.py](app/services/langchain_rag.py) | 预算内片段到模板与模型，再校验实际交付来源；保留原始响应 |
| [app/services/langchain_adapter.py](app/services/langchain_adapter.py) | 普通文本单次调用转项目结果与异常，以 HTTP 响应钩子记录实际状态 |
| [app/tools.py](app/tools.py) | 工具声明、参数校验与本地工具执行 |
| [app/services/mcp_tools.py](app/services/mcp_tools.py) | 将 Agent 的笔记工具请求接到 MCP Client |
| [app/mcp_server.py](app/mcp_server.py) | 提供笔记 Tool 和学习路线 Resource，执行真实文件读取 |
| [app/database.py](app/database.py) | SQLite 建表、历史窗口、消息/调用记录与记忆存储 |
| [app/services/memory.py](app/services/memory.py) | 记忆触发、候选绑定、范围合并、Core/Regular 选择预算与写入编排 |
| [app/services/embedding.py](app/services/embedding.py) | 请求本机 Ollama，将文本转为 BGE-M3 向量 |
| [app/services/vector_store.py](app/services/vector_store.py) | 接收已有向量，在 Chroma 中存储、同步与查询 |
| [app/services/rag_tools.py](app/services/rag_tools.py) | 校验语义工具参数，检索并选择预算内片段；Agent 回传工具消息 |
| [app/services/rag_answer.py](app/services/rag_answer.py) | 共用引用收尾，以及独立的严格知识库问答路径 |

对应的 `tests/test_*.py` 说明每条链路的正常与失败预期。`pyproject.toml` 管理依赖与 pytest 配置，`uv.lock` 固定依赖解析结果；`playground/message.json` 是文件读写练习的数据，不是应用配置。注释写法见 [代码注释规范](notes/代码注释规范.md)。

## 本地运行

先安装 [uv](https://docs.astral.sh/uv/)，然后在仓库根目录执行：

```bash
uv sync --dev
cp .env.example .env
uv run uvicorn app.main:app --reload --env-file .env
```

服务默认运行在 `http://127.0.0.1:8000`。可使用以下命令检查接口：

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"test-001","message":"你好"}'
```

`/chat` 可选传入 `user_id`；省略时创建匿名会话。会话建立后归属固定，后续请求必须保持一致，包括是否匿名；不同归属返回 `409`，不会保存本轮消息或调用 Agent。该字段当前是学习用身份标识，尚未接入登录认证。

`.env` 只用于本地配置，已被 Git 忽略。不要在 `.env.example` 或代码中写入真实 API Key。

可选配置 `RAG_INDEX_PATH` 指向已建好的专用 Chroma 索引；留空时不提供语义检索工具。配置后仍由模型决定是否调用，应用启动或普通聊天不会自动重建索引。显式索引入口是 `app.services.rag_index.build_index()`，当前读取指定目录下的普通 Markdown，不递归或跟随符号链接。

`/chat` 返回 `sources` 和 `invalid_citation_ids`，没有来源时为空列表。来源来自本轮交付且被正文合法引用的片段；ID 合法不等于结论一定得到原文支持。来源快照只在本次响应返回，尚未持久化为可恢复的历史证据。

`POST /memories/query` 和 `POST /memories/delete` 提供记忆查看与按范围删除；具体请求模型见 `app/schemas.py` 和 `/docs`。归属检查沿用会话规则，当前没有额外登录认证。

## GitHub SSH Key 撤销提醒

本仓库首次推送使用为个人账号 `Galilieo` 单独创建的 SSH Key。以后如果不再从当前电脑维护这个仓库，请前往 GitHub 的 `Settings > SSH and GPG keys` 撤销对应 Key，并删除本机私钥。不要将私钥或访问令牌提交到仓库。

## 运行测试

```bash
uv run pytest
```

2026-11-03 实际离线全量结果为 `135 passed`。默认 pytest 使用 fake 模型 HTTP、临时数据库和索引，不调用真实模型。后续结果以正式路线更新为准。

LangChain 对照测试为 `tests/test_langchain_*.py`，模拟聊天 HTTP 和问题 Embedding，真实运行模板、SDK、工具、Agent、回调及临时 Chroma 查询。严格 RAG 仅交付预算内片段，来源校验不证明语义忠实；人工向量不证明真实检索质量。普通文本适配已返回项目 `LLMResult` 并转换超时、连接、上游状态与解析异常，工具协议、Agent 记录与持久化接线仍待完成。适配计时覆盖客户端及框架处理，回调计时覆盖模型步骤，均不等同于纯网络耗时。框架模型限额在下一次模型请求前检查，最后一次工具可能已执行，与原生执行前预算保护不同；此处仅验证无外部副作用的计算器。

固定合成题的真实模型验收需显式运行，会请求本机 Ollama 和已配置聊天 API：

```bash
uv run --offline --no-sync --env-file .env python -m playground.rag_acceptance_probe \
  --output playground/results/rag_acceptance_new_run.json
```

选择新的结果文件名以保留历史证据。这里的 `--offline` 只约束 uv 的依赖获取，不会禁用脚本中的模型网络请求。

本轮 [首次结果](playground/results/rag_acceptance_probe.json)发现引用 ID 多加前缀；[中断复验](playground/results/rag_acceptance_recheck.json)记录连接失败；[完整复验](playground/results/rag_acceptance_recheck_2.json)在说明澄清后通过限定验收：12 次 HTTP、17 次模型调用，4 道可答题事实与对应引用正确，5 道资料题无未知引用，缺失电话未编造，问候未检索。这是进程内正式 `/chat` 路径的合成实验，排除了关键词 MCP 工具；不是部署网络验收，也不证明单轮改善的因果或通用稳定性。

## 当前完成情况

- [x] FastAPI 项目基础骨架
- [x] `GET /health` 健康检查接口
- [x] `POST /chat` 真实异步 LLM 调用
- [x] Pydantic 请求与响应模型
- [x] 基础接口测试
- [x] 环境变量示例与 Git 忽略规则
- [x] 真实大模型调用
- [x] SQLite 连接、会话/消息/调用/记忆四表结构、模型调用重试关系、跨会话外键隔离、稳定历史与最近窗口查询、文件持久化验证
- [x] SQLite 多轮对话 API 接线，以及成功/失败 `model_call` 追踪
- [x] SQLite schema 启动生命周期
- [x] 阶段 5 真实 Uvicorn + HTTP 两轮会话验收
- [x] calculator Tool Calling 协议解析、参数校验和单轮 Agent 工具闭环
- [x] `/chat` 接入 Agent，并追踪中间与最终成功模型调用
- [x] 可配置 Agent 工具循环，以及默认最多 3 次模型调用的停止保护
- [x] 后续模型调用失败时保留已完成调用并持久化完整失败链
- [x] 最大模型调用预算耗尽时返回 `502` 并持久化已完成调用
- [x] 未知工具、非法参数和工具执行失败时返回 `502`，并保留此前成功的模型调用
- [x] get_current_time 时区参数校验、本地执行、双工具注册与回传闭环的自动化验证
- [x] search_notes 固定范围查询、原文出处、空结果和三工具注册的自动化验证
- [x] 独立 MCP Server 工具注册、同进程 Client 测试与真实 stdio 查询实验
- [x] MCP Client 接入 Agent 查询分支、工具结果回传与失败边界验证
- [x] 学习路线 Resource 的真实 stdio 读取，以及 Tool / Resource / Prompt 职责复述
- [x] 可选用户标识、会话归属冲突检查与旧会话表补列兼容
- [x] 两种范围 memory 表、UPSERT、来源校验与无效来源不覆盖旧记忆
- [x] [Memory V1.1 完整方案](notes/Memory-V1.1轻量分层长期记忆方案.md)落盘并关联正式路线
- [x] Pydantic 提取结果模型、多条候选与 skip、空 upsert 和伪造来源拒绝
- [x] LLM 按需提取、Core/Regular 选择预算与上下文注入的离线闭环
- [x] 记忆查看、按归属范围删除和顺序执行下防旧历史重建
- [x] Markdown 读取切分、本地 BGE-M3 Embedding 和 Chroma 持久化
- [x] 显式索引同步、TopK 检索和整片上下文预算
- [x] `/chat` 按配置启用语义工具、Agent 按需调用和来源累积
- [x] 引用 ID 白名单检查、无效引用标注及实际引用来源响应
- [x] 固定合成题的真实模型对照与限定范围复验
- [x] LangChain 单次模型调用、模板与 Runnable 的独立离线对照
- [x] 框架计算器、Agent 循环及成功/超时模型回调记录的独立离线验证
- [x] LangChain 异步检索、严格 RAG 链及原始响应保留的独立离线验证
- [x] 普通文本框架调用的项目结果与异常适配、实际 HTTP 状态观测
- [ ] 框架工具/Agent 完整业务契约对齐、原生对照验收及流式接口
- [ ] LangGraph、SSE 与心屿 Java + Python 接入

阶段 5 只保证数据模型可记录同一 user message 的多次调用，不实现自动重试策略；自动重试留到评测与工程化阶段。最近消息窗口是当前最小上下文裁剪方案，历史摘要待记忆或评测阶段出现真实需求后再实现，不阻塞阶段 5 完成。

阶段 5 已在用户明确授权后，通过本地 `.env`、真实 Uvicorn 和独立临时数据库完成一次真实 DeepSeek 两轮联调；第二轮正确回答了第一轮提供的合成测试代号。联调没有输出 API Key，临时数据库已在验证后删除。

阶段 6 已完成第一轮：三个基础工具、原生 Agent 循环、错误持久化边界及官方 MCP SDK 2.3.0 接线均已验证。`run_agent()` 的 search_notes 分支通过异步 MCP Client 执行，其他基础工具沿用本地执行；Server 另提供 `notes://learning-route` Resource。2026-10-16 的 `41 passed` 是历史基线；fake 模型配合真实同进程 MCP 查询验证回传链，独立 stdio 实验验证工具查询与 Resource 读取。当时未访问真实聊天模型，不将后续排除关键词工具的 RAG 验收当作完整 MCP 联调证据。Agent 接线与 Tool / Resource / Prompt 职责已完成复述；Resource 未自动注入上下文，MCP Prompt 只做职责理解。

阶段 7 的记忆最小闭环已离线验证；原生 RAG 已完成上述有限合成验收。真实记忆提取与偏好遵循、并发删除时在途任务防重建、多租户知识权限及历史来源快照恢复仍未验证或实现。

2026-10-19 会话归属目标测试为 `3 passed`，全量为 `44 passed`，`git diff --check` 通过。该测试使用临时旧数据库和 fake Agent，验证归属冲突返回 409、拒绝请求不追加消息和调用 Agent，以及旧会话数据保留；另以临时数据库验证重复初始化及旧会话继续聊天。已完成复述验收，没有调用真实模型。

## 后续学习路线

- V0.1 基础模型调用与调用日志
- V0.2 多轮对话与上下文管理
- V0.3 Tool Calling、Structured Output 与 MCP 小补充
- V0.4 轻量记忆
- V0.5 RAG
- 接下来：LangChain → LangGraph → SSE、评测与工程化
- 最后：保留 Python AI 服务，与心屿 Java 业务后端集成

每个阶段都应先理解并验证核心机制，再决定是否重构或迁移到正式项目。
