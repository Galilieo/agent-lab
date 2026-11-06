"""固定合成问题通过正式 /chat 路径比较有/无语义工具；显式运行才会调用真实模型。

运行：uv run --offline --no-sync --env-file .env python -m playground.rag_acceptance_probe
使用临时 SQLite/Chroma、本地 BGE-M3 与已配置聊天 API，不修改真实配置或索引。
HTTP 入口通过进程内 TestClient 执行，不代表已部署服务器的网络验收。
受控工具清单排除 search_notes，并阻断意外的关键词 MCP 调用；其余链路使用真实实现。
报告只记录合成材料、回答和调用元数据；自动信号不替代语义人工复核。
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

import chromadb
from fastapi.testclient import TestClient
import httpx

from app import main as chat_app
from app.config import settings
from app.database import create_connection
from app.services import agent, rag_tools
from app.services.embedding import EMBEDDING_MODEL
from app.services.rag_index import build_index
from app.services.rag_retrieval import retrieve
from app.tools import CALCULATOR_TOOL, CURRENT_TIME_TOOL


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "rag_acceptance.json"
RESULT_PATH = Path(__file__).parent / "results" / "rag_acceptance_probe.json"
MAX_CHAT_MODEL_CALLS = 36


async def reject_keyword_search(*args, **kwargs):
    """即使模型返回未公布的关键词工具名，也不允许本探针读取真实笔记。"""
    raise RuntimeError("Keyword MCP search is disabled in the synthetic acceptance probe.")


def save_report(report):
    result_path = Path(report["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def snapshot_hits(hits):
    return [{
        "id": f"{hit.chunk.source}::{hit.chunk.chunk_index}",
        "distance": hit.distance, "text": hit.chunk.text,
    } for hit in hits]


def review_rubric_for(case, *, mode):
    """按组别选择复核标准；无资料的虚构资料题检查不足说明与不编造。"""
    if mode not in {"without_knowledge", "with_knowledge"}:
        raise ValueError("Unsupported evaluation mode.")

    if (
        mode == "without_knowledge"
        and case["kind"] != "no_retrieval_needed"
    ):
        return "未提供知识资料，应说明无法确定，不编造资料事实或来源。"

    return case["review"]


def automatic_signals(case, body, model_calls, *, mode):
    """记录适用于当前组别的辅助信号；不适用为None，不自动判定语义通过。"""
    if mode not in {"without_knowledge", "with_knowledge"}:
        raise ValueError("Unsupported evaluation mode.")

    answer = body.get("answer", "")
    expected = set(case["expected_sources"])
    cited = {source["id"] for source in body.get("sources", [])}
    check_reference_answer = mode == "with_knowledge"
    return {
        "expected_terms_present": all(
            any(term.casefold() in answer.casefold() for term in group)
            for group in case["answer_term_groups"]
        ) if check_reference_answer and case["answer_term_groups"] else None,
        "expected_cited_sources_present": (
            expected <= cited
            if check_reference_answer and expected else None
        ),
        "no_invalid_citation_ids": body.get("invalid_citation_ids") == [],
        "knowledge_search_count": sum(
            call["tool_names"].count("search_knowledge")
            for call in model_calls
        ),
        "phone_like_number_present": bool(
            re.search(
                r"(?<!\d)(?:1[3-9]\d{9}|\d{3,4}[- ]\d{7,8})(?!\d)",
                answer,
            )
        ) if case["kind"] == "insufficient_evidence" else None
    }


def persisted_counts(database_path, conversation_id):
    connection = create_connection(database_path)
    try:
        return {
            "messages": connection.execute(
                "SELECT COUNT(*) FROM message WHERE conversation_id = ?", (conversation_id,),
            ).fetchone()[0],
            "model_calls": connection.execute(
                "SELECT COUNT(*) FROM model_call WHERE conversation_id = ?", (conversation_id,),
            ).fetchone()[0],
        }
    finally:
        connection.close()


def run(report):
    if not all((settings.openai_api_key, settings.openai_base_url, settings.openai_model)):
        raise ValueError("Chat API configuration is incomplete.")
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    with httpx.Client(timeout=10.0, trust_env=False) as client:
        response = client.get("http://127.0.0.1:11434/api/tags")
        response.raise_for_status()
        available = {model["name"] for model in response.json()["models"]}
        if EMBEDDING_MODEL not in available:
            raise ValueError("Expected local embedding model is not installed.")

    with TemporaryDirectory(prefix="agent-lab-rag-acceptance-") as folder:
        root = Path(folder)
        notes_dir = root / "notes"
        notes_dir.mkdir()
        for name, text in fixture["documents"].items():
            (notes_dir / name).write_text(text, encoding="utf-8")
        index_dir = root / "chroma"
        database_path = str(root / "chat.sqlite3")
        report["phase"] = "build_index"
        print("Building synthetic index with local Ollama...", flush=True)
        report["indexed_chunks"] = asyncio.run(build_index(notes_dir, index_dir, chunk_size=180, overlap=30))

        # 单独观察问题本身的检索，避免把模型没调用工具误判为向量检索失败。
        report["phase"] = "retrieval_observations"
        for case in fixture["cases"]:
            if case["kind"] == "no_retrieval_needed":
                continue
            hits = asyncio.run(retrieve(case["question"], index_dir))
            found = snapshot_hits(hits)
            expected = set(case["expected_sources"])
            report["retrieval_observations"].append({
                "case_id": case["id"], "hits": found,
                "expected_sources": sorted(expected),
                "expected_source_recall_at_3": len(expected & {hit["id"] for hit in found}) / len(expected)
                if expected else None,
            })
        save_report(report)

        real_generate = agent.generate_reply
        real_retrieve = rag_tools.retrieve
        active_case = {}

        async def observed_generate(*args, **kwargs):
            if report["chat_model_calls_attempted"] >= MAX_CHAT_MODEL_CALLS:
                raise RuntimeError("Acceptance model-call budget exhausted.")
            report["chat_model_calls_attempted"] += 1
            result = await real_generate(*args, **kwargs)
            active_case["record"]["model_calls"].append({
                "model": result.model, "upstream_status": result.upstream_status,
                "latency_ms": result.latency_ms, "total_tokens": result.total_tokens,
                "tool_names": [call.name for call in result.tool_calls],
            })
            return result

        async def observed_retrieve(question, persist_directory, *, top_k=3):
            hits = await real_retrieve(question, persist_directory, top_k=top_k)
            active_case["record"]["tool_retrievals"].append({"query": question, "hits": snapshot_hits(hits)})
            return hits

        # 仅改变本次进程内运行条件；不写 .env，不让关键词 MCP 工具访问真实笔记。
        with (
            patch.object(settings, "database_path", database_path),
            patch.object(settings, "rag_index_path", None),
            patch.object(agent, "AVAILABLE_TOOLS", [CALCULATOR_TOOL, CURRENT_TIME_TOOL]),
            patch.object(agent, "execute_mcp_notes", reject_keyword_search),
            patch.object(agent, "generate_reply", observed_generate),
            patch.object(rag_tools, "retrieve", observed_retrieve),
            TestClient(chat_app.app, raise_server_exceptions=False) as client,
        ):
            for mode in ("without_knowledge", "with_knowledge"):
                settings.rag_index_path = str(index_dir) if mode == "with_knowledge" else None
                for case in fixture["cases"]:
                    record = {
                        "mode": mode, "case_id": case["id"], "kind": case["kind"],
                        "question": case["question"], "review_rubric": review_rubric_for(case, mode=mode),
                        "model_calls": [], "tool_retrievals": [], "manual_review": None,
                    }
                    report["cases"].append(record)
                    active_case["record"] = record
                    report["phase"] = f"chat:{mode}:{case['id']}"
                    print(f"Calling /chat: {mode} / {case['id']}", flush=True)
                    conversation_id = f"acceptance-{mode}-{case['id']}"
                    started = time.perf_counter()
                    response = client.post("/chat", json={
                        "conversation_id": conversation_id, "message": case["question"],
                    })
                    record["elapsed_seconds"] = time.perf_counter() - started
                    record["http_status"] = response.status_code
                    if response.status_code == 200:
                        record["response"] = response.json()
                        record["automatic_signals"] = automatic_signals(
                            case, response.json(), record["model_calls"], mode=mode,
                        )
                    else:
                        # 不记录潜在敏感上游异常正文；合成回答仅在成功结果中保存。
                        record["error"] = "HTTP request did not succeed."
                    record["persisted"] = persisted_counts(database_path, conversation_id)
                    save_report(report)
                    if response.status_code != 200:
                        raise RuntimeError("Acceptance HTTP case failed; remaining cloud calls stopped.")
        report["status"] = "completed_needs_manual_review"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=RESULT_PATH, help="结果路径；复验时另存文件以保留原始观察。")
    args = parser.parse_args()
    # 仅保留进度；业务日志不写回答/凭据，报告中的回答全部来自本次合成问题。
    logging.basicConfig(level=logging.WARNING)
    started = time.perf_counter()
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "status": "running",
        "result_path": str(args.output.resolve()),
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "knowledge_tool_description": agent.SEARCH_KNOWLEDGE_TOOL["function"]["description"],
        "embedding_model": EMBEDDING_MODEL, "chat_model": settings.openai_model,
        "chromadb_version": chromadb.__version__, "max_chat_model_calls": MAX_CHAT_MODEL_CALLS,
        "chat_model_calls_attempted": 0, "retrieval_observations": [], "cases": [],
        "scope": "Synthetic fixed cases; real local embeddings, Chroma, cloud chat and production /chat handler via in-process TestClient. Keyword MCP tool excluded and unexpected keyword MCP calls blocked. No deployed-server network test.",
    }
    try:
        run(report)
    except Exception as exc:
        report["status"] = "failed"
        report["error_type"] = type(exc).__name__
    report["elapsed_seconds"] = time.perf_counter() - started
    report["total_tokens"] = sum(call.get("total_tokens") or 0 for case in report["cases"] for call in case["model_calls"])
    save_report(report)
    print(json.dumps({
        "status": report["status"], "phase": report.get("phase"),
        "completed_cases": len([case for case in report["cases"] if "http_status" in case]),
        "chat_model_calls_attempted": report["chat_model_calls_attempted"],
        "total_tokens": report["total_tokens"], "result_path": report["result_path"],
        "error_type": report.get("error_type"),
    }, ensure_ascii=False), flush=True)
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
