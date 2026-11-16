"""提供按用途返回 JSON、记录输入消息的假模型客户端，不进行网络调用。"""

import json
from copy import deepcopy
from dataclasses import dataclass

from pydantic import JsonValue


@dataclass(frozen=True)
class RecordedModelCall:
    """保存调用用途及消息快照，供测试检查实际传入的上下文。"""

    purpose: str
    messages: list[dict[str, str]]


class FakeModelClient:
    """由测试设置各用途的响应，未知用途应明确失败。"""

    def __init__(self) -> None:
        self.responses: dict[str, JsonValue] = {}
        self.calls: list[RecordedModelCall] = []

    async def complete(self, purpose: str, messages: list[dict[str, str]]) -> str:
        """返回预设 JSON 文本，并保存不随调用方修改而变化的消息快照。"""
        self.calls.append(RecordedModelCall(purpose, deepcopy(messages)))
        return json.dumps(self.responses[purpose], ensure_ascii=False)
