"""显式请求一次真实模型流，记录合成输出、片段顺序和结束/usage信号。

uv run --offline --no-sync --env-file .env python -m playground.langchain_stream_probe
只发送固定合成提示；不运行工具、读真实笔记或写业务数据库。
HTTP钩子只计数，不读取响应正文，保留真实逐段消费行为。
"""

import argparse
import asyncio
from contextlib import aclosing
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import time
from unittest.mock import patch

from app.config import settings
from app.services import langchain_streaming


DEFAULT_OUTPUT = Path("playground/results/langchain_stream_probe_2026-11-04.json")
QUESTION = "请分三行输出：第一行青榆，第二行流式，第三行验收完成。除此之外不要输出任何内容。"


def save(report):
    Path(report["result_path"]).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


async def consume(report, started):
    real_client = langchain_streaming.AsyncClient

    async def count_request(request):
        if report["http_requests"] >= 1:
            raise RuntimeError("This probe permits only one HTTP request.")
        report["http_requests"] += 1

    def observed_client(**kwargs):
        return real_client(**kwargs, event_hooks={"request": [count_request]})

    combined = None
    with patch.object(langchain_streaming, "AsyncClient", observed_client):
        async with aclosing(langchain_streaming.stream_langchain_reply(
            QUESTION, system_prompt="请严格按照要求简短输出。",
        )) as stream:
            async for chunk in stream:
                elapsed_ms = (time.perf_counter() - started) * 1000
                if not isinstance(chunk.content, str):
                    raise TypeError("Expected plain text chunks in this probe.")
                if chunk.content and report["first_text_ms"] is None:
                    report["first_text_ms"] = elapsed_ms
                    print("Received first text chunk.", flush=True)
                report["chunks"].append({
                    "content": chunk.content, "elapsed_ms": elapsed_ms,
                    "finish_reason": chunk.response_metadata.get("finish_reason"),
                    "usage": chunk.usage_metadata,
                })
                report["partial_answer"] += chunk.content
                combined = chunk if combined is None else combined + chunk
                save(report)

    if combined is None:
        raise ValueError("No model chunks were received.")
    report["answer"] = combined.content
    report["finish_reason"] = combined.response_metadata.get("finish_reason")
    report["usage"] = combined.usage_metadata
    normalized = "".join(combined.content.split())
    report["automatic_checks"] = {
        "one_http_request": report["http_requests"] == 1,
        "expected_synthetic_text": normalized == "青榆流式验收完成",
        "finish_stop_received": report["finish_reason"] == "stop",
        "stream_ended_without_exception": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new file to preserve earlier evidence.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.ERROR)
    sources = ["app/services/langchain_streaming.py", "playground/langchain_stream_probe.py"]
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "result_path": str(args.output.resolve()), "status": "running",
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
        "scope": "One synthetic real model stream, Python consumer only. No tools, database, application SSE endpoint or deployment validation. No induced real interruption.",
        "question": QUESTION, "http_requests": 0, "chunks": [],
        "first_text_ms": None, "partial_answer": "",
    }
    started = time.perf_counter()
    try:
        if not all((settings.openai_api_key, settings.openai_base_url, settings.openai_model)):
            raise ValueError("Model configuration is incomplete.")
        asyncio.run(consume(report, started))
        report["status"] = "completed_needs_review"
    except Exception as exc:
        report["status"] = "failed"
        report["error_type"] = type(exc).__name__
    report["elapsed_seconds"] = time.perf_counter() - started
    save(report)
    print(json.dumps({
        "status": report["status"], "http_requests": report["http_requests"],
        "chunks_received": len(report["chunks"]), "finish_reason": report.get("finish_reason"),
        "result_path": report["result_path"], "error_type": report.get("error_type"),
    }, ensure_ascii=False), flush=True)
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
