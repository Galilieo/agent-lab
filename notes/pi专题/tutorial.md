# pi 产品设计专题 1：多步执行与中断后的状态

状态：已展开；固定源码静态带读，未运行 pi、未验证真实模型任务。用户已确认continue答疑的主干理解，其余专题理解与体验仍待完成。工程重要性：高；与心屿接入的相关性：高。

## 阅读版本与范围

- 核验日期：2026-11-06（Asia/Taipei）。
- 官方仓库：[earendil-works/pi](https://github.com/earendil-works/pi)；旧 badlogic/pi-mono 地址实际跳转到这里。
- `git ls-remote` 当次返回的 main 完整 SHA：`96667f342a8da98ec7969caee7f920ace104436f`。以下源码均从该 SHA 下载核对，不用默认分支网页代替固定源码。
- 该快照 `packages/agent/package.json` 声明 `@earendil-works/pi-agent-core` 为 `1.5.0`；这是源码中的包版本，不是本机已安装 CLI 版本，也不据此声称是最新发布版。
- 主读 `packages/agent` 的执行核心，延伸到 `coding-agent` 的会话事件与 JSONL 存储。当前仓库还包含 pi-durable，本课没有深读它，结论不外推到整个 pi 的所有持久化能力。
- 本次只下载六个公开源码/说明文件到临时目录，不安装依赖、不运行 pi、不请求模型。网页入口观察、固定源码结论与既有 lab 测试分开记录。

## 1. 场景：一句任务为什么需要多次调用模型

假设用户要求“读取配置，计算预算，再解释是否超支”。模型第一次看到任务时，可能只知道需要读取文件；读到文件后才知道要计算什么；取得计算结果后才能解释。

这里的多步执行不必预先生成一份完整计划。模型提出下一批工具请求，运行时执行并回传结果，再让模型决定下一步，就能形成动态循环。显式计划、任务清单是额外的产品设计，不从循环的存在自动推导。

最小前置概念：transcript 是已经形成的消息记录；运行时还会有当前输出片段、待执行工具 ID 和取消信号；这两类状态的寿命不同。

```text
AgentSession.prompt(text)
  → _preparePrompt / _startRun / _prepareRun
  → Agent.prompt(messages)
  → runPromptMessages → runWithLifecycle → runAgentLoop
  → runLoop
      → prepareRequest → streamAssistantResponse
      → 有工具请求：executeToolCalls → 工具结果入上下文 → 再次请求模型
      → 无工具且无继续条件：agent_end

每条定稿消息的事件支线：
message_end
  → Agent.processEvents 更新内存消息
  → await AgentSession._handleAgentEvent
  → SessionManager.appendMessage → _appendEntry → _persist
```

这张图有一条直接调用主链和一条事件回调支线。不是模型自己调用本地文件函数，也不是 UI 在每次工具完成后重新发送整项用户任务。

## 2. 沿主链读四个职责

| 顺序 | 固定源码与符号 | 要看懂的职责 |
| --- | --- | --- |
| 1 | [agent-session.ts：prompt](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/coding-agent/src/core/agent-session.ts#L2137)、[_startRun](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/coding-agent/src/core/agent-session.ts#L1918) | 输入处理、忙碌时入队、准备本次消息和产品层运行生命周期 |
| 2 | [agent.ts：prompt / continue](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent.ts#L380)、[runWithLifecycle](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent.ts#L517) | 防止同一 Agent 并发启动、建立取消信号、结束后清理瞬时状态 |
| 3 | [agent-loop.ts：runLoop](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent-loop.ts#L172)、[streamAssistantResponse](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent-loop.ts#L390) | 上下文转模型输入、流式响应、工具执行、下一步与结束判断 |
| 4 | [agent-session.ts：_handleAgentEvent](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/coding-agent/src/core/agent-session.ts#L1139)、[session-manager.ts：appendMessage](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/coding-agent/src/core/session-manager.ts#L1215) | 将定稿消息转为带父子关系的持久记录 |

第一次读先沿这四步。供应商实现、终端渲染、压缩算法、插件系统和 pi-durable 暂缓。

### 2.1 循环继续的依据

`runLoop` 取 assistant 消息中的 `toolCall`，执行后把 `toolResult` 放入上下文，才开始下一次模型调用。工具 ID 关联请求与结果，与我们原生 `tool_call_id` 的作用相同。

正常情况下，有工具结果就继续；无工具时可能结束。但当前实现还有 `finishTurn` 的显式决定、steering 队列和 follow-up 队列，因此“没有工具请求就必定结束”并不精确。`error` / `aborted` 的模型响应走硬退出，不能靠 `finishTurn` 强行续跑。工具批次还支持全部结果均声明 `terminate` 时跳过自动续调。

产品上的意义：用户不需要把一句任务拆成多次提交；运行时负责把每一步的真实结果组织成下一步输入。代价是每次续调都有模型成本，也需要明确的结束和预算策略。我们已有 `max_model_calls` 执行前预算，不应因参考项目的调度能力更多而删除。

### 2.2 运行中的追加输入

`Agent.steer()` 与 `followUp()` 都先入队。steering 在下一轮模型调用前的边界消费；follow-up 在当前循环本来要结束时消费。

就本课这个快照而言，steering 不等于立即杀掉当前工具，也不会把当前工具批次切开。工具批次有串行与并行两种策略；默认 Agent 配置为并行。并行完成事件可以乱序，但工具结果消息按模型原请求顺序提交。不要把旧教程里“steer 跳过剩余工具”的行为套到这个版本。

## 3. 状态怎样从瞬时显示变成可恢复记录

`streamAssistantResponse` 将流中的增量发成 `message_update`；`Agent.processEvents` 用它更新 `streamingMessage`。模型流形成最终消息后发 `message_end`，Agent 才把该消息追加到正式 `messages`，再等待订阅者。

AgentSession 在构造时订阅 Agent；它的 `_handleAgentEvent` 在 `message_end` 上调用 SessionManager 保存 system / user / assistant / toolResult 等消息。`message_end` 表示这条消息已经定稿，**不等于任务成功**：一条带 `stopReason: aborted` 的 assistant 消息也可以定稿。

| 状态 | 本课实现中的位置 | 意义和边界 |
| --- | --- | --- |
| 当前输出片段、待执行工具集合 | Agent 的 `streamingMessage`、`pendingToolCalls` | 运行与显示状态；结束会清理，不是恢复用的程序计数器 |
| 定稿消息 | Agent 的 `messages` | 内存上下文；Agent 核心本身不负责写会话文件 |
| 会话记录 | SessionManager 的 JSONL entries | 开启持久化时逐条写入；每项含 id / parentId，支持按分支重建 |
| 下一次模型输入 | `buildSessionProjection()` | 从当前分支记录生成；考虑压缩和上下文编辑，并非无条件把全部历史交给模型 |
| 文件修改、外部请求等实际效果 | 工具及外部系统 | 与会话写盘不在同一个事务里；停止或重读会话不等于撤销效果 |

`_installAgentRequestProjection` 注册 `prepareRequest`，在每次模型调用前用 SessionManager 的 projection 建立规范上下文；`_refreshFinalizedContext` 也从同一 projection 更新 Agent 内存。这能解释为什么“保存的会话记录”和“下一次模型实际看到的消息”需要明确的转换层。

SessionManager 的 `_persist` 有一个有用细节：仅有模型选择、系统设置等启动记录时先不创建文件；一旦存在 user 或 assistant 消息就首次写文件。用户消息在首次模型调用前已经经过 `message_end`，所以首次回复失败也有机会留下用户请求。这里以启用持久化、写入成功为前提，不能进一步宣称断电无损或跨系统事务一致。

相关源码：[事件归约](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent.ts#L575)、[请求投影接线](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/coding-agent/src/core/agent-session.ts#L823)、[JSONL 写入](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/coding-agent/src/core/session-manager.ts#L1160)、[分支投影](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/coding-agent/src/core/session-manager.ts#L544)。

## 4. 中断：停止、留档、继续是三个动作

### 4.1 停止当前执行

产品层 `AgentSession.abort()` 标记取消意图，取消重试、压缩等相关活动，调用 `Agent.abort()`，再等待会话 idle。核心 `Agent.abort()` 只触发本轮 `AbortController`；同一个 signal 传给模型流和工具执行。

所以这属于协作式取消：模型适配器和工具必须响应 signal。当前代码等待工具的执行 Promise，不能仅凭信号发出就保证工具立即停止。已经完成的写文件或外部请求，也没有因 abort 自动回滚。

模型流若以 `aborted` 最终消息返回，该消息会经过正常的 `message_end` 留存链，再由 loop 发出 `turn_end` / `agent_end` 退出。若 executor 抛错，Agent 另有 `handleRunFailure` 形成错误或取消消息。两条路径分开理解，不假设任意异常都能保存流中的全部前缀。

`agent_end` 之后，Agent 还要等被 await 的订阅者结束，最后 `finishRun` 清理 streaming / pending 等状态并解除忙碌。事件已经发出与对象已经 idle 有时间差。产品层还可能有自己的收尾，因此会话层 `waitForIdle` 与核心的等待范围也不同。

源码：[核心取消](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent.ts#L349)、[会话取消](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/coding-agent/src/core/agent-session.ts#L2576)、[工具 signal](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent-loop.ts#L830)。

### 4.2 继续之前必须知道恢复什么

核心 `Agent.continue()` 检查消息尾部：

- 无消息或只有 system：拒绝。
- 尾部是 assistant：先尝试消费已排队的 steering，其次 follow-up；两者都没有时拒绝直接继续。
- 非 assistant 尾部：进入 `runAgentLoopContinue`，用现有上下文发起新模型调用；仍须满足转成供应商输入后的角色契约，不能理解成任何自定义消息都可直接续跑。

因此，保留了一条 aborted assistant 消息，不代表下一句 `continue()` 一定可以从该模型输出的中间继续。读取会话也只是重建上下文，不会重建 JS 调用栈、在途网络连接或工具执行到一半的内部变量。产品层有错误重试等额外策略，但不能用它们反推核心 API 支持任意断点续跑。

### 4.3 答疑：新模型请求为什么仍然叫“继续任务”

用户问“弄到一半，难道是重新发出第二次模型请求？”需要把任务进度和模型请求次数分开。若第2次生成已真正取消，之后继续通常需要新的请求尝试；它可以带着原任务、已完成工具结果，以及产品选择保留的输出上下文，不必把整个任务从头重做，也不保证从取消前的下一个token逐字续接。只断开界面而后台仍运行是另一种情况，不能当成已取消生成。

```text
user：读取配置并分析
assistant：请求读取工具              ← 模型请求#1
toolResult：配置内容                 ← 已完成并留档
assistant：分析了一半，stopReason=aborted ← 模型请求#2被取消
user：继续分析                       ← 显式的新输入
assistant：结合前面的配置继续分析       ← 新请求尝试#3
```

“新请求”不等于“工具重跑”。工具结果在上下文中使模型有机会复用它；若需要程序保证不重复执行有副作用的动作，还须独立的执行状态/幂等设计，不能只依赖提示词。

本课固定源码的两个入口要分清：`agent.prompt("继续分析")`会新增user消息并用现有历史启动请求；直接`agent.continue()`不自动添加这条user消息。当尾部是aborted assistant且队列为空时，后者抛错；官方agent README也给出先`agent.steer(userMessage)`再`agent.continue()`的示例。若尾部已经是可用的toolResult，则该方法可以直接从现有上下文请求模型。

因此，上一轮单独强调“assistant尾部拒绝”容易造成误解。准确边界只是这个核心方法的输入契约，尚不能代表终端产品的“继续”操作；本课没有追UI按钮接线。来源：[固定Agent实现](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent.ts#L380)、[固定README](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/README.md)。

## 5. 与现有 agent-lab 对照

| 问题 | pi 本课已读路径 | 当前 lab |
| --- | --- | --- |
| 一句任务多步执行 | model → toolResult → model 循环，另有事件/队列/边界 hook | `app/services/agent.py:run_agent` 已有循环；独立图 `langgraph_agent.py` 用条件边表达同一主链 |
| 失败后保留什么 | 定稿消息逐条进入 SessionManager；内存显示状态另行管理 | 原生异常携带真实模型调用记录，交路由处理；这不是完整执行检查点 |
| 保存后怎样继续 | 从会话投影生成模型上下文；核心 continue 有尾部角色限制 | 独立 LangGraph + checkpointer 保存状态和待执行节点，可以显式继续失败节点 |
| 等人确认 | 本课没有核验一套持久化审批流程，不能将 abort 当审批暂停 | `langgraph_approval.py` 在工具前 interrupt，调用方以 `Command(resume=...)` 恢复 |
| 工具错误 | 工具执行异常通常转为带 isError 的工具结果，模型有机会看到 | 原生/教学图工具错误抛为 `AgentToolError`，当前链结束；这是不同的错误策略 |

已有测试 `tests/test_langgraph_agent.py:test_model_timeout_resumes_saved_tool_result_after_reopen` 的断言明确检查：工具结果已保存、`snapshot.next == ('model',)`，重开 SQLite 后 `ainvoke(None)` 只重试模型，工具执行次数仍为一次。该测试是预设模型 HTTP + 真实本地图/SQLite/计算器的限定证据；本课只读测试，没有重跑，也不能据此宣称进程崩溃或外部写操作幂等已经验证。

### 5.1 同题横向参考：pi之外的当前官方设计说明

2026-11-06在线核验；下表后两项为官方文档层面的行为说明，未固定实现源码、未安装实测，不能与pi固定源码证据混为一谈。

| 项目与来源 | 当前说明中的具体行为 | 本专题的设计启发 |
| --- | --- | --- |
| [pi核心固定源码](https://github.com/earendil-works/pi/blob/96667f342a8da98ec7969caee7f920ace104436f/packages/agent/src/agent.ts#L393) | 核心continue检查消息尾部及队列；prompt可追加新输入 | 产品继续动作与底层方法名需要分开追踪 |
| [Claude Code工作机制](https://code.claude.com/docs/en/how-claude-code-works#interrupt-and-steer)、[会话恢复](https://code.claude.com/docs/en/sessions) | Esc停止后等待下一指令或发送排队消息；运行中纠正可在工具完成后读取；恢复会话保留历史/工具结果，先前进程结束时未完成的工具不自动重跑 | 停止、纠正、重开会话是不同操作；工具完成与下一步调度之间有交互边界 |
| [Hermes CLI](https://hermes-agent.nousresearch.com/docs/user-guide/cli#redirecting-the-agent-mid-turn) | 区分interrupt/queue/steer；interrupt重新开始模型生成并保留已显示推理与已完成工作；steer在工具结果边界交付，queue准备下一轮 | 用户可以感知为当前任务继续，底层仍可能重新请求模型；产品应明确何时接受纠正 |

另核对[OpenCode当前V2快捷键文档](https://dev.opencode.ai/v2/docs/cli/keybinds/)含`session.interrupt`与排队输入入口；仅有快捷键不足以判断恢复、持久化或取消工具的实现，本轮不补造结论。后续专题按相关性轮换主读，不固定只读pi。

## 6. 完整场景回顾与设计选择

正常路径：用户提交任务 → user 消息定稿并留档 → 模型提出读取请求 → assistant 工具请求留档 → 工具读取并形成结果 → toolResult 留档 → 下一次模型读到结果再行动 → 最后无继续条件时结束。

分支 A：工具已完成，下一次模型输出期间用户停止。此前已写入的请求和工具结果仍可保留；当前响应若以取消消息定稿则也留档；瞬时显示状态随后清理。后续新任务可以利用这些上下文，但不能宣称从模型流的某个 token 原地恢复。

分支 B：工具已经改变外部世界，却在结果留档前进程退出。消息文件本身不能证明该动作没执行，更不能保证自动重试不会重复执行。对真实写操作，是否要业务动作记录、结果核对或幂等设计，取决于心屿接入时的具体动作；这里是设计推论，未新增实现任务。

值得带到心屿的判断：先区分已确认消息、显示中的片段、待运行步骤和业务动作结果，再决定停止/继续按钮的语义。普通聊天的“继续”可能只需从上下文发起新请求；真正的人工审批和跨步骤恢复，则需要明确的流程状态及恢复入口。不能仅因消息有落盘，就显示“已暂停，可从原处继续”。

本课不改 lab 核心、不新增测试，也不将专题记为已经体验验收。下一步先由学习者解释下面的同一个场景，再视需要选择一个最小回放验证：

> 读取工具已经完成，第二次模型响应输出一半时按停止。哪些事实应该保留？哪些状态可以清理？之后点“继续”，依据什么判断应重调模型、重跑工具，还是先请求用户输入？
