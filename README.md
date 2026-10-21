# agent-lab

用于学习和验证大模型调用、多轮对话、Tool Calling、记忆、RAG、SSE 流式输出等 AI 应用开发能力。

> agent-lab 是学习与验证仓库，xinyu 是后续承接成熟能力的正式项目。这里优先保证理解原理，不追求一开始就做成完整产品。
>
> 当前进度：阶段 5、阶段 6 均已完成第一轮；阶段 7 的会话归属、两种范围记忆存储和 Pydantic 提取结果模型已通过回归，当前全量基线为 `51 passed`。Memory V1.1 方案已确定，提取结果结构校验小主题已收口，下一步是轻量触发规则与 LLM 提取调用契约；自动提取、记忆选择和注入尚未接通。详细阶段、验收标准和下一步见 [agent-lab 总体学习路线](notes/agent-lab总体学习路线.md)。

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

当前阶段不使用 LangChain、LangGraph、向量数据库、Redis、Docker、前端框架、用户系统、多 Agent 或复杂架构。

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
│       └── mcp_tools.py
├── playground/
│   ├── 01_basic_syntax.py
│   ├── 02_json_file.py
│   ├── calculator.py
│   ├── home.py
│   ├── message.json
│   ├── mcp_note_client.py
│   └── use_calculator.py
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_agent_mcp.py
│   ├── test_conversation_ownership.py
│   ├── test_database.py
│   ├── test_health.py
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
| [app/tools.py](app/tools.py) | 工具声明、参数校验与本地工具执行 |
| [app/services/mcp_tools.py](app/services/mcp_tools.py) | 将 Agent 的笔记工具请求接到 MCP Client |
| [app/mcp_server.py](app/mcp_server.py) | 提供笔记 Tool 和学习路线 Resource，执行真实文件读取 |
| [app/database.py](app/database.py) | SQLite 建表、历史窗口、消息/调用记录与记忆存储 |

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

## GitHub SSH Key 撤销提醒

本仓库首次推送使用为个人账号 `Galilieo` 单独创建的 SSH Key。以后如果不再从当前电脑维护这个仓库，请前往 GitHub 的 `Settings > SSH and GPG keys` 撤销对应 Key，并删除本机私钥。不要将私钥或访问令牌提交到仓库。

## 运行测试

```bash
uv run pytest
```

2026-10-21 实际全量结果为 `51 passed`，其中 `tests/test_memory_extraction.py` 的三个场景已由正确 RED 转为 GREEN。后续结果以正式路线更新为准；测试通过与真实模型联调是不同证据。

## 当前完成情况

- [x] FastAPI 项目基础骨架
- [x] `GET /health` 健康检查接口
- [x] `POST /chat` 真实异步 LLM 调用
- [x] Pydantic 请求与响应模型
- [x] 基础接口测试
- [x] 环境变量示例与 Git 忽略规则
- [x] 真实大模型调用
- [x] SQLite 连接、三表结构、模型调用重试关系、跨会话外键隔离、稳定历史与最近窗口查询、文件持久化验证
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
- [ ] LLM 按需提取、分层选择与上下文注入

阶段 5 只保证数据模型可记录同一 user message 的多次调用，不实现自动重试策略；自动重试留到评测与工程化阶段。最近消息窗口是当前最小上下文裁剪方案，历史摘要待记忆或评测阶段出现真实需求后再实现，不阻塞阶段 5 完成。

阶段 5 已在用户明确授权后，通过本地 `.env`、真实 Uvicorn 和独立临时数据库完成一次真实 DeepSeek 两轮联调；第二轮正确回答了第一轮提供的合成测试代号。联调没有输出 API Key，临时数据库已在验证后删除。

阶段 6 已完成第一轮：三个工具、原生 Agent 循环、错误持久化边界及官方 MCP SDK 2.3.0 接线均已验证。`run_agent()` 的 search_notes 分支通过异步 MCP Client 执行，其他工具沿用本地执行；Server 另提供 `notes://learning-route` Resource。2026-10-16 全量测试为 `41 passed`；fake 模型配合真实同进程 MCP 查询验证回传链，失败探索验证异常承接和调用记录保留，独立 stdio 实验验证工具查询与 Resource 读取。上述阶段 6 验证未访问真实 DeepSeek，不能证明真实模型的工具选择或完整 MCP 联调。Agent 接线与 Tool / Resource / Prompt 职责均已完成复述验收；Resource 未自动注入 Agent 上下文，MCP Prompt 只做职责理解。阶段 7 的可选用户标识、会话归属与记忆存储已实现并验证，自动提取与上下文注入仍待完成。阶段 6 曾于 2026-08-26 暂停，并于 2026-09-04 恢复开发。

2026-10-19 会话归属目标测试为 `3 passed`，全量为 `44 passed`，`git diff --check` 通过。该测试使用临时旧数据库和 fake Agent，验证归属冲突返回 409、拒绝请求不追加消息和调用 Agent，以及旧会话数据保留；另以临时数据库验证重复初始化及旧会话继续聊天。已完成复述验收，没有调用真实模型。

## 后续学习路线

- V0.1 基础模型调用与调用日志
- V0.2 多轮对话与上下文管理
- V0.3 Tool Calling、Structured Output 与 MCP 小补充
- V0.4 轻量记忆
- V0.5 RAG
- V0.6 SSE 流式输出
- V0.7 将成熟模块迁移到 xinyu

每个阶段都应先理解并验证核心机制，再决定是否重构或迁移到正式项目。
