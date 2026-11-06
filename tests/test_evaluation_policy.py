"""复用合成题检查两组评测口径；只调用纯函数，不执行真实模型探针。"""

import json

from playground import rag_acceptance_probe as probe


def test_evaluation_policy_uses_mode_for_checks_and_review_rubric():
    """关闭组不检查资料答案命中，开启组保留检查，复核标准随场景选择。"""
    fixture = json.loads(probe.FIXTURE_PATH.read_text(encoding="utf-8"))
    case = next(item for item in fixture["cases"] if item["id"] == "batch_tag")
    unknown = {"answer": "当前没有资料，无法确定。", "sources": [], "invalid_citation_ids": []}

    without = probe.automatic_signals(case, unknown, [], mode="without_knowledge")
    assert without["expected_terms_present"] is None
    assert without["expected_cited_sources_present"] is None
    assert without["no_invalid_citation_ids"] is True
    assert without["knowledge_search_count"] == 0

    with_missing = probe.automatic_signals(case, unknown, [], mode="with_knowledge")
    assert with_missing["expected_terms_present"] is False
    assert with_missing["expected_cited_sources_present"] is False

    answer = {
        "answer": "索引批次标签是苍鹭5836。[notes/service.md::0]",
        "sources": [{"id": "notes/service.md::0"}], "invalid_citation_ids": [],
    }
    calls = [{"tool_names": ["search_knowledge"]}]
    with_answer = probe.automatic_signals(case, answer, calls, mode="with_knowledge")
    assert with_answer["expected_terms_present"] is True
    assert with_answer["expected_cited_sources_present"] is True
    assert with_answer["knowledge_search_count"] == 1

    # 出现了资料答案也不把关闭组改成适用，更不在此自动输出质量pass。
    without_with_answer = probe.automatic_signals(case, answer, calls, mode="without_knowledge")
    assert without_with_answer["expected_terms_present"] is None
    assert without_with_answer["expected_cited_sources_present"] is None

    rubric = probe.review_rubric_for(case, mode="without_knowledge")
    assert rubric != case["review"]
    assert "不编造" in rubric
    assert probe.review_rubric_for(case, mode="with_knowledge") == case["review"]
    for case_id in ("missing_phone", "greeting"):
        item = next(item for item in fixture["cases"] if item["id"] == case_id)
        assert probe.review_rubric_for(item, mode="with_knowledge") == item["review"]
        if case_id == "greeting":
            assert probe.review_rubric_for(item, mode="without_knowledge") == item["review"]
