# agent-lab

用于学习和验证大模型调用、多轮对话、Tool Calling、记忆、RAG、SSE 流式输出等 AI 应用开发能力。

> agent-lab 是学习与验证仓库，xinyu 是后续承接成熟能力的正式项目。这里优先保证理解原理，不追求一开始就做成完整产品。

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
- SQLite（后续接入）

当前阶段不使用 LangChain、LangGraph、向量数据库、Redis、Docker、前端框架、用户系统、多 Agent 或复杂架构。

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
- [x] `POST /chat` 占位接口
- [x] Pydantic 请求与响应模型
- [x] 基础接口测试
- [x] 环境变量示例与 Git 忽略规则
- [ ] 真实大模型调用
- [ ] SQLite 数据持久化

## 后续学习路线

- V0.1 基础模型调用与调用日志
- V0.2 多轮对话与上下文管理
- V0.3 Tool Calling
- V0.4 轻量记忆
- V0.5 RAG
- V0.6 SSE 流式输出
- V0.7 将成熟模块迁移到 xinyu

每个阶段都应先理解并验证核心机制，再决定是否重构或迁移到正式项目。
