"""显式为浏览器提供真实本地应用和预设模型；仅测试进程注册放行/观察接口。

运行：.venv/bin/python -m playground.sse_browser_probe
浏览器访问打印地址下的/static/stream-demo.html，问题填normal/timeout/stop。
首段后上游阻塞；观察首段后由测试操作者POST /__probe/release/normal或timeout。
stop用页面按钮取消，不放行；GET /__probe/state只返回合成测试状态。
不调用真实模型，不启动业务数据库，不应作为部署入口。
"""

import asyncio
import json
import os
import socket
from unittest.mock import patch

import httpx
import uvicorn
from fastapi import HTTPException

from app.main import app
from app.services import langchain_streaming
from playground.sse_http_probe import model_event


async def serve():
    """同一临时服务依次供浏览器验证正常、超时和停止，退出时恢复替换。"""
    gates = {name: asyncio.Event() for name in ("normal", "timeout", "stop")}
    states = {name: {
        "requests": 0, "released": False, "finished": False,
        "cancelled": False, "iterator_stopped": False, "closed": False,
    } for name in gates}

    @app.get("/__probe/state")
    async def read_state():
        """只读查看fake上游是否被放行、取消及关闭。"""
        return states

    @app.post("/__probe/release/{case}")
    async def release(case: str):
        """在操作者已观察页面首段后放行，排除全文缓冲的假象。"""
        if case not in ("normal", "timeout"):
            raise HTTPException(400, "Only normal/timeout can be released.")
        states[case]["released"] = True
        gates[case].set()
        return {"released": case}

    class ModelStream(httpx.AsyncByteStream):
        """真实SDK读取的预设字节源；Event把首段和后续内容分开。"""

        def __init__(self, case):
            self.case = case

        async def __aiter__(self):
            state = states[self.case]
            try:
                yield model_event({"role": "assistant", "content": "首段"})
                await gates[self.case].wait()
                if self.case == "timeout":
                    raise httpx.ReadTimeout("synthetic browser probe timeout")
                yield model_event({"content": "后段"})
                state["finished"] = True
                yield model_event(finish_reason="stop")
                yield b"data: [DONE]\n\n"
            except asyncio.CancelledError:
                state["cancelled"] = True
                raise
            finally:
                state["iterator_stopped"] = True

        async def aclose(self):
            states[self.case]["closed"] = True

    def respond(request):
        """按页面提交的合成问题选场景，所有其他模型输入直接拒绝。"""
        payload = json.loads(request.content)
        case = payload["messages"][-1]["content"]
        assert case in gates and payload["stream"] is True
        states[case]["requests"] += 1
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=ModelStream(case))

    def create_client(**kwargs):
        """仅把模型HTTP替换为MockTransport；浏览器到Uvicorn走真实网络。"""
        return httpx.AsyncClient(**kwargs, transport=httpx.MockTransport(respond))

    with (
        patch.dict(os.environ, {"LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"}),
        patch.object(langchain_streaming.settings, "openai_api_key", "offline-placeholder"),
        patch.object(langchain_streaming.settings, "openai_base_url", "https://example.invalid/v1"),
        patch.object(langchain_streaming.settings, "openai_model", "offline-model"),
        patch.object(langchain_streaming, "AsyncClient", create_client),
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener,
    ):
        listener.bind(("127.0.0.1", 0))
        listener.listen(16)
        listener.setblocking(False)
        print(f"http://127.0.0.1:{listener.getsockname()[1]}", flush=True)
        server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="error", access_log=False))
        try:
            await server.serve(sockets=[listener])
        finally:
            print(json.dumps(states, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(serve())
