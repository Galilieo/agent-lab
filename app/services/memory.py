"""根据当前用户消息预筛选是否需要调用记忆提取器。

预筛选只决定消息是否值得进入提取流程，不生成候选或批准数据库写入。
规则只做有限短语匹配，不调用模型或数据库，也不承担完整的语义判断。
"""


def should_extract_memory(message: str) -> bool:
    """判断当前消息是否值得进入记忆提取流程。

    本条不保存要求优先于正向线索。返回 True 仅表示需要进一步提取，
    不代表允许保存；提取器仍可返回 skip，候选还需通过后续校验。
    """
    blocked_markers = (
        "不要保存",
        "别保存",
        "不要记住",
        "别记住",
    )
    trigger_markers = (
        "记住",
        "记下来",
        "以后",
        "默认",
        "我的学习目标",
        "我的技术栈",
    )

    # 不保存要求优先，避免其中的正向线索触发提取。
    if any(marker in message for marker in blocked_markers):
        return False

    # 不把“这次”作为否决词，同一条消息也可能同时表达长期偏好。
    return any(marker in message for marker in trigger_markers)
