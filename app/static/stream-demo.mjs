/** 将页面与同源POST /stream连接；字节读取和取消委托给sse-client模块。 */
import { readSseResponse, stopStream } from "./sse-client.mjs";

const form = document.querySelector("#stream-form");
const question = document.querySelector("#message");
const startButton = document.querySelector("#start");
const stopButton = document.querySelector("#stop");
const status = document.querySelector("#status");
const output = document.querySelector("#output");
let activeController = null;

/** 请求期间锁定输入与开始按钮；停止仅对正在进行的请求开放。 */
function setRunning(running) {
  question.disabled = running;
  startButton.disabled = running;
  stopButton.disabled = !running;
}

/** 一次提交对应一个控制器；收到完整事件才更新页面，不保存业务会话。 */
async function submitQuestion(event) {
  event.preventDefault();
  if (activeController) return;
  const message = question.value.trim();
  if (!message) {
    status.textContent = "请输入问题。";
    return;
  }

  const controller = new AbortController();
  activeController = controller;
  setRunning(true);
  output.textContent = "";
  status.textContent = "正在接收…";
  let failureMessage = "模型响应失败。";
  try {
    const response = await fetch("/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    });
    if (!response.ok) {
      await response.body?.cancel();
      throw new Error(`请求失败（HTTP ${response.status}）。`);
    }
    const mediaType = response.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase();
    if (mediaType !== "text/event-stream") {
      await response.body?.cancel();
      throw new Error("响应不是SSE事件流。");
    }
    const terminal = await readSseResponse(response, (item) => {
      if (item.event === "delta") output.textContent += item.data.text;
      if (item.event === "error") failureMessage = item.data.message;
      if (item.event !== "delta") stopButton.disabled = true;
    });
    status.textContent = terminal === "done" ? "已完成" : `失败：${failureMessage}`;
  } catch (error) {
    status.textContent = controller.signal.aborted || error.name === "AbortError"
      ? "已取消"
      : `失败：${error.message}`;
  } finally {
    activeController = null;
    setRunning(false);
  }
}

/** 只取消当前请求，已显示正文保留；最终状态由submitQuestion的catch更新。 */
function stopCurrentRequest() {
  if (!activeController) return;
  stopButton.disabled = true;
  stopStream(activeController);
}

form.addEventListener("submit", submitQuestion);
stopButton.addEventListener("click", stopCurrentRequest);
