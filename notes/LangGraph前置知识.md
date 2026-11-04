# LangGraph 前置知识

本主题帮助阅读后续状态图，不代表已把现有Agent迁移到LangGraph。正式进度以[学习路线第14节](./agent-lab总体学习路线.md#14-当前下一步)为准。2026-11-04 核验本机安装版本为 `langgraph==1.2.19`。

## 为什么从原来的Agent循环出发

[原生run_agent](../app/services/agent.py)已经包含流程：调用模型→判断工具请求→执行工具→回传结果→继续调用，或结束/报告错误。`model_calls`、`additional_messages`、`knowledge_sources`是流程携带的数据；`if`和`for`控制下一步。

LangGraph将数据、步骤和流向显式表示为State、Node和Edge，并提供后续持久化/暂停恢复等机制。图中可以有分支和循环，不局限于只能向前的DAG。每个节点不必调用模型，纯Python计算也能成为节点。

## 需要的Python基础

| 基础 | 对应用途 |
| --- | --- |
| 字典读写 | 读取当前State，返回部分更新 |
| 函数对象 | 注册节点函数，执行时再由框架调用 |
| 类型标注与TypedDict | 描述状态字段；不把类型声明当作运行时数据 |
| async/await | 异步节点等待模型/工具；使用编译图的ainvoke执行 |
| if与有限循环 | 理解条件边与停止规则 |

不要求先学图论算法。本节先用顺序图，不展开并行调度。

## State：每次流程运行的数据

```python
from typing import TypedDict

class DemoState(TypedDict):
    question: str
    model_calls: int

initial: DemoState = {"question": "计算2+3", "model_calls": 0}
```

`TypedDict`来自Python标准库typing；DemoState描述字典形状，initial才是运行时数据。它本身不做Pydantic式的运行时字段类型校验，不提供model_validate等方法。

State也不自动等于项目的长期记忆、SQLite会话或全局变量。跨次运行续接需要后续明确配置checkpointer及会话标识。节点通过返回更新与框架通信，不依赖直接修改入参字典来更新状态。

## Node：读取状态、返回更新的函数

```python
def count_call(state: DemoState):
    return {"model_calls": state["model_calls"] + 1}
```

这个纯本地例子只演示计数，不请求真实模型。输入是当前状态，输出只包含本节点要更新的字段：

```text
输入：{"question": "计算2+3", "model_calls": 0}
更新：{"model_calls": 1}
合并后：{"question": "计算2+3", "model_calls": 1}
```

未返回的question保留；返回的model_calls默认替换该字段。`return {"model_calls": 1}`表示写入1，不表示自动加1。

## Edge：下一步运行谁

固定边连接已知下一节点。条件边由路由函数读取状态并返回下一步的选择。例如有工具请求时走工具节点，无工具请求时结束；预算耗尽仍需明确处理。

START与END是从langgraph.graph导入的特殊标记，表示入口与结束，不是需要调用的模型或业务函数。

## 搭图与运行分开

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(DemoState)
builder.add_node("count", count_call)
builder.add_edge(START, "count")
builder.add_edge("count", END)
graph = builder.compile()
result = graph.invoke(initial)
```

| 写法 | 作用 |
| --- | --- |
| StateGraph(DemoState) | 创建使用该状态结构的图构建器 |
| add_node("count", count_call) | 注册节点名及函数对象，此时不执行函数 |
| add_edge(...) | 声明节点流向 |
| compile() | 校验并生成可运行的CompiledStateGraph，不运行业务流程 |
| graph.invoke(initial) | 同步运行这个只有同步节点的示例图 |
| await graph.ainvoke(initial) | 异步运行图，可用于后续异步模型节点 |

builder、graph和count是此处取的变量/节点名，不是特殊语法。注册时传count_call，不写count_call(...)；后者会在搭图时就调用函数。

同样叫ainvoke，行为取决于接收对象：模型的ainvoke执行模型步骤，编译图的ainvoke执行图中的流程。本例未指定输出schema，得到最终状态字典；其他图可以单独定义输出范围。

## Reducer：同一字段怎样合并更新

字段默认用新值替换，列表也一样：旧值["旧"]加上节点更新["新"]，结果默认是["新"]。

```python
from operator import add
from typing import Annotated, TypedDict

class AppendState(TypedDict):
    items: Annotated[list[str], add]
```

Annotated给基础类型list[str]附加元数据；普通Python不会因此自动执行add。LangGraph读取该元数据，把add作为此字段的合并规则，按add(旧值, 更新值)得到["旧", "新"]。

真正聊天消息可用langgraph.graph.message.add_messages；它按消息ID合并，新ID通常追加，同ID更新已有消息，不等同于永远简单拼接。使用它时再结合真实消息展开。

并行节点同时更新默认替换字段时可能被框架拒绝，不应推断为任意“最后写入者获胜”；那时要专门设计reducer。本节不引入并行图。

## 边界与下一步

数据合并、运行流向、错误策略是不同职责。LangGraph不会凭空替应用定义模型次数预算、授权或业务事务；checkpoint和人工确认需要明确接入，也不能据使用框架宣称已具备。

本轮纯内存探索实测：节点部分更新后question保留、计数变1，初始输入字典仍为0；默认列表更新替换，Annotated[list[str], add]按追加合并。没有调用模型或改变现有Agent。第一次实践会先围绕最小顺序图及状态更新，不直接重写整个Agent。

## 我的理解

用户已概括：节点拆开方便复用，也可以组织workflow；默认字段原值为1、节点仍返回1时，最后还是1，没返回的question仍保留。这部分判断正确。

讲解已补充：START→count和count→END是两条边，count只是中间唯一业务节点；initial是自取的输入变量名，invoke才启动流程；Annotated挂合并规则，由LangGraph调用add；框架还负责调度节点与选择流向，不只是修改字典。“未更新则保留”指同次运行内的状态，跨次续接另需配置。上述补充不据一次OK宣称全部掌握，后续通过顺序图实践核对。

首次顺序图实践使用[PreviewState](../app/services/langgraph_basics.py)的question/normalized_question/preview/trace；两个节点分别提交部分更新，trace声明add时只返回本步新增项，不手动带上旧轨迹，避免重复追加。


## 首个演示图的用途

prepare_question只做strip，render_preview只拼接预览字符串。这两步没有实际问答业务价值，目的是用最小可观察结果验证上游更新能被下游读取，以及字段保留和reducer合并。question是原始输入，normalized_question是第一步产物，preview是第二步产物；trace是节点手工提交的执行标签，不是自动日志。

真正业务节点可以先请求模型、执行工具或完成其他处理，再把结果作为State更新交给后续节点。演示节点的工作简单，不意味着LangGraph节点只能赋值；本例跑通后回到与Agent相关的流程，不继续扩展纯预览功能。

首次顺序图的预期已由[真实内存图测试](../tests/test_langgraph_basics.py)验证：原问题保留，派生字段更新，下游读取上游结果，轨迹仅追加本步标签，原始调用输入未变。该结果证明本例状态协议，不等于已实现真实Agent图。
