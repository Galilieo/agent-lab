"""LangChain 单次模型调用入口，供独立调用与原生实现对照。

将应用提供的问题和历史交给 ChatDeepSeek，返回框架的 AIMessage。
调用时会请求配置的模型服务；本层不执行工具、写入数据库或映射 HTTP 状态。
"""

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_deepseek import ChatDeepSeek

from app.config import settings


def build_chat_prompt() -> ChatPromptTemplate:
    """声明系统文本、完整历史消息和当前问题的模板。

    history 按消息列表插入；传入变量值中的花括号作为数据保留。
    返回模板本身，不调用模型或保存会话历史。
    """
    return ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{message}"),
    ])


async def generate_langchain_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    system_prompt: str = "You are a helpful assistant.",
) -> AIMessage:
    """按系统指令、旧历史、当前问题调用一次模型并返回消息对象。

    不修改传入的 history；网络或 SDK 异常交由调用方处理。
    AIMessage 代表一次模型输出，不保证整轮 Agent 已获得最终回答。
    """
    model = ChatDeepSeek(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        api_base=settings.openai_base_url,
        timeout=60.0,
        max_retries=0,
    )

    prompt = build_chat_prompt()
    chain = prompt | model

    return await chain.ainvoke({
        "system_prompt": system_prompt,
        "history": history or [],
        "message": message,
    })
