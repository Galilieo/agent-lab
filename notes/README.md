# 笔记索引

2026-11-16 整理：当前项目是实习求职助手 Agent；已被取代的规划移入 [`history/`](./history/)，知识笔记保留在本目录。

## 当前项目

- [实习求职助手 Agent 设计文档](./求职助手Agent/README.md)：总览与决策、功能设计、技术架构与数据模型、可信安全与隐私、评测方案、落地与里程碑。**设计完成并冻结（2026-11-16），尚未实施。**

## 知识笔记

知识笔记按「项目用途 → 常用写法与例子 → 我的理解 → 误区与验证」整理。个人原有表述可保留并注明校准；尚未由自己复述的内容写成待补充，不记为已经掌握。

### Python 与数据校验

- [Python 函数与装饰器](./Python函数与装饰器.md)：函数对象、内部函数、闭包与装饰器。
- [Python 函数参数与解包](./Python函数参数与解包.md)：`*args`、`**kwargs`、单独的 `*`，以及调用时解包与装饰器参数转发。
- [Pydantic 与 schemas](./Pydantic与schemas.md)：模型职责、常用方法的输入输出与校验链路。

### LangChain 与 LangGraph

- [LangChain 与原生实现对照](./LangChain与原生实现对照.md)：三个入口的职责、共享场景验收、工具参数与失败记录，以及计时和预算的差异。
- [LangGraph 前置知识](./LangGraph前置知识.md)：State / Node / Edge、部分状态更新、reducer，以及模型 / 工具图的路由与预算。
- [LangGraph 检查点与恢复](./LangGraph检查点与恢复.md)：checkpointer 与 thread_id、SQLite 重开读回、工具前人工确认、模型超时后的显式恢复。
- [LangGraph 阶段总结](./LangGraph阶段总结.md)：第一轮核心机制收口、原生与图的职责对应和验证边界。

### 流式输出

- [SSE 前置知识](./SSE前置知识.md)：模型片段、异步生成器、HTTP 流与 SSE 事件，中途失败与断开取消。
- [SSE 浏览器消费](./SSE浏览器消费.md)：浏览器端解码、事件缓冲与 AbortController 停止。

### 记忆与数据

- [Memory V1.1 轻量分层长期记忆方案](./Memory-V1.1轻量分层长期记忆方案.md)：分层、提取、选择、注入与删除防重建；求职助手的长期记忆沿用此设计。
- [SQLite 多轮会话数据模型草案](./sqlite多轮会话数据模型草案.md)：早期实验的表关系与持久化语义。

### 评测与工程化

- [固定评测与结果判读](./固定评测与结果判读.md)：固定合成题、按组检查口径与离线汇总。
- [重试与错误日志边界](./重试与错误日志边界.md)：有限重试与安全失败日志。
- [工程化职责与心屿交接](./工程化职责与心屿交接.md)：身份与归属、限流与预算、日志关联、模型判断与执行权限的职责划分。

### 产品与开源学习

- [优秀 Agent 产品设计学习](./优秀Agent产品设计学习.md)：pi / Hermes / Codex / Claude Code 等的定向学习安排与证据要求。
- [pi 专题](./pi专题/tutorial.md)：固定源码的多步执行与中断状态带读。

### 规范与协作

- [代码注释规范](./代码注释规范.md)：参考 PEP 8 / PEP 257 的注释约定。
- [Codex 学习导师提示词](./Codex学习导师提示词.md)：教学粒度、设计讲解与代码验证的协作约定。

### 学习路线（已结束）

- [agent-lab 总体学习路线](./agent-lab总体学习路线.md)：2026-11-07 收口前机制学习的正式路线与进度记录，保留为历史证据。

## 实验材料：RAG 固定合成题

- [问题与合成文档](../playground/fixtures/rag_acceptance.json)：同题对照关闭 / 开启知识库。
- [显式运行脚本](../playground/rag_acceptance_probe.py)：真实本机 Embedding、Chroma 和聊天 API；默认 pytest 不会执行。
- [首次记录](../playground/results/rag_acceptance_probe.json)、[连接中断记录](../playground/results/rag_acceptance_recheck.json)、[完整复验记录](../playground/results/rag_acceptance_recheck_2.json)：保留原始结果与逐题复核。重跑时用 `--output` 选择新文件，不覆盖历史记录。

## 历史记录（history/）

已被取代或已结束的规划，保留原文，不再作为当前依据：

| 文档 | 说明 |
| --- | --- |
| [2026-11-16 求职主题比较与企业知识评测](./history/2026-11-16-求职主题比较与企业知识评测.md) | 主题比较；当时建议企业知识分析 Agent，其中的实习岗位要求仍可参考 |
| [2026-11-16 Agent 功能与开源选型](./history/2026-11-16-Agent功能与开源选型.md) | 选型调研 |
| [2026-11-16 Harness 架构候选池与筛选记录](./history/2026-11-16-Harness架构候选池与筛选记录.md) | 22 个 Harness / 框架候选的比较 |
| [2026-11-14 技术调研 Agent V1 方案](./history/2026-11-14-技术调研Agent-V1方案.md) | 此前的候选产品设计 |
| [2026-11-07 阶段封存与心屿交接](./history/2026-11-07-阶段封存与心屿交接.md) | 机制学习收口时的验证与限制 |
| [2026-11-07 心屿升级范围讨论记录](./history/2026-11-07-心屿升级范围讨论记录.md) | 心屿范围讨论 |
| [心屿整体设计讨论](./history/心屿整体设计讨论.md)、[心屿接入首轮方案](./history/心屿接入首轮方案.md) | 心屿设计草案；以心屿仓库的总方案为准 |
| [优秀产品设计调研 2026-11-06](./history/优秀产品设计调研-2026-11-06.md) | 多产品横向研究准备 |
| [设计复核 2026-11-02](./history/设计复核-2026-11-02.md) | 早期代码的评审快照 |
| [早期机制实验说明](./history/早期机制实验说明.md) | 2026-11-16 前根目录 README 中的完成清单、验收记录与源码阅读顺序 |

## 记录约定

建议每次实验至少记录：

1. 想验证的问题。
2. 核心机制、设计理由与真实源码位置。
3. 实验过程和结果。
4. 推翻或保留当前方案的原因。
5. 是否适合用于求职助手或心屿。

不要在笔记中记录真实 API Key、公司代码、内部接口、公司数据或其他敏感信息。

讲解与笔记优先回答四个问题：解决什么问题、为什么这样设计、代码怎样执行、如何证明有效。明确区分文档阅读、源码核验、实际体验、离线测试与生产经验，不将参考文章的功能清单直接扩成项目任务。

## 后续书籍参考

- 李博杰[《深入理解 AI Agent：设计原理与工程实践》](https://github.com/bojieli/ai-agent-book)：优先阅读[第2章上下文工程](https://github.com/bojieli/ai-agent-book/blob/main/book/chapter2.md)、[第7章评估](https://github.com/bojieli/ai-agent-book/blob/main/book/chapter7.md)，按需对照[第3章记忆与知识库](https://github.com/bojieli/ai-agent-book/blob/main/book/chapter3.md)、[第6章交互](https://github.com/bojieli/ai-agent-book/blob/main/book/chapter6.md)。先看[学习建议](https://github.com/bojieli/ai-agent-book/blob/main/docs/zh-CN/LEARNING.md)，再用现有项目检查设计取舍和验证证据；不另开一套必修课程。
