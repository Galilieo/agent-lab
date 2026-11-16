"""检查假模型按用途返回 JSON，并保留可用于上下文断言的调用记录。"""

import json

from jobpilot.tests.fakes import FakeModelClient


async def test_fake_returns_purpose_response_and_keeps_message_snapshot(
    fake_model_client: FakeModelClient,
) -> None:
    """合成消息传入后再修改原对象，历史快照仍应保持收到时的内容。"""
    fake_model_client.responses["parse_jd"] = {"keywords": ["Python"]}
    messages = [{"role": "user", "content": "<untrusted_data>合成 JD</untrusted_data>"}]

    response = await fake_model_client.complete("parse_jd", messages)
    messages[0]["content"] = "调用后修改原对象"

    assert json.loads(response) == {"keywords": ["Python"]}
    assert len(fake_model_client.calls) == 1
    assert fake_model_client.calls[0].purpose == "parse_jd"
    assert fake_model_client.calls[0].messages == [
        {"role": "user", "content": "<untrusted_data>合成 JD</untrusted_data>"}
    ]
