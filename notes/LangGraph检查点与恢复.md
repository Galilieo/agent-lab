# LangGraph 检查点与恢复

> 当前检查点（2026-11-05）：内存/SQLite存取、工具前人工确认及后续模型超时后恢复已离线验证，目标10 passed、全量159 passed。检查点/确认功能提交8876380、文档408fce3；恢复测试已本地提交38527e6，阶段总结及说明随收口docs检查点提交。以下保留概念探索、RED和修正过程，以最新核验段落为准。恢复场景仅覆盖同进程关闭/重开连接，进程重启与外部写入幂等仍未验证。

本笔记承接[模型/工具图](../app/services/langgraph_agent.py)，解释跨次状态需要的概念并记录逐步验证。正式进度以[路线第14节](./agent-lab总体学习路线.md#14-当前下一步)为准；概念探索与正式离线测试分别记录。

2026-11-05核验本机`langgraph==1.2.19`，并阅读本机`StateGraph.compile`、`InMemorySaver.get_tuple`、`StateSnapshot`及[官方检查点文档](https://docs.langchain.com/oss/python/langgraph/checkpointers)。

## 最初的问题：接线前缺少什么

接线前`build_calculator_graph`以`builder.compile()`编译，没有配置checkpointer；节点之间可以沿同一次运行传递State，但没有跨调用查找已存状态的机制。后续已增加可选checkpointer参数，调用方可持有带存储的图；原`run_calculator_graph`仍每次构建未配置检查点的独立图，不自动恢复。

设想模型已经给出工具请求，流程暂时停止，稍后还要继续：只存最终聊天正文不足以知道原始工具请求、已有调用记录和下一步应运行的节点。检查点要保留流程可恢复的数据和调度信息。

## 四个概念

| 名称 | 含义 | 当前图的例子 |
| --- | --- | --- |
| State | 当前流程携带的业务数据 | question、model_calls、additional_messages等 |
| checkpoint | 某个执行边界保存的检查点 | 保存State及后续调度所需的信息 |
| checkpointer | 负责保存、读取检查点的组件 | InMemorySaver；后续可换数据库实现 |
| thread_id | 定位同一条状态历史的应用标识 | 同一个计算流程使用相同标识 |

顺序图可以先理解为输入处理、模型节点、工具节点等步骤边界产生检查点。框架严格按super-step（一次调度轮次）组织；本例节点顺序执行，暂不引入并行节点的检查点细节。

checkpoint不是Python函数执行栈快照，不会把函数暂停在任意一行。恢复执行会按照保存的图进度调度节点；失败或中断节点可能从头执行，因此外部写入不能仅靠checkpoint保证不重复。

## 最小接线的写法与每个新名字

下面是接线形状，**不是当前文件已经提供的可直接调用入口**；当前builder在构建函数内部，正式实践会先设计参数怎样传入。

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "calculator-demo-1"}}

result = await graph.ainvoke(initial, config=config)
snapshot = await graph.aget_state(config)
```

- `InMemorySaver`是框架提供的类；`checkpointer`是自取的变量名，保存这个类的实例。检查点放在实例维护的内存中。同一进程也不能每次创建新实例再期待自动找到旧数据；进程退出后其数据会丢失。
- `compile(checkpointer=...)`在已有图的编译步骤接入存取组件，不立即执行节点。
- `config`是普通字典变量；`configurable`和`thread_id`是框架识别的配置键。这份配置用于定位状态，不属于传给模型的prompt，也不是State里自动新增的字段。
- `initial`仍是本次输入状态变量；图的`ainvoke`执行流程。有checkpointer时，已有线程的新输入按字段reducer合并，不会自动清空旧State。
- `aget_state`是编译图的异步读取方法，返回`StateSnapshot`。读取本身不运行模型或工具；`get_state`是其同步版本。不是所有名为`a...`的方法都执行整张图。
- `snapshot.values`是快照中的业务状态，`snapshot.next`是下一步待执行的节点名元组。已正常结束时`next == ()`；未创建过的线程也可能没有待执行节点，因此不能仅凭空元组判断线程存在。
- `checkpoint_id`标识这条历史中的某一个检查点；`thread_id`标识整条历史。第一步只读最新状态，不指定历史检查点。

`thread_id`不是操作系统线程，也不代表登录用户。一个用户可以有多个会话或工作流；同一存储空间内独立流程应使用不同标识。标识本身不承担项目的会话归属或权限校验。

## 保存在哪里，与业务SQLite有什么关系

| 机制 | 保存内容及用途 |
| --- | --- |
| 当前业务SQLite | 聊天消息、模型调用日志、长期记忆等业务记录 |
| 图checkpointer | State及调度信息，用于查看与恢复流程 |
| InMemorySaver | 在内存中实验checkpointer协议，不验证重启后恢复 |
| 文件或数据库checkpointer | 后续通过真实文件/连接验证跨实例或跨进程读取 |

二者可以并存。用相同的`conversation_id`或自行映射为`thread_id`，也不会让现有业务表自动变为检查点存储；需要明确各自的生命周期、状态范围及写入职责。本阶段尚未迁移原生`/chat`。

## 找到旧状态以后，不同输入意味着什么

在同一线程已经存在检查点的前提下：

| 调用方式 | 含义 |
| --- | --- |
| `await graph.aget_state(config)` | 只查看保存的状态，不执行节点 |
| `await graph.ainvoke(new_input, config)` | 将新输入合并到旧状态，再从入口开始处理新工作 |
| `await graph.ainvoke(None, config)` | 尝试继续尚未完成的工作；若已正常结束，就返回保存结果，不重跑已结束的流程 |
| `Command(resume=...)` | 回答动态interrupt的专用输入，留人工确认主题展开 |

复用`thread_id`并不单独决定是否恢复。读状态、发送新问题、继续失败工作、回答人工确认，应按目的选择不同调用。

当前`model_calls`和`additional_messages`都用`add`追加。旧列表加`[]`还是旧列表；不能将同一线程中的`model_calls: []`当成每轮预算清零方案。检查点接线前要明确State表示一轮任务还是整个会话；第一步采用一条thread对应一轮计算任务，不直接把本例改成跨轮聊天Agent。

## 一次性离线探索的证据

2026-11-05通过终端内联脚本，用当前`CalculatorState`、两个真实节点及条件路由重建相同的图，编译时传入`InMemorySaver`。探索只将`generate_langchain_result`替换为`offline_model`：接收同样关键字参数，记录问题并直接返回一个预设`LLMResult`，不执行HTTP/SDK。这与现有测试只替换HTTP传输的证据范围不同。

临时`compile_with(saver)`只注册已有节点与边并接收saver；临时异步`main`依次运行图、重建图、读取快照和比较隔离。它们没有写入应用源码或新增正式pytest用例。

实测结果：

- 图正常结束后，同一saver、同一thread重新编译仍读回原问题和`LLMResult`；`snapshot.next == ()`。
- 读取前后预设模型函数调用次数均为1；对已结束图再传`None`，次数仍为1。
- 换thread读取`values == {}`；换成新的内存saver后，即使用原thread读取也得到`{}`。
- 本机反序列化自定义`app.services.llm.LLMResult`时提示未显式注册类型。后续接线要讲清序列化，并为本图实际使用的`LLMResult`及`LLMToolCall`配置明确类型支持；不使用允许任意类型的全开设置。本次有提示但运行完成，不能据此声称完成未来版本兼容。

这验证同进程内的状态存取与隔离，不证明模型行为、数据库持久化、进程重启恢复或失败重试。正式测试基线仍是已提交图单元的154 passed，没有把一次探索算作新增通过用例。

## 我的理解

用户已说明：检查点可用于出错后选择保存状态重新执行；新建内存saver不能获取旧实例数据，进程结束数据丢失；读取检查点不执行节点。用户进一步指出新独立任务必须分配不同编号，同一次运行内部保持一致。已明确：本例一轮任务一个thread_id，失败后恢复沿用原编号；同存储内无关任务复用编号会误读/合并旧状态，内存和数据库均有此问题，不一定表现为重复键报错。

后续以应用接线验证这些判断，不据口头回答宣称已完成持久化或失败恢复。

## 本次局部实践：传入存取组件

已在[图模块](../app/services/langgraph_agent.py)准备`create_calculator_checkpointer()`。它用`JsonPlusSerializer(allowed_msgpack_modules=[LLMResult, LLMToolCall])`声明本图自定义类型，再以`InMemorySaver(serde=serializer)`创建存储。`serde`是框架接收序列化/反序列化组件的参数名。这里只配置类型转换，图运行时由框架调用，不需要业务节点自己写二进制。

序列化是把对象字段转为可存储的数据，反序列化是读回字段并还原对象；不是把Python对象引用直接塞入内存字典。显式支持两个类，是因为`LLMResult.tool_calls`中还嵌套`LLMToolCall`，读取后仍要支持`.answer`、`.call_id`等属性。一次性本地往返探索已确认两个类型和字段值还原相等，没有先前未注册类型提示；这不代替图接线测试。

已导入`BaseCheckpointSaver`供核心参数标注使用。它是框架存取组件的共同基类；`BaseCheckpointSaver | None = None`表示可传组件或不启用，允许以后接入其他符合框架接口的实现。调用方负责复用saver及分配任务编号，构建函数只接收并传给`compile`。当前`run_calculator_graph`仍是未配置检查点的独立入口；本次测试直接持有编译图并调用其`ainvoke`/`aget_state`。

用户局部任务只有两处：`build_calculator_graph`增加仅限关键字的可选`checkpointer`参数；函数末尾使用`builder.compile(checkpointer=checkpointer)`。原节点与边继续复用，默认不传时保持原有行为。尚未代写这两处。

新增测试`test_checkpoint_reads_saved_calls_and_isolates_independent_tasks`，复用原`offline_graph`与`calculator_request`，未新增fake：

1. 预设三条HTTP响应：A的工具请求、A的最终回答、B的直接回答。真实HTTP请求到来才消费下一条，列表本身不触发运行。
2. 测试内异步`scenario`把有先后依赖的await放在同一个事件循环，最外层`asyncio.run(scenario())`运行它；该函数不是框架API。
3. A用自己的thread_id运行，真实计算后有两次HTTP；重新编译图但复用saver，读回状态，检查嵌套类型、原始参数/调用ID、工具结果、最终回答及空next，HTTP仍为两次。
4. A已结束，再传None，返回已有结果且HTTP仍为两次；这不是失败恢复用例。
5. B用另一个thread_id，先读为空，再发送新输入，只产生一次模型调用；B只有自己的记录，A的快照没有变化。总HTTP三次、工具仅尝试一次。
6. 换成新内存saver，用A原编号也读为空，HTTP次数仍为三次，证明相同编号不能代替共享存储。

目标RED为`1 failed, 5 passed`（1.04秒）：失败是构建函数不接受`checkpointer`关键字，无收集错误；原有五种图场景通过。当前等待用户补核心后再验目标及全量，未新增数据库依赖、未运行真实模型、未提交本单元。

补写后核验：用户完成checkpointer参数及compile接线；误撤的新增测试与导入已恢复，核心修改保留。目标6 passed（1.17秒）、全量155 passed（1.94秒）、diff检查通过。证明本例内存保存/读回、类型还原、任务隔离及正常结束后不重跑；数据库持久化、重启后恢复及失败恢复仍待实践。本单元未提交。

## 下一实践：SQLite文件与连接生命周期

用户表示补写完成并继续；再次核验目标6 passed（1.12秒）、全量155 passed（2.02秒）。不再重考fixture/prepare；已记录其返回函数、解包及闭包链路，后续按需要回看测试源码。

本机新增`langgraph-checkpoint-sqlite==3.1.3`与`aiosqlite==0.22.1`，解析时还新增扩展的依赖`sqlite-vec==0.1.9`，未升级既有包。pyproject.toml声明直接使用的SQLite saver及aiosqlite依赖，uv.lock锁定解析结果。官方扩展来源见[PyPI](https://pypi.org/project/langgraph-checkpoint-sqlite/)，连接与构造接口以本机安装源码为准。

图的状态、节点、边与thread_id规则继续复用。检查点写到单独文件；它不是app/database.py中的会话/消息/记忆表，也不会自动迁移既有业务数据。图异步运行时使用`AsyncSqliteSaver`配合`aiosqlite`连接。

### 新模块与共用配置

[langgraph_checkpoint.py](../app/services/langgraph_checkpoint.py)负责序列化配置和连接生命周期。`create_checkpoint_serializer()`是将原内存工厂的两类自定义记录配置原样抽出，内存工厂现在调用它；SQLite组件也使用它，避免两种存储的类型还原配置不一致。图构建与节点核心不变。

待用户补写的`open_calculator_checkpointer(database_path)`负责打开专用SQLite文件、构造saver并向调用方提供。父目录由调用方准备，图运行和读取必须发生在连接仍打开的上下文内。框架内部按需setup建表，本机aget_tuple源码已确认会调用setup，不另写业务建表SQL。

### async with、装饰器与yield

普通`with`提供进入/退出资源范围的协议；`async with`用于进入和退出需要异步等待的资源。`await`等待一次操作完成，`async with`管理整段代码期间的资源。

`@asynccontextmanager`来自Python标准库contextlib，让带yield的异步函数能够用于`async with`。调用装饰后的函数得到上下文管理器；进入上下文后执行到yield，把该值交给`as`后面的变量，并暂停函数；调用方块执行完或抛异常后，函数继续清理，内部连接上下文负责关闭。

`AsyncIterator`来自标准库collections.abc，`AsyncIterator[AsyncSqliteSaver]`描述这个原始异步生成器交出的值类型。这里yield一次用于资源借用，不是在循环发送多个模型片段；装饰后的调用方使用async with，不需要自己async for。

完整局部参考（尚未代写核心）为：

```python
@asynccontextmanager
async def open_calculator_checkpointer(
    database_path: str,
) -> AsyncIterator[AsyncSqliteSaver]:
    """提供块内可用的检查点组件，退出块时关闭连接。"""
    async with aiosqlite.connect(database_path) as connection:
        saver = AsyncSqliteSaver(
            connection,
            serde=create_checkpoint_serializer(),
        )
        yield saver
```

外部`async with open_calculator_checkpointer(path) as saver:`里的saver，就是这里yield交出的对象；yield后函数尚未结束，内部connection仍打开。外部块退出时才完成清理。不是return后拿一个连接已关闭的saver继续运行。

当前占位的raise及其后不可达yield应整体替换；不可达yield只为让RED阶段仍保持异步生成器形状，从而准确抛出NotImplementedError，不是正式业务逻辑。

### 新测试怎样验证

新增`test_sqlite_checkpoint_survives_connection_reopen`，复用已有offline_graph和calculator_request。pytest内置`tmp_path`提供临时目录Path，`tmp_path / "graph-checkpoints.sqlite3"`拼接文件路径，`str(...)`转成连接函数接收的字符串。未引入新的fake或fixture函数。

测试内异步scenario先打开文件，用A编号实际跑计算器两轮，保存before快照；退出第一个上下文后重新打开同一文件，创建新的连接、saver和编译图，读取after。检查两个saver与连接确为不同对象、状态和嵌套记录类型保留、最终回答与调用ID正确、新任务B读取为空。总HTTP仍是两次、计算器一次，证明读回没有请求模型或重算。

这次覆盖同一进程关闭后重新连接，不等于已验证进程重启、失败节点续跑、崩溃恢复或生产运行。

目标RED为1 failed / 6 passed（1.57秒），新增场景明确失败于open_calculator_checkpointer的NotImplementedError；原六种场景通过，锁文件离线检查及diff检查通过。依赖变更后尚未完成全量GREEN；最近全量155 passed是新增数据库场景前的结果。用户补写后再验目标及全量，无真实模型请求，不自动提交。

补写后的实际失败：用户理解serde用途，构造saver已补，但yield saver放在内部async with块外，导致交出对象前连接已经关闭。目标1 failed / 6 passed（1.44秒），graph.ainvoke首次读取时，SQLite saver试图重启已关闭连接的工作线程，报threads can only be started once。应将yield saver缩进到内部连接块中，与saver赋值同级，并移除旧占位注释；原问题不需要改图调度或线程配置。留用户修正后再验，不能记为持久化GREEN。

修正后核验：用户已修复资源范围并清理占位注释。目标7 passed（1.24秒）、全量156 passed（2.21秒）、diff及离线锁检查通过。本例真实SQLite文件重开连接读回成立，不扩成进程重启/故障恢复结论；本单元未提交。

## 人工确认前置：interrupt与Command

下一步拟在模型提出工具请求之后、执行工具之前增加确认点。计算器用于观察机制；正式动作是否要求确认，应按业务需要判断，不要求所有计算都人工确认。以下是接线前的机制说明，当前计算器图还没有确认节点。

```text
model提出工具请求 → approval请求人工决定并暂停
                           ├─ 同意 → tools → model
                           └─ 拒绝 → 应用结束该操作
```

`interrupt`从langgraph.types导入，用在节点内部。传给它的字典/字符串是应用可以展示的确认内容，需可JSON序列化；例如工具名、原始参数和确认问题。第一次执行到这里时，框架保存暂停信息并让本次ainvoke返回；本机当前默认API在返回字典的__interrupt__中提供内容。应用展示、用户提交决定等流程需要另行接入，它不会自行生成按钮或让模型代替人同意。

`Command`是同模块的类；调用方以Command(resume=True)或Command(resume=False)作为下一次ainvoke的输入，并使用原检查点存储及thread_id。它是调用方发送给框架的恢复指令对象，resume里的值会成为节点内interrupt调用的结果；同意后具体走tools、拒绝后具体怎样结束仍由应用图决定，不是框架自动实现业务分支。

```python
# 节点内部的机制示意，尚未接入当前图
decision = interrupt({"question": "允许执行本次工具请求吗？"})

# 调用方恢复已暂停的图，使用原config
continued = await graph.ainvoke(Command(resume=True), config=config)
```

恢复时该节点从头运行，并在interrupt位置取到提交值，再继续后续代码。它没有保存Python函数栈；interrupt前的代码可能再次执行。确认节点前部只整理待审内容，工具执行放在明确同意后的工具节点。模型节点此前已完成并保存时，不应为回答这次确认而重新请求同一轮模型。

2026-11-05核验本机函数说明及[官方interrupt文档](https://docs.langchain.com/oss/python/langgraph/interrupts)，另做一次纯本地单节点内联探索：ApprovalState仅描述approved字段，approval节点在外部entries列表记录进入次数后调用interrupt并返回决定；main注册节点/边并配置内存saver，依次调用初次ainvoke、aget_state和Command恢复。初次返回问题、next为approval、入口计数1；恢复True后approved=True、计数2、next为空。该示例没有模型、工具、HTTP或SQLite，没有写入应用源码或新增pytest；只验证陌生API的暂停与重入语义，不能记为工具审批已实现。

下一步先预测工具执行次数与恢复起点，再安排真实计算器图的局部改动及同意/拒绝测试。身份、权限、并发审批、前端接线及SSE不在当前小单元范围。

## 人工确认的局部任务与测试

用户预测暂停前不执行工具、恢复从确认节点开始，主干正确；补充恢复节点从头运行，但该interrupt取得resume值后继续，不是同一请求永久重新暂停。

[langgraph_approval.py](../app/services/langgraph_approval.py)保留独立图，复用已有模型、工具节点与预算路由。ApprovalCalculatorState继承CalculatorState，包括原列表reducer；只新增tool_approved记录最近一次人的决定，None表示尚未决定，布尔值分别表示同意与拒绝。它不替代身份权限，也不是后续所有工具自动放行的总开关；每次进入approval都为当前最新工具请求重新调用interrupt。

Codex准备build_approval_calculator_graph：必须提供checkpointer，缺失时抛ValueError；注册model/approval/tools，START进入model，原choose_next返回finish时到END、use_tools时到approval，确认路由use_tools到tools、finish到END，tools固定回model，compile时传入checkpointer。继续复用原预算检查，耗尽预算时先报错，不多做人工确认。没有新的模型/工具实现或最终结果映射函数。

用户补写两个函数：

```python
def request_tool_approval(state: ApprovalCalculatorState) -> dict:
    """展示待执行请求并暂停，恢复后记录布尔决定。"""
    latest = state["model_calls"][-1]
    decision = interrupt({
        "question": "是否允许执行本次工具请求？",
        "tool_calls": [{
            "call_id": call.call_id,
            "name": call.name,
            "arguments": call.arguments,
        } for call in latest.tool_calls],
    })
    if not isinstance(decision, bool):
        raise ValueError("Approval decision must be a boolean.")
    return {"tool_approved": decision}


def choose_after_approval(state: ApprovalCalculatorState) -> str:
    """将已校验决定转为条件边标签。"""
    if state["tool_approved"] is True:
        return "use_tools"
    return "finish"
```

这里列表推导将本次全部工具请求整理成基础字段，供调用方展示；保留原始arguments字符串，真正参数校验仍由同意后工具入口负责。一份决定针对本次请求列表整体，不做逐工具编辑或并行审批。恢复值只接受真正bool，不用bool("false")等真值转换冒充同意。节点只提交状态更新，路由只返回控制标签。

拒绝直接END，状态中的tool_approved为False、最新模型记录仍是成功发起的工具请求，可能没有正文；调用方可据此展示取消，不虚构一个新模型回答或把它送给原独立入口的AgentResult映射。

测试test_approval_pauses_before_tools_and_resumes_after_reopen按approved=True/False参数化，pytest分别独立执行同一测试，两种分支有独立临时数据库及fixture。Command只在测试调用方导入，以Command(resume=approved)作为恢复输入，不是发送给模型的消息。默认ainvoke返回的__interrupt__是框架提供的暂停信息，测试检查其中第一个Interrupt的value，不把__interrupt__设计成业务State字段。

observed_approval是新增的观察包装：在外部approval_entries列表追加entered后调用原request_tool_approval，通过monkeypatch替换图注册所取的函数；不替换确认行为或人决定。原offline_graph仍只假HTTP，工具真实运行。fixture/prepare无需重复从头讲。

测试初次模型响应工具请求，断言HTTP一次、工具尝试零、确认负载正确、State尚未提交tool_approved、next为approval、节点进入一次。退出SQLite连接后重开同文件/同编号，重新编译图再发送Command恢复：两分支确认节点均进入两次；同意后HTTP累计两次、真实工具一次，下一模型看到计算结果并给最终回答；拒绝仍HTTP一次、零工具、没有新增交互或伪造回答。最终两者next为空，但拒绝不是正常模型最终回答。

目标RED为2 failed / 7 passed（1.84秒），两例停在request_tool_approval占位，无收集错误，diff检查通过。待用户补写后再验证目标及全量；本轮没有真实模型请求、没有进程重启/前端或身份验收，未提交本单元。

人工确认补写后核验：is None误写造成同意提前结束，定向同意失败/拒绝通过；用户改为is True后目标9 passed（1.15秒）、全量158 passed（2.25秒），diff及离线锁检查通过。两分支的暂停、SQLite重开后恢复、确认节点重入、旧模型不重跑及真实工具执行/拒绝边界成立；没有真实模型请求或进程重启验收。本批未提交，后续进入失败恢复。

## 失败恢复前置：错误退出后怎样继续

本节是下一主题的设计与行为预测，尚未完成故障恢复测试，不计入已有验证成果。2026-11-05核验[官方检查点恢复说明](https://docs.langchain.com/oss/python/langgraph/checkpointers)及[重试边界说明](https://docs.langchain.com/oss/python/langgraph/fault-tolerance)，结合当前call_model/call_tools读取。

计划围绕现有计算器图验证：首次模型成功提出工具请求，工具节点完成并保存结果，第二次模型请求超时导致图抛出AgentRunError；稍后重开同一SQLite文件，以原任务编号继续。

```python
# 连接与图仍需按已有上下文方式准备，config使用原thread_id
snapshot = await graph.aget_state(config)
final = await graph.ainvoke(None, config=config)
```

aget_state只读进度；ainvoke(None, ...)不提供新业务输入，框架从最新检查点尝试未完成工作。不要为这个恢复操作附带历史checkpoint_id，否则会变成指定历史位置的重放。输入None也不是重新初始化空State，已有问题、调用记录、工具消息继续使用。

| 场景 | 调用方输入 | 含义 |
| --- | --- | --- |
| 人工确认暂停 | Command(resume=True/False) | 为interrupt提供决定 |
| 错误退出后继续 | None | 重试未完成工作，没有人工回答值 |
| 新独立任务 | 新输入与新thread_id | 独立任务使用独立历史 |

恢复不等于自动重试：当前图没有配置RetryPolicy，SDK保留max_retries=0；当前先学习调用方稍后显式恢复，不添加多层重试。失败的模型节点从头重新执行，但前面已成功且写入检查点的顺序节点应复用已有结果。待验证场景应从第二次model步骤继续，而不是重跑第一个model或tools。

model_calls当前记录成功且可用的模型结果；超时尝试不新增成功项。计划场景在首次超时后有两次HTTP尝试、一个成功模型结果；若恢复时模型成功，累计三次HTTP尝试、两个成功结果、工具执行一次。当前max_model_calls按成功记录长度计数，不能据它声称跨恢复限制了包括失败在内的全部HTTP尝试；独立尝试日志和总重试预算仍需单独设计，不在此概念带读中自动扩展。

检查点不保存任意Python执行行，也不替外部系统回滚副作用。若某工具已发送消息或写库，却在节点提交状态前失败，重新执行该节点可能重复动作。幂等表示重复提交同一业务操作仍只产生一次效果，常见做法是让外部系统按稳定业务编号去重；本项目当前没有此类外部写入保障，不宣称框架已提供。计算器无外部写入，用它验证先前已完成工具节点不重跑；不能外推为所有工具都能无条件重试。

下一步预测：计算器结果已写入检查点、第二次模型超时后，显式恢复是否应重新执行计算器，以及恢复成功后HTTP尝试数与成功模型记录数。随后准备真实图/临时SQLite/预设模型HTTP的集中失败恢复验证；此处不强造新生产代码。

## 已验证：后续模型超时，重开连接后继续

用户确认失败节点重入范围；已解释历史重放从所选旧检查点重新执行其后节点，最新错误恢复则复用较新的已提交进度。用户认为失败也应留日志，已区分State的成功LLMResult列表与业务model_call表的成功/失败日志：当前独立图未接入原生/chat的persist_agent_run_error，不能把成功列表当完整调用尝试审计。

新增[恢复测试](../tests/test_langgraph_agent.py)中的`test_model_timeout_resumes_saved_tool_result_after_reopen`，不修改业务核心、State或框架接口。现有checkpointer及ainvoke(None, config)已具备目标能力，因此新增的是已有能力的回归证明，没有人为制造占位RED。

复用原offline_graph、calculator_request及pytest的tmp_path，没有新fixture/fake/辅助函数；测试内scenario仍只是把异步顺序操作放入同一事件循环。prepare依次配置工具请求、字符串timeout、最终回答；已有respond遇到timeout抛httpx.ReadTimeout，实际SDK/适配器将其转为LLMTimeoutError，实际call_model再包装AgentRunError。

测试关键步骤和证据：

1. 打开临时SQLite，以原图执行初始输入；`pytest.raises(AgentRunError) as caught`要求该段确实抛出预期异常，退出with后可从caught.value检查异常实例。检查cause为LLMTimeoutError、异常携带记录与State成功列表一致；不是捕获后伪装正常完成。
2. graph.aget_state读失败进度：next为model，成功记录1条，已存tool结果5、调用ID关联正确，HTTP两次、工具尝试一次。
3. 退出第一连接，重开同文件并重建图，读到同样的State与待执行model；读取期间HTTP仍两次。
4. `await rebuilt.ainvoke(None, config=config)`继续未完成工作；最终next为空、回答为预设最终正文，成功记录2条，第一条记录和已存工具交互不变。
5. HTTP累计三次、工具仍一次；第三次和第二次的实际出站messages完全相同，证明使用了相同问题/工具结果，未重跑前面的模型及计算器。

恢复定向1 passed / 9 deselected（1.28秒）；图模块目标10 passed（1.16秒）；默认全量159 passed（2.04秒）；diff及离线锁检查通过。真实图/SDK/适配器/计算器/SQLite，仅模型HTTP预设。未验证真实服务可用性、进程重启、崩溃窗口、历史重放、外部动作幂等、自动重试或生产审计。此次测试与说明未提交。

阶段收口（2026-11-05）：用户要求整理提交后，LangGraph相关11 passed（1.20秒）、全量159 passed（2.11秒），diff及离线锁检查通过。恢复测试本地提交38527e6；第一轮核心机制范围、验证及边界统一见[阶段总结](./LangGraph阶段总结.md)。下一步阶段10先讲SSE事件与HTTP流前置，未自动新增接口或迁移主路由。
