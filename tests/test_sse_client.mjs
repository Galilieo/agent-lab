/**
 * 使用Node自带测试运行真实浏览器消费模块及Web Streams，无网络/浏览器。
 * 覆盖多帧合包、UTF-8和事件拆包、异常终止及取消传播。
 * 运行：node --test tests/test_sse_client.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readSseResponse, stopStream } from "../app/static/sse-client.mjs";

/** 只用内存字节代替网络；Response、ReadableStream及TextDecoder真实执行。 */
function responseFrom(parts) {
  return new Response(new ReadableStream({
    start(controller) {
      for (const part of parts) controller.enqueue(part);
      controller.close();
    },
  }), { headers: { "Content-Type": "text/event-stream" } });
}

test("合并或逐字节输入均还原中文及多事件", async () => {
  const raw = 'event: delta\ndata: {"text":"你好\\n世界"}\n\n'
    + 'event: delta\ndata: {"text":"！"}\n\n'
    + 'event: done\ndata: {"finish_reason":"stop","usage":null}\n\n';
  const bytes = new TextEncoder().encode(raw);
  for (const parts of [[bytes], Array.from(bytes, (byte) => Uint8Array.of(byte))]) {
    const response = responseFrom(parts);
    const received = [];
    const terminal = await readSseResponse(response, (event) => received.push(event));
    assert.equal(terminal, "done");
    assert.deepEqual(received, [
      { event: "delta", data: { text: "你好\n世界" } },
      { event: "delta", data: { text: "！" } },
      { event: "done", data: { finish_reason: "stop", usage: null } },
    ]);
    assert.equal(response.body.locked, false);
  }
});

test("error是失败终态，已交付前缀保留", async () => {
  const raw = 'event: delta\ndata: {"text":"部分"}\n\n'
    + 'event: error\ndata: {"code":"model_timeout","message":"模型响应超时。"}\n\n';
  const received = [];
  const terminal = await readSseResponse(
    responseFrom([new TextEncoder().encode(raw)]),
    (event) => received.push(event),
  );
  assert.equal(terminal, "error");
  assert.deepEqual(received.map((item) => item.event), ["delta", "error"]);
  assert.equal(received[0].data.text, "部分");
});

test("EOF缺少终态或最后事件残缺时拒绝报成功", async () => {
  const prefix = 'event: delta\ndata: {"text":"部分"}\n\n';
  for (const raw of [prefix, prefix + 'event: done\ndata: {"finish_reason":"stop"}']) {
    const received = [];
    await assert.rejects(
      readSseResponse(responseFrom([new TextEncoder().encode(raw)]), (item) => received.push(item)),
      /完整.*结束|结束.*完整/,
    );
    assert.deepEqual(received.map((item) => item.event), ["delta"]);
  }
});

test("首事件后停止，取消信号与读取异常继续传播", async () => {
  const aborter = new AbortController();
  const source = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('event: delta\ndata: {"text":"首段"}\n\n'));
      // 模拟fetch响应源响应signal，模块中的控制器/读取/事件处理仍真实执行。
      aborter.signal.addEventListener("abort", () => {
        controller.error(new DOMException("请求已取消", "AbortError"));
      }, { once: true });
    },
  });
  const response = new Response(source);
  const received = [];
  await assert.rejects(readSseResponse(response, (item) => {
    received.push(item);
    stopStream(aborter);
  }), { name: "AbortError" });
  assert.equal(aborter.signal.aborted, true);
  assert.deepEqual(received.map((item) => item.event), ["delta"]);
  assert.equal(response.body.locked, false);
});
