"""使用 LangChain 的预建 Agent 执行计算器工具循环。

独立对照原生 Agent，返回历史、本轮问题及模型/工具交互的完整消息列表。
不接入 HTTP 路由或数据库；模型与框架异常继续交给调用方。
"""

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage, HumanMessage, convert_to_messages
from langchain_deepseek import ChatDeepSeek

from app.config import settings
from app.services.langchain_tools import build_calculator_tool


async def run_langchain_agent(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    callbacks: list[AsyncCallbackHandler] | None = None,
) -> list[BaseMessage]:
    """执行计算器 Agent，正常结束时返回完整消息轨迹，不修改输入历史。

    每次运行最多调用模型三次，超限抛框架异常。
    此限制在下一次模型调用前检查，不保证最后一次工具请求尚未执行；
    不能直接当作原生 Agent 的执行前预算边界使用。
    """
    model = ChatDeepSeek(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        api_base=settings.openai_base_url,
        timeout=60.0,
        max_retries=0,
    )

    agent = create_agent(
        model=model,
        tools=[build_calculator_tool()],
        system_prompt="You are helpful assistants.",
        middleware=[
            ModelCallLimitMiddleware(
                run_limit=3,
                exit_behavior="error",
            ),
        ],
    )

    messages = [
        *convert_to_messages(history or []),
        HumanMessage(content=message),
    ]

    state = await agent.ainvoke(
        {"messages": messages},
        config={"callbacks": callbacks or []},
    )
    return state["messages"]
