# agent-lab

面向 AI 应用 / Agent 开发实习求职的个人项目：**实习求职助手 Agent**（开发中）。

> 当前状态（2026-11-16）：**设计完成并冻结，尚未开始实现。** 设计文档见 [notes/求职助手Agent](notes/求职助手Agent/README.md)。

## 求职助手 Agent 是什么

帮正在找技术类实习的学生完成「看 JD → 对照简历 → 按岗位改简历 → 准备面试 → 跟踪投递」。

核心约束是**改写简历时不编造经历**：简历先拆成用户确认过的「经历事实」，改写的每一条都必须引用事实，再经过三层依据检查（引用合法性、数字与实体比对、语义支持判断）。效果用自建评测集和对照实验衡量。

V1 定位为个人学习项目，本人求职时在本地使用；暂不上线和推广，但用户表、登录与用户隔离照常实现，为以后开放预留。

| 设计文档 | 内容 |
| --- | --- |
| [00 总览与决策](notes/求职助手Agent/00-总览与决策.md) | 为什么选这个题目、范围、完成标准 |
| [01 功能设计](notes/求职助手Agent/01-功能设计.md) | 经历事实库、JD 解析、匹配、改写与依据检查、模拟面试、记忆等 |
| [02 技术架构与数据模型](notes/求职助手Agent/02-技术架构与数据模型.md) | 架构决定、LangGraph 流程、数据表、RAG、记忆与上下文管理 |
| [03 可信、安全与隐私](notes/求职助手Agent/03-可信安全与隐私.md) | 防编造、提示注入防御、个人信息保护 |
| [04 评测方案](notes/求职助手Agent/04-评测方案.md) | 评测集、指标与对照实验 |
| [05 落地与里程碑](notes/求职助手Agent/05-落地与里程碑.md) | 每周计划、风险 |

### 计划技术栈

- 前端：React + Vite + TypeScript + Ant Design
- 后端：Python 3.12、FastAPI（异步）、SQLAlchemy 2.0 + Alembic
- 数据库：PostgreSQL + pgvector（本地用 Docker 启动）
- Agent：LangGraph 编排，自写模型调用网关（DeepSeek）
- 评测：自建评测集与对照实验

## 仓库结构

```text
agent-lab/
├── app/          # 早期机制实验：原生 Agent、工具、Memory、RAG、MCP、LangChain / LangGraph 对照、SSE
├── tests/        # 早期实验的自动化测试
├── playground/   # Python 练习、真实模型验收脚本与结果
├── notes/
│   ├── 求职助手Agent/   # 当前项目的设计文档
│   ├── history/        # 已被取代的规划与历史记录
│   └── ...             # 知识笔记，索引见 notes/README.md
└── README.md
```

求职助手的代码将放在新目录 `jobpilot/`（后端）和 `web/`（前端），与 `app/` 分开管理、依赖独立。

## 早期机制实验（app/）

这个仓库最初是 AI 应用机制的学习实验场，按阶段手写并验证了：

- 模型调用与调用日志，SQLite 多轮会话与会话归属检查
- Tool Calling 与原生 Agent 循环（调用预算、中途失败的持久化）
- MCP Server / Client 接线
- 分层长期记忆（[Memory V1.1](notes/Memory-V1.1轻量分层长期记忆方案.md)）：提取、选择、注入、删除防重建
- RAG：BGE-M3 Embedding、Chroma、引用 ID 校验
- LangChain 与原生实现对照；LangGraph 的条件路由、检查点、人工确认与失败恢复
- SSE 流式输出与浏览器消费
- 固定合成题评测与有限重试

这部分已于 2026-11-07 收口。完整的完成清单、验收记录和源码阅读顺序见[早期机制实验说明](notes/history/早期机制实验说明.md)，学习笔记见 [notes/README.md](notes/README.md)。

### 运行

先安装 [uv](https://docs.astral.sh/uv/)，然后在仓库根目录执行：

```bash
uv sync --dev
cp .env.example .env
uv run uvicorn app.main:app --reload --env-file .env
```

服务默认运行在 `http://127.0.0.1:8000`。`.env` 只用于本地配置，已被 Git 忽略；不要在 `.env.example` 或代码中写入真实 API Key。

### 测试

```bash
uv run pytest
```

2026-11-07 收口时离线全量结果为 `174 passed`。默认测试使用假的模型 HTTP、临时数据库和索引，不调用真实模型。

## License

见 [LICENSE](LICENSE)。
