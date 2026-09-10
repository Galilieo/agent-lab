# agent-lab

用于学习和验证大模型调用、多轮对话、Tool Calling、记忆、RAG、SSE 流式输出等 AI 应用开发能力。

> agent-lab 是学习与验证仓库，xinyu 是后续承接成熟能力的正式项目。这里优先保证理解原理，不追求一开始就做成完整产品。
>
> 当前进度：阶段 5“SQLite 与多轮对话”已完成第一轮；阶段 6“原生 Tool Calling 与 Agent 循环”已完成可配置循环和中途失败记录，尚未完成全部错误边界，已于 2026-09-04 恢复开发，当前从最大模型调用预算耗尽后的错误边界继续。详细阶段、验收标准和下一步见 [agent-lab 总体学习路线](notes/agent-lab总体学习路线.md)。

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
│   ├── tools.py
│   └── services/
│       ├── __init__.py
│       ├── agent.py
│       └── llm.py
├── playground/
│   ├── 01_basic_syntax.py
│   ├── 02_json_file.py
│   ├── calculator.py
│   ├── home.py
│   ├── message.json
│   └── use_calculator.py
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_database.py
│   ├── test_health.py
│   └── test_tools.py
├── notes/
│   ├── README.md
│   ├── agent-lab总体学习路线.md
│   ├── Codex学习导师提示词.md
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

`.env` 只用于本地配置，已被 Git 忽略。不要在 `.env.example` 或代码中写入真实 API Key。

## GitHub SSH Key 撤销提醒

本仓库首次推送使用为个人账号 `Galilieo` 单独创建的 SSH Key。以后如果不再从当前电脑维护这个仓库，请前往 GitHub 的 `Settings > SSH and GPG keys` 撤销对应 Key，并删除本机私钥。不要将私钥或访问令牌提交到仓库。

## 运行测试

```bash
uv run pytest
```

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

阶段 5 只保证数据模型可记录同一 user message 的多次调用，不实现自动重试策略；自动重试留到评测与工程化阶段。最近消息窗口是当前最小上下文裁剪方案，历史摘要待记忆或评测阶段出现真实需求后再实现，不阻塞阶段 5 完成。

阶段 5 已在用户明确授权后，通过本地 `.env`、真实 Uvicorn 和独立临时数据库完成一次真实 DeepSeek 两轮联调；第二轮正确回答了第一轮提供的合成测试代号。联调没有输出 API Key，临时数据库已在验证后删除。

阶段 6 当前已完成 calculator 工具、Pydantic 参数校验、工具结果回传模型、直接回答分支、可重复 Agent 循环、默认最大模型调用次数，以及成功、“中途成功后最终失败”和最大次数耗尽三条调用链的 `model_call` 持久化。未知工具和工具执行错误、当前时间与 Markdown 工具、MCP 接入仍待完成，因此阶段 6 尚未完成。阶段 6 曾于 2026-08-26 暂停，并于 2026-09-04 恢复开发。

## 后续学习路线

- V0.1 基础模型调用与调用日志
- V0.2 多轮对话与上下文管理
- V0.3 Tool Calling、Structured Output 与 MCP 小补充
- V0.4 轻量记忆
- V0.5 RAG
- V0.6 SSE 流式输出
- V0.7 将成熟模块迁移到 xinyu

每个阶段都应先理解并验证核心机制，再决定是否重构或迁移到正式项目。
