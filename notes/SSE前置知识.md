# SSE 前置知识

本笔记承接[LangGraph阶段总结](./LangGraph阶段总结.md)，进入阶段10的HTTP流式输出。正式进度见[学习路线第14节](./agent-lab总体学习路线.md#14-当前下一步)。当前是概念与源码带读，尚未新增SSE路由或浏览器消费代码。

2026-11-05核验本机FastAPI 0.115.14、Starlette 0.46.2的StreamingResponse源码，以及[WHATWG事件流规范](https://html.spec.whatwg.org/multipage/server-sent-events.html)。不为跟随新版文档自动升级依赖；本机已有StreamingResponse可用于后续接线。

## 现有代码到哪里了

[chat路由](../app/main.py)先检查归属、读旧历史、保存用户问题，再调用原生Agent，最终保存回答和成功调用，处理记忆反馈后返回ChatResponse。客户端此时收到一份完整JSON，不能从该返回值提前获得模型生成中的正文。

[stream_langchain_reply](../app/services/langchain_streaming.py)已经是异步生成器：调用函数先获得可迭代对象，消费时才打开HTTP客户端；chain.astream依次产生AIMessageChunk，函数用yield逐个交出。它可保留空正文片段中的finish_reason/usage，并向外传播读取异常，但不发送本应用HTTP响应，也不写业务数据库。

模型服务到Python应用、Python应用到浏览器是两段独立HTTP通信。模型SDK已经解析上游协议得到Python对象，浏览器不会因此自动收到这些对象；应用还需要选择对外数据契约并编码。

## 四层数据

```text
模型服务增量
→ SDK解析成AIMessageChunk
→ Python异步生成器逐个yield
→ 应用整理并编码SSE事件
→ StreamingResponse逐段写入同一HTTP响应
→ 浏览器积累字节、解析完整事件并更新界面
```

| 层次 | 负责什么 |
| --- | --- |
| AIMessageChunk | 模型片段对象，可含正文或结束/用量信息；不保证一块对应一个字或token |
| 异步生成器 | 按消费进度交出对象，本身不意味着已经发送HTTP |
| StreamingResponse | 接收可迭代内容，逐段发送响应体；不自动把对象变为SSE事件 |
| SSE事件格式 | 用event/data等行及空行表达事件边界，便于客户端识别类型和负载 |

SSE全称Server-Sent Events。客户端先发起请求，服务端在该请求的一个HTTP响应里继续发送事件；不是每个事件都返回一次新的HTTP响应。模型继续生成时，应用可逐步交付正文，不必先收齐全文再切分。

## SSE字节长什么样

```text
event: delta
data: {"text":"你好"}

event: delta
data: {"text":"，欢迎"}

event: done
data: {"finish_reason":"stop"}

```

这是响应体的文本格式，不是Python变量定义：event是字段名，后面的delta是应用选择的事件类型；data是负载文本，本项目拟放JSON，SSE本身并不强制JSON。一个空行结束事件，常用编码末尾是两个换行符`\n\n`；响应媒体类型为text/event-stream，文本按UTF-8处理。

delta/done/error是拟定的应用事件名，不是SSE替我们定义的业务语义。JSON中的text也是应用字段，和模型SDK对象的属性分开。

## 应用先约定三种事件

| 拟定事件 | 客户端怎样理解 |
| --- | --- |
| delta | 追加可展示正文，但不据此判断整轮成功 |
| done | 本接口约定的正常收尾已完成，客户端结束等待 |
| error | 本次流程失败，可保留已显示前缀，但不能标为成功 |

详细负载在下一实践确定。接入业务持久化后，done应在本接口承诺的必要保存成功之后发出；模型finish_reason或上游[DONE]只说明模型协议进度，不自动证明业务入库成功。若连接意外断开、没有收到done，客户端也不能仅凭已有文字判定成功。

空正文模型chunk可能包含结束或usage元数据，不应在收集元数据前统一丢弃；它通常无需变成一个空正文delta。

## HTTP200与业务成功分开

本机StreamingResponse.stream_response先发送http.response.start（状态及响应头），再迭代内容发送http.response.body。已开始的响应不能把先前发出的200改成504；流内部失败需要按事件契约表达，连接断开时也可能根本送不出error。发送响应前已发现的请求校验或归属错误，仍可用常规HTTP状态拒绝。

一次性纯本地探索：frames异步生成器先yield一条delta文本，再抛RuntimeError；send函数只收集StreamingResponse交出的ASGI消息。调用stream_response后实测先有状态200及text/event-stream头，再有正文且more_body=True，随后异常抛出，没有正常结束的body消息。框架不会自动替应用生成done/error事件。

此探索没有启动HTTP服务器、浏览器或调用模型，没有写入应用源码或新增pytest；只验证本机响应发送顺序，不证明网络传输及时性、取消或代理行为。

## 浏览器读取的边界

浏览器原生EventSource会解析SSE并提供监听接口，但其构造接口不提供聊天所需的POST请求体设置。后续聊天POST可以由fetch发送并读取响应流，再使用事件解析器。请求方式和响应采用SSE文本格式是两个问题；此处不先写一套前端。

网络读取块与应用事件没有一一对应关系：一个事件可能分成几次读取，多条事件也可能合并在一次读取中，UTF-8字符也可能跨字节块。客户端要增量解码并积累完整事件后再处理，不把每次read到的数据直接JSON.parse。实际代码应遵循换行/空行协议或复用合适解析器，不能仅按网络块切割。

yield把内容交给响应层，不承诺屏幕立即更新；客户端、服务端和代理缓冲的实际效果需要后续HTTP及浏览器验证。断开/取消如何停止上游读取、如何关闭客户端，以及最终回答何时保存，后续围绕同一请求链展开。

## 本轮边界与下一步

本轮只读现有模型流/chat、核验协议与本机响应源码，并做一次无网络探索。不新增接口、依赖或业务行为，不强造RED，不运行真实模型；全量基线仍是阶段9收口的159 passed，本轮没有重跑它。

下一步先预测：200响应后已经交付部分正文再超时，是否能把同一响应改为504并发送done；以及一次网络读取是否保证是一条完整SSE事件。随后确定应用事件契约，准备局部编码/模型片段到事件的实现和正常/失败验证，再进入HTTP接线。

## 我的理解

用户已正确预测：中途失败应发送error，不能发送done；半条事件不能当完整JSON解析，至少积累完整事件再处理。已补充连接断开时可能无法再交付error，不能据没有错误事件就推断成功。Python端yield对象、HTTP字节发送与客户端消费的实际位置仍随后续接线验证，不据一次OK写成已实现SSE链路。

## 局部实践：模型片段转为事件

新增[app/services/sse.py](../app/services/sse.py)，本层接收已有模型异步生成器，不自行调用模型或写库。当前done仅表示这段普通模型文本流正常完整；之后业务接口若承诺保存回答，业务done需在保存成功之后交付。当前没有HTTP路由，也没有浏览器解析器。

Codex已写三个辅助定义：

- InvalidStreamError：应用自己的异常类型，用于没有正常结束、空正文、非文本或工具请求等不符合本单元契约的输出。
- encode_sse(event_name, data)：只允许delta/done/error事件名；json.dumps将字典转JSON文本，ensure_ascii=False保留中文，allow_nan=False拒绝非标准JSON数值；正文换行自动转义，最终编码为event行、data行及空行，避免正文伪造事件。
- stream_error_payload(error)：超时映射model_timeout，协议不完整映射invalid_model_stream，其他SDK APIError映射model_request_failed；返回固定code/message，不把原始异常详情直接暴露给客户端。

用户补写stream_sse_events。chunks标注AsyncGenerator[AIMessageChunk, None]，表示可异步逐块读取并关闭的生成器，本单元不向生成器额外发送值；返回AsyncIterator[str]，逐个交出已编码事件字符串。APIError是SDK请求错误的共同类型，已核验APITimeoutError属于它；取消及未知错误不并入这些已知错误。

局部完整参考（核心尚未代写）为：

```python
async def stream_sse_events(
    chunks: AsyncGenerator[AIMessageChunk, None],
) -> AsyncIterator[str]:
    """逐块发送正文，正常收尾或已知失败只发一种终态。"""
    combined = None
    try:
        async with aclosing(chunks) as stream:
            async for chunk in stream:
                if (
                    not isinstance(chunk.content, str)
                    or chunk.tool_calls
                    or chunk.invalid_tool_calls
                ):
                    raise InvalidStreamError()
                combined = chunk if combined is None else combined + chunk
                if chunk.content:
                    yield encode_sse("delta", {"text": chunk.content})

        if (
            combined is None
            or not combined.content.strip()
            or combined.response_metadata.get("finish_reason") != "stop"
        ):
            raise InvalidStreamError()
    except (APIError, InvalidStreamError) as exc:
        yield encode_sse("error", stream_error_payload(exc))
        return

    yield encode_sse("done", {
        "finish_reason": "stop",
        "usage": combined.usage_metadata,
    })
```

aclosing仍是标准库contextlib组件，退出时调用输入生成器的aclose，释放其客户端。combined使用AIMessageChunk的加法保留正文、结束及usage，不是只拼字符串；已在本机探索确认空正文stop/usage片段合并后元数据保留。先合并每个chunk，再只对非空正文yield delta，因此空元数据不会漏掉。全部正常迭代后仍要求非空有效正文及finish_reason为stop；即使到达迭代结束，没有stop也发error。usage未知可为None，不虚构Token数。except中yield error后return避免随后再done；本层不吞取消/未知异常。

新增测试在原[test_langchain_streaming.py](../tests/test_langchain_streaming.py)，复用已有offline_stream；prepare仅增加include_finish参数控制是否发送上游finish_reason，默认True兼容旧测试，没有新增fake/fixture。

编码测试故意让正文含中文、引号及换行后的event: done，验证它仍在同一JSON负载内且只占一条SSE事件。转换测试参数化normal/timeout/missing-finish，调用现有stream_langchain_reply获得真实SDK解析的chunk，再传给新转换函数：

| 场景 | 期望事件 | 证据 |
| --- | --- | --- |
| normal | 两条delta及一条done | finish前已有delta；done保留stop及实际usage |
| timeout | 一条delta及一条error | 已交付前缀保留，错误码model_timeout，无done |
| missing-finish | 两条delta及一条error | HTTP与迭代结束但没有stop，错误码invalid_model_stream，无done |

测试内consume仍用asyncio.run执行，直接拆分每次编码函数交出的完整帧检查event/data/空行并用json.loads还原负载。这个拆分不是浏览器网络解析器，不证明半帧缓冲；真实网络块边界仍需后续验证。每例均检查一次模型HTTP及上游关闭，正文前缀按预期保留，不用预设正文推断模型能力。

正确RED：目标3 failed / 3 passed（1.46秒），三例均明确指向stream_sse_events的NotImplementedError；旧两例和新增编码例通过，无收集错误，diff检查通过。最近全量159 passed属于新增这些行为前的基线，当前不是全绿。等用户补核心后再验目标/全量；不新增HTTP、浏览器或数据库接线，不运行真实模型，不自动提交。

## 转换层核验与HTTP接线任务

用户已完整补写转换函数，变量名combind前后一致，是有效的自取名字。初次核验正常场景失败，是Codex写的usage字典精确相等断言过严：真实SDK增加input_token_details/output_token_details两个空字典，属于合法明细，不应为此修改转换逻辑。目标当时1 failed / 5 passed（1.20秒），先前误启动的全量为1 failed / 162 passed（2.25秒）；已修正测试为核对三个核心Token计数并允许附带明细。随后目标6 passed（1.14秒）、全量163 passed（2.01秒），用户核心未改，diff检查通过。

下一步在实际FastAPI应用新增独立POST /stream，仅接收message，接通普通模型文本流。本小步不绑定业务会话、不执行工具或RAG、不写聊天数据库；done仍只表示本接口的模型流正常完成，正式/chat继续原生链路。完整Agent流式、会话持久化、取消及浏览器消费仍按阶段10后续推进，不把此独立端点记为全链路完成。

Codex已准备：

- schemas.py的TextStreamRequest：继承BaseModel，message使用Field(min_length=1)。空字符串在进入路由之前返回JSON422；当前与原输入风格一致，未扩展为全面空白/长度策略。
- main.py的StreamingResponse、TextStreamRequest、stream_langchain_reply及stream_sse_events导入；注册POST /stream，路由主体留占位供用户补写。
- 路由测试复用已有offline_stream，不新建fake；TestClient直接调用实际app，模型SDK/转换器/响应框架真实运行，仅上游HTTP预设。此端点不依赖数据库，TestClient不进入上下文以不启用lifespan，不触碰运行者数据库；finally关闭测试客户端。

完整局部参考：

```python
@app.post("/stream", response_class=StreamingResponse)
async def stream_text(request: TextStreamRequest) -> StreamingResponse:
    """逐段返回普通文本模型流，不承诺会话保存。"""
    source = stream_langchain_reply(request.message)
    events = stream_sse_events(source)
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
```

source与events都是异步生成器对象，不在这两处await，也不先收集完整列表。StreamingResponse接收events，实际发送响应时async for消费它，才会进入模型读取和SSE转换。装饰器的response_class声明路由响应种类，返回语句则创建实际响应实例；media_type设定Content-Type，headers是HTTP响应头，Cache-Control:no-cache请求缓存使用前重新验证，不保证代理即时转发，也不等于断线恢复。

新增HTTP测试两种参数化路径与空输入一例：正常返回HTTP200、text/event-stream、两条delta和done；上游部分正文后超时仍为HTTP200，但最终error且没有done；空输入返回application/json的422，模型请求为零。还检查缓存头、实际传入模型的当前问题、一次上游HTTP及正常/故障关闭。

TestClient.post等到响应消费完才返回，因此response.text只用于检查完整事件契约，不能据此证明浏览器收到首片段的时刻或网络及时性。这里按空行拆完整响应也不是半包解析器；前单元已验证转换层在上游finish前交出正文，真实网络及浏览器仍需专门验证。

HTTP接线正确RED：目标2 failed / 7 passed（1.49秒），两个失败均为main.stream_text的NotImplementedError；六个已有流测试和新增输入校验通过，无收集错误。全量最近全绿163 passed为新增HTTP场景前的基线；等待用户补路由后再验目标/全量。未新增依赖、未请求真实模型、未提交。

路由补写后核验：模型生成器、事件转换器与响应连接正确，但media_type误写type/event-stream；实际响应头也因此为这个字符串。目标2 failed / 7 passed（1.15秒），两条HTTP用例均在Content-Type断言失败。应修为text/event-stream，再验目标及全量；尚未宣称HTTP接线GREEN或验证真实网络及时性。

## 已验证：HTTP接线和真实回环逐段交付

用户修正响应类型后，目标9 passed（1.07秒）、全量166 passed（2.38秒），diff及离线锁检查通过。实际/stream路由的正常终态、部分正文后超时error及输入422拒绝成立。独立文本流仍不写业务数据库，不将done当成会话保存证明。

新增显式[HTTP探针](../playground/sse_http_probe.py)：

```bash
uv run --offline --no-sync python -m playground.sse_http_probe \
  --output playground/results/sse_http_probe_new.json
```

必须选择新报告路径，脚本不覆盖旧文件。它不读取.env，设置合成模型配置，只有客户端到本应用走真实127.0.0.1临时端口；上游模型HTTP仍由MockTransport提供预设字节。真实SDK、转换器、FastAPI、Starlette及Uvicorn运行，关闭应用lifespan以不访问业务数据库；脚本退出时停止本次服务。loopback客户端trust_env=False绕过环境代理，不修改用户代理模式。

新增辅助代码逐个说明：

| 定义 | 做什么 |
| --- | --- |
| model_event | 将合成delta、stop和usage编码为模型上游协议字节，继续由真实SDK解析 |
| run_case | 分别驱动正常和超时场景，收集客户端真正读到的应用事件并核验顺序/关闭 |
| ModelStream.__aiter__ | 先交出首段，随后等待放行；正常时继续正文/结束/usage，故障时抛ReadTimeout |
| ModelStream.aclose | 记录上游响应流是否被关闭，不冒充供应商停止计算 |
| respond | 记录模型HTTP次数，检查stream及实际问题，返回含ModelStream的假上游响应 |
| create_client | 只替换langchain_streaming使用的异步客户端入口，将SDK连接到假上游 |
| probe | 创建回环临时监听socket，启动Uvicorn任务，等启动后顺序跑两例，finally请求退出并等待服务停止 |
| main | 处理显式输出参数，记录时间和相关源码SHA256指纹，保存有限验证结果；失败也留原始记录 |

核心控制是asyncio.Event：开始未放行，上游yield首段后await release.wait()；真实HTTP客户端用client.stream及aiter_lines增量读响应，积累到空行后才处理完整事件；第一次读到delta时确认上游finished仍为False、放行开关尚未打开，再release.set()。如果服务端先收齐全文才发，客户端就读不到首段，放行也不会发生，探针会超时失败。wait_for的5秒是防卡住上限，不是首Token延迟性能指标。

探针只解析本应用固定的event行加单行JSON data行，借助HTTPX增量解码；不是实现通用浏览器SSE解析器。Uvicorn的create_task在当前事件循环驱动本地服务，短暂sleep仅轮询启动标志，server.should_exit及finally负责清理。patch仅在探针范围替换上游入口、模型配置和tracing环境，退出后恢复。

首次执行受环境权限限制，记录[PermissionError结果](../playground/results/sse_http_probe_2026-11-05.json)，未形成网络验证；在允许本地监听的执行环境中使用相同源码另存[复验结果](../playground/results/sse_http_probe_2026-11-05_recheck.json)，正常与模拟超时两例passed。两例均first_delta_received_while_upstream_blocked=True、上游请求一次且closed=True；正常事件delta/delta/done及usage总数12，故障事件delta/error且finished=False，没有done。服务已退出，没有遗留常驻监听。

这是真实本地HTTP配合预设模型响应的逐段交付证据，没有调用真实模型、启动浏览器、接入代理或部署，也没有验证客户端断开或业务持久化。显式探针不计入pytest用例数；本单元未提交。

## 下一步：断开与取消前置

目标是在客户端不再接收时停止本应用继续读取上游，并关闭生成器/HTTP客户端，避免后台无意义地等完整回答。HTTP读取超时是模型请求错误；客户端断开引发的任务取消是另一种控制流程，不应伪装成模型超时或正常done。

本机核验asyncio.CancelledError直接继承BaseException，当前except (APIError, InvalidStreamError)不捕获它；Starlette具有http.disconnect监听/取消逻辑，但已有路径是否在实际断开后完整清理，要通过下一单元真实连接验证，不能仅据库有此代码宣称完成。清理用finally/aclosing，取消继续传播；已经关闭的下游不要求还能送达error事件。

下一次先预测首段后主动断开时是否应继续等上游及是否能标done，再准备实际断开与关闭证据。前端停止按钮、浏览器分包解析、业务保存和完整Agent工具流仍依正式路线后续推进。

## 已验证：客户端断开后的取消传播和清理（2026-11-06）

用户询问前次HTTP探针是模拟还是真实，已明确：客户端到应用是真实Uvicorn/HTTPX回环连接，上游模型HTTP模拟，没有真实模型或浏览器。用户正确预测断开后不等待完整回答、不标done，并提出独立取消标记。标记分位置：前端主动停止可本地显示已取消；服务器可记录客户端断开/取消的运行状态；断开后不能依赖原SSE再送达cancelled。当前应用没有新增任务状态持久化，不能把探针观察字段说成已有业务状态。

本次扩展原[显式探针](../playground/sse_http_probe.py)而不修改路由、模型读取或事件转换核心。run_case新增disconnect参数，正常/超时保持旧路径；第三例首delta后主动离开HTTP响应上下文，实际关闭连接，且不调用release.set。上游仍在Event等待，必须由实际服务器断开处理触发取消。

新增观察和等待逻辑：

- ModelStream.__aiter__捕获asyncio.CancelledError后设置upstream_read_cancelled并立即raise，finally设置upstream_iterator_stopped；只观察控制流程，不吞取消或伪造上游完成。
- ModelStream.aclose记录closed并设置upstream_closed事件；客户端断开后，run_case在服务器仍运行、探针配置仍生效的范围内等待此事件。三秒只是失败保护上限，不是性能指标，也不允许借finally停止整个服务器的副作用来冒充取消成功。
- 断开例检查release仍未放行、finished为False、真实上游请求一次、读取确实取消且迭代停止和响应流关闭，客户端只收到delta。该状态为探针记录，未增添生产日志/数据库任务状态。
- probe顺序执行正常、模型超时和客户端断开三例，再按原finally停止服务器；原报告不覆盖。

[2026-11-06报告](../playground/results/sse_http_probe_2026-11-06_disconnect.json)三例passed，断开例upstream_read_cancelled=True、upstream_iterator_stopped=True、closed=True、finished=False，上游请求一次，客户端仅首delta。相关源码指纹在报告中保留。正常及超时两例仍符合原契约。本次在允许临时回环监听的执行环境运行，服务已在finally退出。

另外新增一条默认离线回归测试test_cancelled_stream_propagates_cancellation_and_closes_upstream，复用offline_stream，不新增独立fixture：prepare增加wait_after_first选项，在首正文后通知waiting事件再阻塞；测试先anext读取首delta，再create_task(anext(events))请求下一条，等上游确实进入待读取后pending.cancel，要求await pending抛CancelledError。若被转换成error或done则不会抛预期异常，测试会失败。finally确保取消读取任务后才关闭生成器，aclosing负责释放；最后检查cancelled=True、finish_sent=False、closed=True和一次模型HTTP。

这里anext表示从异步迭代器取下一项；create_task允许下一项读取与测试控制逻辑同时推进；cancel发出取消请求，await任务用于确认取消实际传播。waiting只表示已经进入测试等待点，不表示业务完成，超时保护避免测试挂住。

现有清理链路已满足目标，故新增的是行为回归证明，不为RED而人为修改生产代码。流相关10 passed（1.31秒），全量167 passed（2.11秒），diff及离线锁检查通过。真实本地HTTP配合模拟模型上游，不证明供应商后端停止计算/计费、浏览器停止按钮、代理部署或业务取消状态已实现。本SSE批次尚未提交，下一步可进入浏览器增量读取/完整事件解析和停止操作；会话/Agent流式及保存边界继续保留。

2026-11-06取消责任补充：cancelled是应用状态，不是给模型的新prompt或向断开客户端补发的done。浏览器→应用、应用→模型供应商是两段独立连接；应用检测下游断开后取消读取任务并关闭上游HTTP流，不能只改状态却继续等完整模型输出。供应商收到连接关闭后怎样终止推理、何时停止计费取决于其服务实现与契约；若该API提供明确取消接口，再按契约调用。核对[HTTPX异步流文档](https://www.python-httpx.org/async/)确认退出stream上下文会关闭响应；核对[DeepSeek Chat Completions文档](https://api-docs.deepseek.com/api/create-chat-completion/)未找到“断开即立即停算/停费”的明确保证，不将本地关闭证据外推为供应商结算证据。当前业务取消状态仍未持久化，本段只澄清职责，无新增实现或真实模型请求。

范围确认：用户明确没有列入规划的取消扩展快速带过。正式路线阶段10要求用户中断和断开检测，未要求独立任务取消端点、cancelled状态入库或供应商专用取消接口；当前保留概念说明，不安排这些实现，不把它们当作SSE完成前置。下一步继续浏览器增量消费和停止操作。
