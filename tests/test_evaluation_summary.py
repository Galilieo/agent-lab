"""用少量合成报告记录验证离线统计口径，不调用模型或改写历史报告。"""

import pytest

from playground.evaluation_summary import summarize_cases


def test_summary_counts_attempts_separately_from_reviews_and_missing_usage():
    """计划6题但只开始3题，失败分母为3；未复核和未知用量不能当作通过/零。"""
    # 未运行的另外3题不进入cases；这些字典是函数输入，不是假模型调用。
    cases = [
        {"http_status": 200, "elapsed_seconds": 1.0,
         "manual_review": {"outcome": "pass_with_quality_note"},
         "model_calls": [{"total_tokens": 10}]},
        {"http_status": 200, "elapsed_seconds": 3.0,
         "manual_review": None, "model_calls": [{"total_tokens": None}]},
        {"http_status": 503, "elapsed_seconds": 5.0,
         "manual_review": {"outcome": "pass"}, "model_calls": []},
    ]
    result = summarize_cases(cases)

    assert result["attempted"] == 3
    assert result["http_succeeded"] == 2
    assert result["http_failed"] == 1
    assert result["http_unknown"] == 0
    assert result["request_failure_rate"] == pytest.approx(1 / 3)
    # HTTP失败行即使误带pass也不进入成功回答的质量统计。
    assert result["reviewed"] == 1
    assert result["quality_passed"] == 1
    assert result["quality_failed"] == 0
    assert result["unreviewed"] == 1
    assert result["quality_pass_rate"] == 1.0
    assert result["latency_samples"] == 3
    assert result["mean_elapsed_seconds"] == 3.0
    assert result["model_calls_recorded"] == 2
    assert result["recorded_tokens_sum"] == 10
    assert result["model_calls_without_usage"] == 1


def test_summary_keeps_empty_and_incomplete_results_unknown():
    """零尝试不除零；已开始但缺HTTP结果时不报确定失败率，未复核不判通过。"""
    empty = summarize_cases([])
    assert empty["attempted"] == empty["reviewed"] == empty["unreviewed"] == 0
    assert empty["request_failure_rate"] is None
    assert empty["quality_pass_rate"] is None
    assert empty["mean_elapsed_seconds"] is None
    assert empty["recorded_tokens_sum"] is None

    result = summarize_cases([
        {"http_status": 200, "manual_review": {"outcome": "changes_required"}, "model_calls": []},
        {"manual_review": None, "model_calls": []},
    ])
    assert result["attempted"] == 2
    assert result["http_failed"] == 0
    assert result["http_unknown"] == 1
    assert result["request_failure_rate"] is None
    assert result["reviewed"] == result["quality_failed"] == 1
    assert result["quality_passed"] == result["unreviewed"] == 0
    assert result["quality_pass_rate"] == 0.0
    assert result["latency_samples"] == result["model_calls_recorded"] == 0
