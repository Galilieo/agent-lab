"""验证应用声明的聊天模板如何插入变量和历史消息。

真实运行 ChatPromptTemplate 格式化，检查角色、顺序及花括号文本的保留。
不创建模型客户端或发送 HTTP；模型接线复用 test_langchain_llm.py 的回归。
"""

from app.services import langchain_llm


def test_chat_prompt_preserves_history_roles_and_literal_variable_values() -> None:
    """历史按消息展开，输入值中的花括号不被当作第二轮模板变量。"""
    history = [
        {"role": "user", "content": "我叫小宇，代码中有 {old_key}。"},
        {"role": "assistant", "content": "记住了"},
    ]
    prompt = langchain_llm.build_chat_prompt()

    value = prompt.invoke({
        "system_prompt": "请保留 {literal}，并简洁回答。",
        "history": history,
        "message": '解释 {"name": "小宇"} 和 {unknown}。',
    })

    assert [(message.type, message.content) for message in value.to_messages()] == [
        ("system", "请保留 {literal}，并简洁回答。"),
        ("human", "我叫小宇，代码中有 {old_key}。"),
        ("ai", "记住了"),
        ("human", '解释 {"name": "小宇"} 和 {unknown}。'),
    ]
    assert history == [
        {"role": "user", "content": "我叫小宇，代码中有 {old_key}。"},
        {"role": "assistant", "content": "记住了"},
    ]
