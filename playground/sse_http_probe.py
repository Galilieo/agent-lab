"""显式验证本机/stream的真实HTTP逐段交付，上游模型HTTP使用预设字节流。

运行：uv run --offline --no-sync python -m playground.sse_http_probe --output 路径.json
仅监听127.0.0.1临时端口；关闭应用lifespan，不读取.env或使用业务数据库。
不请求真实模型、不启动浏览器；报告只记录合成内容，已有报告不覆盖。
"""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
from unittest.mock import patch

import httpx
import uvicorn

from app.main import app
from app.services import langchain_streaming


def model_event(delta=None, *, finish_reason=None, usage=None) -> bytes:
    """生成上游合成协议帧，保留真实SDK解析流程。"""
    data = {
        "id": "offline-http-probe", "object": "chat.completion.chunk",
        "created": 0, "model": "offline-model",
        "choices": [] if usage else [{
            "index": 0, "delta": delta or {}, "finish_reason": finish_reason,
        }],
    }
    if usage:
        data["usage"] = usage
    return ("data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")


async def run_case(url: str, *, fail: bool, disconnect: bool = False) -> dict:
    """首事件后放行或关闭连接，核验正常/超时终态及断开后的上游清理。"""
    release = asyncio.Event()
    upstream_closed = asyncio.Event()
    state = {
        "upstream_requests": 0, "finished": False, "closed": False,
        "upstream_read_cancelled": False, "upstream_iterator_stopped": False,
    }
    events = []
    first_delta_before_release = False

    class ModelStream(httpx.AsyncByteStream):
        """首段后等待客户端确认，保证验证的是逐段到达而非全文缓冲。"""

        async def __aiter__(self):
            try:
                yield model_event({"role": "assistant", "content": "首段"})
                await asyncio.wait_for(release.wait(), timeout=5)
                if fail:
                    raise httpx.ReadTimeout("offline upstream stream interrupted")
                yield model_event({"content": "后段"})
                state["finished"] = True
                yield model_event(finish_reason="stop")
                yield model_event(usage={
                    "prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12,
                })
                yield b"data: [DONE]\n\n"
            except asyncio.CancelledError:
                state["upstream_read_cancelled"] = True
                raise
            finally:
                state["upstream_iterator_stopped"] = True

        async def aclose(self):
            state["closed"] = True
            upstream_closed.set()

    def respond(request):
        state["upstream_requests"] += 1
        payload = json.loads(request.content)
        assert payload["stream"] is True
        assert payload["messages"][-1] == {"role": "user", "content": "合成HTTP验证"}
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, stream=ModelStream(),
        )

    def create_client(**kwargs):
        return httpx.AsyncClient(**kwargs, transport=httpx.MockTransport(respond))

    with patch.object(langchain_streaming, "AsyncClient", create_client):
        # 只有到应用的这段HTTP走真实回环网络，显式绕过环境代理。
        async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
            async with client.stream("POST", url, json={"message": "合成HTTP验证"}) as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                pending_lines = []
                async for line in response.aiter_lines():
                    if line:
                        pending_lines.append(line)
                        continue
                    if not pending_lines:
                        continue
                    # 本探针只消费本应用的一条event行加一条JSON data行格式。
                    event_line, data_line = pending_lines
                    pending_lines.clear()
                    assert event_line.startswith("event: ")
                    assert data_line.startswith("data: ")
                    name = event_line.removeprefix("event: ")
                    data = json.loads(data_line.removeprefix("data: "))
                    events.append({"event": name, "data": data})
                    if name == "delta" and not release.is_set():
                        assert state["finished"] is False
                        assert data == {"text": "首段"}
                        first_delta_before_release = True
                        if disconnect:
                            # 离开response上下文实际关闭HTTP流，不放行模拟上游。
                            break
                        release.set()
                assert pending_lines == []

        if disconnect:
            # 等实际服务器响应断开；超时是清理失败，不能靠探针退出时取消补救。
            await asyncio.wait_for(upstream_closed.wait(), timeout=3)

    assert first_delta_before_release
    assert state["upstream_requests"] == 1
    assert state["closed"] is True
    assert [event["event"] for event in events] == (
        ["delta"] if disconnect else ["delta", "error"] if fail else ["delta", "delta", "done"]
    )
    if disconnect:
        assert not release.is_set()
        assert state["finished"] is False
        assert state["upstream_read_cancelled"] is True
        assert state["upstream_iterator_stopped"] is True
    elif fail:
        assert events[-1]["data"]["code"] == "model_timeout"
    else:
        assert events[-1]["data"]["finish_reason"] == "stop"
        assert events[-1]["data"]["usage"]["total_tokens"] == 12
    return {
        "case": "disconnect" if disconnect else "timeout" if fail else "normal",
        "http_status": 200,
        "first_delta_received_while_upstream_blocked": first_delta_before_release,
        **state, "events": events,
    }


async def probe() -> list[dict]:
    """临时启动真实Uvicorn，检查正常/超时/主动断开并在finally停止服务。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(16)
        listener.setblocking(False)
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(
            app, lifespan="off", log_level="error", access_log=False,
            http="h11", ws="none",
        ))
        server_task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            for _ in range(500):
                if server.started:
                    break
                if server_task.done():
                    await server_task
                    raise RuntimeError("Probe server exited before startup.")
                await asyncio.sleep(0.01)
            else:
                raise TimeoutError("Probe server did not start.")

            with (
                patch.dict(os.environ, {"LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"}),
                patch.object(langchain_streaming.settings, "openai_api_key", "offline-placeholder"),
                patch.object(langchain_streaming.settings, "openai_base_url", "https://example.invalid/v1"),
                patch.object(langchain_streaming.settings, "openai_model", "offline-model"),
            ):
                url = f"http://127.0.0.1:{port}/stream"
                return [
                    await run_case(url, fail=False),
                    await run_case(url, fail=True),
                    await run_case(url, fail=False, disconnect=True),
                ]
        finally:
            server.should_exit = True
            await asyncio.wait_for(server_task, timeout=5)


def main():
    """显式运行探针并保存来源指纹和有限验证结果，已有文件不覆盖。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new path.")
    sources = [
        "app/main.py", "app/schemas.py", "app/services/sse.py",
        "app/services/langchain_streaming.py", "playground/sse_http_probe.py",
    ]
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Real loopback HTTP via Uvicorn/HTTPX, including client disconnect; fake upstream model HTTP. No real model, browser, proxy/deployment, provider-side compute cancellation or database validation.",
        "source_sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
        "status": "running",
    }
    try:
        report["cases"] = asyncio.run(probe())
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error_type"] = type(exc).__name__
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output)}, ensure_ascii=False))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
