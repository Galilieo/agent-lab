"""只读汇总已保存的RAG评测报告，不导入模型入口或重新执行评测。

运行：.venv/bin/python -m playground.evaluation_summary 报告.json
按mode分别打印请求结果、复核覆盖、耗时和已记录用量，不改原报告。
"""

import argparse
import json
from pathlib import Path


def summarize_cases(cases: list[dict]) -> dict:
    """汇总同组已开始的案例记录；无HTTP结果/复核/用量不假装已知。

    cases只包含已开始的案例，不接收计划但未执行的占位行。
    HTTP成功沿本探针/chat契约为200；耗时均值包含有记录的成功/失败请求。
    用量只汇总model_calls内已记录调用，不推断失败调用的供应商用量。
    """
    attempted = len(cases)
    succeeded = [case for case in cases if case.get("http_status") == 200]
    http_failed = sum(
        case.get("http_status") is not None
        and case["http_status"] != 200
        for case in cases
    )
    http_unknown = sum(
        case.get("http_status") is None for case in cases
    )

    outcomes = [
        (case.get("manual_review") or {}).get("outcome")
        for case in succeeded
    ]
    quality_passed = sum(
        outcome in {"pass", "pass_with_quality_note"}
        for outcome in outcomes
    )
    quality_failed = sum(
        outcome in {"changes_required", "fail"}
        for outcome in outcomes
    )
    reviewed = quality_passed + quality_failed

    latencies = [
        case["elapsed_seconds"]
        for case in cases
        if case.get("elapsed_seconds") is not None
    ]
    calls = [
        call
        for case in cases
        for call in case.get("model_calls", [])
    ]
    know_tokens = [
        call["total_tokens"]
        for call in calls
        if call.get("total_tokens") is not None
    ]

    return {
        "attempted": attempted,
        "http_succeeded": len(succeeded),
        "http_failed": http_failed,
        "http_unknown": http_unknown,
        "request_failure_rate": (
            http_failed / attempted
            if attempted and http_unknown == 0 else None
        ),
        "reviewed": reviewed,
        "quality_passed": quality_passed,
        "quality_failed": quality_failed,
        "unreviewed": len(succeeded) - reviewed,
        "quality_pass_rate": (
            quality_passed / reviewed if reviewed else None
        ),
        "latency_samples": len(latencies),
        "mean_elapsed_seconds": (
            sum(latencies) / len(latencies) if latencies else None
        ),
        "model_calls_recorded": len(calls),
        "recorded_tokens_sum": sum(know_tokens) if know_tokens else None,
        "model_calls_without_usage": len(calls) - len(know_tokens)
    }


def main():
    """读入一个本地报告，按组调用汇总函数，只向标准输出打印派生结果。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    groups = {}
    for case in report["cases"]:
        groups.setdefault(case["mode"], []).append(case)
    result = {
        "source_report": str(args.report.resolve()),
        "source_status": report.get("status"),
        "by_mode": {mode: summarize_cases(cases) for mode, cases in groups.items()},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
