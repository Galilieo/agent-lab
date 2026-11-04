"""显式使用环境配置，比较真实原生/框架模型及预建Agent的合成场景。

uv run --offline --no-sync --env-file .env python -m playground.langchain_live_acceptance
只发送本脚本及固定fixture中的合成数据，不读取业务数据库或真实笔记。
共享Agent仅提供计算器，并阻断意外关键词MCP请求；RAG上下文直接构造，未测检索。
报告含合成回答及安全元数据，不记录配置对象、密钥、请求头或上游异常正文。
"""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import logging
from pathlib import Path
import re
import subprocess
import time
from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolMessage

from app.config import settings
from app.services import agent, langchain_adapter, langchain_agent, llm
from app.services.langchain_callbacks import ModelCallRecorder
from app.services.rag import DocumentChunk
from app.services.rag_answer import finalize_rag_answer
from app.services.rag_context import build_rag_context
from app.services.rag import RetrievedChunk
from app.tools import CALCULATOR_TOOL, execute_tool


DEFAULT_OUTPUT = Path("playground/results/langchain_live_acceptance_2026-11-04.json")
MAX_MODEL_CALLS = 27  # 8组共享Agent场景 + 1组预建Agent，每组至多3次。


def save(report):
    Path(report["result_path"]).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


def model_record(result):
    return {
        "model": result.model, "upstream_status": result.upstream_status,
        "latency_ms": result.latency_ms, "total_tokens": result.total_tokens,
        "outcome": "succeeded",
        "tool_calls": [{"name": call.name, "call_id": call.call_id,
                        **({"arguments": call.arguments} if call.name == "calculator" else {})}
                       for call in result.tool_calls],
    }


def checks_for(case, answer, sources, invalid_ids, executions):
    checks = {"no_invalid_citations": not invalid_ids}
    if case["id"] == "history":
        checks["history_code_recalled"] = "青榆7314" in answer
    elif case["id"] == "calculator":
        checks["calculator_executed"] = any(item["result"] == "437" for item in executions)
        checks["correct_answer"] = bool(re.search(r"(?<!\d)437(?!\d)", answer))
    elif case["id"] == "rag_facts":
        checks["facts_present"] = all(
            any(term.casefold() in answer.casefold() for term in group)
            for group in case["answer_term_groups"]
        )
        checks["expected_cited_sources"] = set(case["expected_sources"]) <= set(sources)
    else:
        checks["no_phone_number"] = not bool(re.search(
            r"(?<!\d)(?:1[3-9]\d{9}|\d{3,4}[- ]\d{7,8})(?!\d)", answer,
        ))
        checks["missing_information_signal"] = any(
            term in answer for term in ("未提供", "没有", "未记录", "未说明", "未找到", "未列出", "不足", "未给出")
        )
    return checks


def make_cases():
    fixture = json.loads(Path("playground/fixtures/rag_acceptance.json").read_text(encoding="utf-8"))
    chunks = [DocumentChunk(f"notes/{name}", 0, 0, len(text), text)
              for name, text in fixture["documents"].items()]
    context = build_rag_context([RetrievedChunk(chunk, 0.0) for chunk in chunks])
    cross = next(case for case in fixture["cases"] if case["id"] == "cross_document")
    phone = next(case for case in fixture["cases"] if case["id"] == "missing_phone")
    return [
        {"id": "history", "question": "请只回答我之前提供的本次临时验收代号。",
         "history": [{"role": "user", "content": "本次临时验收代号是青榆7314。"},
                     {"role": "assistant", "content": "好的。"}], "context": None},
        {"id": "calculator", "question": "请务必调用calculator计算23乘以19，然后简短回答结果。",
         "history": [], "context": None},
        {**cross, "id": "rag_facts", "history": [], "context": context},
        {**phone, "id": "missing_phone", "history": [], "context": context},
    ]


async def run(report):
    if not all((settings.openai_api_key, settings.openai_base_url, settings.openai_model)):
        raise ValueError("Model configuration is incomplete.")
    cases = make_cases()
    for backend, real_generate in (
        ("native", llm.generate_reply),
        ("langchain_adapter", langchain_adapter.generate_langchain_result),
    ):
        for case in cases:
            record = {"backend": backend, "case_id": case["id"], "question": case["question"],
                      "model_calls": [], "tool_executions": [], "review": None}
            report["cases"].append(record)
            report["phase"] = f"{backend}:{case['id']}"
            print(f"Running {report['phase']}", flush=True)
            save(report)

            async def observed_generate(*args, **kwargs):
                if report["model_calls_attempted"] >= MAX_MODEL_CALLS:
                    raise RuntimeError("Live acceptance budget exhausted.")
                report["model_calls_attempted"] += 1
                try:
                    result = await real_generate(*args, **kwargs)
                except llm.LLMRequestError as exc:
                    record["model_calls"].append({
                        "outcome": exc.outcome, "upstream_status": exc.upstream_status,
                        "latency_ms": exc.latency_ms, "error_type": type(exc).__name__,
                        "total_tokens": None,
                    })
                    raise
                record["model_calls"].append(model_record(result))
                return result

            def calculator_only(call):
                if call.name != "calculator":
                    raise ValueError("Only calculator is enabled for this probe.")
                result = execute_tool(call)
                record["tool_executions"].append({"name": call.name, "result": result})
                return result

            async def reject_keyword_search(*args, **kwargs):
                raise RuntimeError("Keyword MCP access is disabled for this probe.")

            context = case["context"]
            try:
                with (
                    patch.object(agent, "generate_reply", observed_generate),
                    patch.object(agent, "AVAILABLE_TOOLS", [CALCULATOR_TOOL]),
                    patch.object(agent, "execute_tool", calculator_only),
                    patch.object(agent, "execute_mcp_notes", reject_keyword_search),
                ):
                    result = await agent.run_agent(
                        case["question"], case["history"],
                        memory_context='Memory Context:\n{"reply_language":"中文","style":"简短"}',
                        rag_context=context.content if context else "",
                    )
                final = finalize_rag_answer(result, context.sources if context else [])
                source_ids = [f"{source.source}::{source.chunk_index}" for source in final.sources]
                record.update({"answer": final.answer, "source_ids": source_ids,
                               "invalid_ids": final.invalid_ids})
                record["automatic_checks"] = checks_for(
                    case, final.answer, source_ids, final.invalid_ids, record["tool_executions"],
                )
            except Exception as exc:
                record["error_type"] = type(exc).__name__
                save(report)
                raise
            save(report)

    # 预建Agent单独验证，不冒充它已返回项目AgentResult或真实HTTP状态。
    report["phase"] = "prebuilt_agent:calculator"
    print(f"Running {report['phase']}", flush=True)
    recorder = ModelCallRecorder()
    record = {"backend": "prebuilt_agent", "case_id": "calculator",
              "model_calls": [], "review": None}
    report["cases"].append(record)
    if report["model_calls_attempted"] + 3 > MAX_MODEL_CALLS:
        raise RuntimeError("Insufficient remaining budget for the prebuilt Agent.")
    try:
        messages = await langchain_agent.run_langchain_agent(
            "请务必调用calculator计算23乘以19，然后简短回答结果。", callbacks=[recorder],
        )
        answer = messages[-1].content
        record["answer"] = answer
        record["requested_tools"] = [call["name"] for message in messages
                                     if isinstance(message, AIMessage) for call in message.tool_calls]
        record["tool_results"] = [message.content for message in messages if isinstance(message, ToolMessage)]
        record["automatic_checks"] = {
            "calculator_requested": "calculator" in record["requested_tools"],
            "tool_returned_437": "437" in record["tool_results"],
            "correct_answer": isinstance(answer, str) and bool(re.search(r"(?<!\d)437(?!\d)", answer)),
        }
    except Exception as exc:
        record["error_type"] = type(exc).__name__
        raise
    finally:
        report["model_calls_attempted"] += len(recorder.records)
        record["model_calls"] = [{
            "outcome": call.outcome, "latency_ms": call.latency_ms,
            "total_tokens": call.total_tokens, "error_type": call.error_type,
        } for call in recorder.records]
        save(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new file to preserve earlier evidence.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.ERROR)
    started = time.perf_counter()
    source_files = ["app/services/llm.py", "app/services/agent.py", "app/services/langchain_adapter.py",
                    "app/services/langchain_agent.py", "playground/langchain_live_acceptance.py"]
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "status": "running",
        "result_path": str(args.output.resolve()),
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in source_files},
        "versions": {name: version(name) for name in ["langchain", "langchain-core", "langchain-deepseek"]},
        "scope": "Synthetic data; real configured model; native Agent + two model backends, plus one prebuilt Agent case. Shared prebuilt RAG context only, no retrieval/embedding/database/HTTP-route/deployment validation. No real notes or MCP access.",
        "max_model_calls": MAX_MODEL_CALLS, "model_calls_attempted": 0, "cases": [],
    }
    try:
        asyncio.run(run(report))
        report["status"] = "completed_needs_review"
    except Exception as exc:
        report["status"] = "failed"
        report["error_type"] = type(exc).__name__
    report["elapsed_seconds"] = time.perf_counter() - started
    report["total_tokens"] = sum(call.get("total_tokens") or 0
                                 for case in report["cases"] for call in case["model_calls"])
    save(report)
    print(json.dumps({key: report[key] for key in
                      ["status", "phase", "model_calls_attempted", "total_tokens", "result_path"]},
                     ensure_ascii=False), flush=True)
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
