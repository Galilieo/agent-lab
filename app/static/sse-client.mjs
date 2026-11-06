/**
 * 本应用SSE协议的浏览器消费核心，供演示页及Node内置测试复用。
 * 输入是真实Response对象；本模块不创建网络请求或操作DOM。
 */

/** 解析本应用的两行事件帧；输入不含结尾空行，不兼容所有SSE扩展格式。 */
function parseSseFrame(frame) {
  const lines = frame.split("\n");
  if (lines.length !== 2 || !lines[0].startsWith("event: ") || !lines[1].startsWith("data: ")) {
    throw new Error("SSE事件格式不符合本应用约定。");
  }
  const event = lines[0].slice(7);
  const data = JSON.parse(lines[1].slice(6));
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("SSE事件数据必须是JSON对象。");
  }
  const valid = (event === "delta" && typeof data.text === "string")
    || (event === "done" && data.finish_reason === "stop")
    || (event === "error" && typeof data.code === "string" && typeof data.message === "string");
  if (!valid) throw new Error("SSE事件名称或数据不符合本应用约定。");
  return { event, data };
}

/** 增量解码、缓冲完整事件并回调；必须收到done或error才允许正常返回。 */
export async function readSseResponse(response, onEvent) {
  if(!response.body) throw new Error("响应没有可读取的正文。");

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", {fatal: true});
  let buffer = "";
  let terminal = null;

  try {
    while (true) {
      const {value, done} = await reader.read();
      buffer += done
        ? decoder.decode()
        : decoder.decode(value, {stream: true });

      while (true) {
        const boundary = buffer.indexOf("\n\n");
        if (boundary === -1) break;

        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        if (terminal !== null) {
          throw new Error("SSE终态之后出现额外事件。");
        }

        const item = parseSseFrame(frame);
        if (item.event === "done" || item.event === "error") {
          terminal = item.event;
        }
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
      // 清理时的异常不能覆盖原始读取事件或取消异常。
    }
    reader.releaseLock();
  }
}

/** 中止调用方为本次fetch创建的控制器，不发送额外取消API请求。 */
export function stopStream(controller) {
  if (controller) controller.abort();
}
