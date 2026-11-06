# SSE 浏览器消费：设计与局部实践

正式进度以[学习路线第14节](./agent-lab总体学习路线.md#14-当前下一步)为准。2026-11-06用户同意继续浏览器逐段显示和停止按钮；不扩展独立任务取消接口、取消状态入库或供应商专用取消API。

最新验证：用户已补两个核心函数，Node 4 passed、Python 167 passed（2.48秒）。真实Edge浏览器配合临时Uvicorn及预设模型上游，正常/模拟超时/按钮停止三例通过，服务已退出；报告见[浏览器记录](../playground/results/sse_browser_probe_2026-11-06.json)。尚未请求真实模型或验证部署/业务持久化；下文保留初始设计与RED经过，提交状态见下一段。

收口更新：用户已准确解释响应体EOF不保证SSE完整正常结束，并授权整理提交。功能提交cc19585，提交前Python167 passed（2.30秒）/Node4 passed；只清理空格与结尾换行，报告保留原验证时源码指纹。文档另作docs提交，不推送；独立文本SSE收口，接续固定评测，不能据此声称完整Agent流式已接入。

## 目标与方案

浏览器从既有POST /stream读取delta/done/error，追加正文；正常done后显示完成，error或连接提前结束显示失败；停止按钮通过AbortController中止请求，保留已显示正文并标记已取消。前端取消状态不等于服务端任务状态已持久化。

本单元采用原生HTML/JavaScript演示页，通过FastAPI静态目录同源提供。仓库没有现成前端，不为演示新建Vue/React工程或构建链；EventSource不提供当前POST所需的body配置，采用fetch+ReadableStream。布局仅保留问题、开始/停止、状态与输出，便于观察机制。此为Codex基于已有接口选择的最小实现方式，不改原生/chat或加入会话持久化。

文件分工：

| 文件 | 职责 |
| --- | --- |
| app/static/sse-client.mjs | 本应用事件帧解析、增量字节读取、停止操作；无DOM依赖便于Node运行 |
| app/static/stream-demo.html | 最小表单、状态和正文区域 |
| app/static/stream-demo.mjs | fetch/DOM连接、按钮状态和结果展示 |
| app/main.py | 挂载/static，复用既有POST /stream |
| tests/test_sse_client.mjs | Node内置测试，真实Web Streams/编码器，网络输入用内存字节 |

Codex准备页面、事件帧机械解析、请求/界面连接与测试。用户补readSseResponse的增量解码/完整事件缓冲和stopStream的abort调用；给完整局部参考，不要求独立设计前端。新增函数和测试全部解释。

## 新概念与数据流

```text
fetch提交问题及signal
→ response.body.getReader取得字节读取器
→ reader.read逐块读取
→ TextDecoder增量还原UTF-8文字
→ buffer积累至完整事件空行
→ parseSseFrame还原event和JSON data
→ 页面追加正文或更新终态
```

response.json()/text()会等待完整响应，不适合这里逐段显示。getReader每次read返回{value, done}，value通常是Uint8Array；这个done只表示响应体读取结束，不是我们的SSE done事件。

同一个TextDecoder使用decode(value, {stream:true})保留不完整UTF-8字节，流结束时decode()刷新尾部；文字缓冲区则负责跨网络块的事件边界，两种缓冲分别保护字符和事件。只处理本应用encode_sse约定的LF分隔、event行+单行JSON data行；不自称通用SSE解析库。

AbortController为本次fetch提供signal，stopStream调用abort；浏览器中止请求及响应体读取。页面将本地状态设为已取消，不再等待SSE cancelled事件。取消要继续抛出，资源清理仍执行；其他HTTP/JSON/协议错误显示失败。界面输出使用textContent，不把模型文本当HTML插入。

源码与接口参考：[TextDecoder.decode](https://developer.mozilla.org/en-US/docs/Web/API/TextDecoder/decode)、[ReadableStream.getReader](https://developer.mozilla.org/en-US/docs/Web/API/ReadableStream/getReader)、[AbortController.abort](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)。本机Node v24.21.0支持本单元使用的Web Streams等API；Node单元测试不算浏览器验收。

## 实施与验证步骤

1. 添加导出占位和Node行为测试，运行node --test tests/test_sse_client.mjs，确认因核心未实现失败、无导入/语法错误。
2. Codex补帧格式辅助和页面样板；用户参考补增量读取/缓冲与停止核心。测试覆盖单块含多个事件、逐字节拆中文及事件、error终态、EOF没有完整终态、取消传播。
3. 用户保存后运行Node目标和默认Python全量，git diff --check；此处不把Node条数混进pytest数量。
4. 核心通过后，在预设模型上游的本地服务验证实际浏览器正常/错误/停止行为；没有运行浏览器就明确记录未验。不自动调用真实模型或提交。

本单元初始尚未GREEN，HTTP/取消后端前一检查点为Python167 passed；后续结果见本页开头及末尾。细节API不要求背诵，重点解释字节、字符、事件三个边界及abort传播。

## 本轮样板带读

`parseSseFrame(frame)`接收已经按空行切出的完整事件，不负责读网络。split将两行拆开，startsWith检查前缀，slice(7)/slice(6)去掉`event: `/`data: `，JSON.parse还原data对象；检查本应用三种事件的数据字段后返回`{event, data}`。JSON中的`\\n`此时才还原为正文换行，不会被误切成事件行。它只支持我们自己的编码格式，未实现注释、CRLF、多行data等通用SSE功能。

`stream-demo.html`提供表单、输入框、两个按钮、状态和pre正文区；type=module加载JS模块，pre保留正文换行。`stream-demo.mjs`的querySelector取得这些真实DOM元素，activeController保存本次请求的控制器。setRunning统一控制输入/按钮；submitQuestion阻止表单跳页，拒绝空白和重复提交，创建控制器，再以JSON body和signal发同源fetch。先检查HTTP状态及Content-Type，错误响应关闭未消费的body；正确响应交给readSseResponse。传入的回调逐次追加delta正文、保存error消息并在终态禁用停止。读取函数正常返回后区分done/error，catch区分取消/其他失败，finally恢复控件。stopCurrentRequest拿到同一个控制器调用stopStream；addEventListener把提交/点击行为连到函数，没有执行第二次模型请求。

FastAPI的StaticFiles挂到/static：收到该路径下的请求后从app/static提供文件；Path(__file__).resolve().parent使路径相对于main.py而不是当前终端目录。未来页面入口为/static/stream-demo.html；直接双击HTML不属于此同源方案。演示页开始按钮连接现有模型接口，核心补齐后再由受控本地服务验收，不把现在打开页面当作流式成功。

## 用户局部参考

只替换app/static/sse-client.mjs中的两个占位函数，保留上面的parseSseFrame。onEvent是调用方传入的同步函数：每解析出一个完整事件调用一次；不是LangChain的ainvoke。

```javascript
export async function readSseResponse(response, onEvent) {
  if (!response.body) throw new Error("响应没有可读取的正文。");
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let buffer = "";
  let terminal = null;

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });

      while (true) {
        const boundary = buffer.indexOf("\n\n");
        if (boundary === -1) break;
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        if (terminal !== null) throw new Error("SSE终态之后出现额外事件。");
        const item = parseSseFrame(frame);
        if (item.event === "done" || item.event === "error") terminal = item.event;
        onEvent(item);
      }

      if (done) break;
    }
    if (buffer !== "" || terminal === null) {
      throw new Error("响应结束时没有完整结束事件，或存在残缺事件。");
    }
    return terminal;
  } finally {
    try {
      await reader.cancel();
    } catch {
      // 已出错的流可能拒绝cancel；清理失败不能盖掉原始读取/取消异常。
    }
    reader.releaseLock();
  }
}

export function stopStream(controller) {
  if (controller) controller.abort();
}
```

`read()`返回对象的解构赋值拿到value字节和done布尔值；await只等待下一块可读数据，不等完整回答。decoder必须在循环外复用，fatal=true使非法或残缺UTF-8报错；stream=true表示还有后续字节，最后无参数decode刷新残留字节。buffer只在有`\n\n`时取出完整帧，内循环处理同一块含多个事件的情况，未完整部分留到下次read。terminal与reader的done是两个不同变量，分别记录协议终态和响应体结束。这里只在EOF时核验完整性，但delta在循环中已立刻回调显示，不等EOF才显示。

finally中的reader.cancel取消尚未消费的读取源，releaseLock解除读取器对流的独占；这与按钮使用AbortController中止fetch的职责不同。没有捕获主流程异常，AbortError、解析错误和回调异常都会继续交给页面catch；唯一空catch只处理清理阶段可能再次抛出的异常。

## 测试怎样执行

Node自带的test注册异步测试、assert检查结果；TextEncoder把准备好的协议文本变为UTF-8字节。responseFrom的parts是字节块列表，ReadableStream.start收到的是流控制器（不是AbortController），enqueue入队、close标记源结束，再用真实Response包装。它只替换网络数据来源，readSseResponse、Web Streams及解码器真实运行。

1. 合包/逐字节：相同文本先作为一个大块，再用Array.from和Uint8Array.of拆成每块一个字节。两次都运行真实读取函数；回调用push收集事件，deepEqual比较事件角色/正文/终态、equal检查返回done及读取器解锁。逐字节会拆开中文和事件边界，能发现逐块独立解码或把每块当一帧的错误。
2. error终态：输入delta后跟模拟model_timeout错误，调用真实读取函数；检查返回error、回调顺序及先前正文仍在。它不制造真实供应商超时，只验证已有错误事件怎样被消费。
3. 提前结束：循环输入“只有完整delta”和“delta后跟少结尾空行的done”。assert.rejects等待异步函数拒绝，正则检查完整结束相关错误；只允许delta被回调，证明半条done不能被当成成功。
4. 停止：源先入队首delta后保持开启，在signal的abort监听里用controller.error模拟fetch响应中断。收到首事件的回调调用stopStream；assert.rejects检查AbortError继续传播，再检查signal已取消、无额外事件、读取器已解锁。AbortController及读取函数真实运行，但signal与内存源的连接是测试手工模拟的，不能证明浏览器或网络已取消。

2026-11-06初始RED：Node共4条、0通过/4失败，均由readSseResponse占位触发，无导入/语法错误。后续页面及机械解析已准备，用户核心仍占位；不记为浏览器完成，也不把此失败数混入pytest。

样板接线后，两个JS模块通过node --check，默认Python全量167 passed（2.30秒）、git diff --check通过。进程内TestClient读取三个静态文件均200，HTML和模块响应类型正确；不启动lifespan、不调用/stream或模型，不等同实际浏览器验收。

## 用户补写后与真实浏览器验证

核对保存的readSseResponse/stopStream：复用解码器、双层循环、完整帧回调、终态/残片检查和finally清理正确，取消异常继续传播；未替换用户实现。Node4条全部通过、Python全量167 passed（2.48秒），本轮未新增Node/pytest用例，也未把浏览器三例混入其数量。实际Edge页面正常首段时禁用开始、启用停止；正常/超时/停止后恢复输入和开始、禁用停止。

新增[显式浏览器探针](../playground/sse_browser_probe.py)，运行命令`.venv/bin/python -m playground.sse_browser_probe`；每次输出新临时地址，不沿用报告端口。只在该显式进程挂载/__probe/state和/__probe/release/{case}，正式app/main.py没有这些控制接口。模块导入不启动服务，默认pytest不执行。

探针新增内容按执行顺序带读：

1. serve创建normal/timeout/stop三个Event和对应状态字典，按合成问题区分场景。read_state只返回预设源的观察状态；release只允许normal/timeout，设置released并Event.set放行。它们用于操作者验证，不是产品任务取消API。
2. ModelStream继承httpx.AsyncByteStream，__init__只保存场景。__aiter__先用复用的model_event编码“首段”，随后等待该场景的Event；放行normal时给后段/stop/[DONE]，timeout则抛ReadTimeout。取消时记录CancelledError并重新抛出，finally记录迭代退出；aclose记录关闭。这些布尔值是fake上游探针状态，不是业务持久化任务状态。
3. respond由MockTransport在真实SDK发出请求时调用，读取请求JSON的最后一条消息作为场景，断言只能提交三种合成问题且stream为True，计数后返回ModelStream。create_client只替换模型HTTP；输入解析、模型SDK、SSE转换器、FastAPI、真实网络和页面消费者都实际执行。
4. patch上下文临时覆盖合成模型配置和客户端，禁止追踪，退出恢复；socket只绑定127.0.0.1且端口0由系统分配，Uvicorn接管同一个socket。lifespan=off不初始化业务DB，finally打印合成状态。验证结束Ctrl-C退出进程，当前服务已结束；不把人为退出的KeyboardInterrupt堆栈算作场景失败。

实际操作：页面分别输入normal/timeout/stop后点开始，先由浏览器AX快照确认“正在接收…”且正文“首段”；前两例再读取测试状态并断言尚未放行/完成，随后POST放行。normal显示“首段后段/已完成”；timeout显示“首段/失败：模型响应超时。”；stop不放行，直接点页面停止，显示“首段/已取消”。最后在服务仍运行时断言三例各请求一次且均已关闭/退出迭代，stop的released=False、finished=False、cancelled=True。

报告中的页面字段来自Codex读取真实Edge无障碍快照后转录，后台字段另由Python读取合成观察接口并断言；不是全自动浏览器断言套件、截图报告或独立人工评审。记录源码SHA256，不覆盖旧HTTP报告。真实的是浏览器至应用HTTP，模型上游仍预设；不能证明供应商终止推理/计费、真实回答质量或部署代理行为。

本轮只新增验证样板和记录，没有调整用户核心。用户尚未在本轮复述缓冲与两种done的区别，不因GREEN写成独立实现掌握。此单元可进入讲解收口和提交整理，提交仍需用户明确提出。
