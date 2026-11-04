"""单次模型调用的项目契约适配，保留框架教学入口。

HTTP观察临时保存状态码与原始消息，框架负责消息与SDK协议；返回项目LLMResult。
本层传递工具声明和交互消息，不执行工具/Agent循环、写库或决定本服务HTTP状态。
"""

from dataclasses import dataclass
from json import JSONDecodeError
from time import perf_counter

from httpx import AsyncClient, Client, Response
from langchain_core.messages import AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_deepseek import ChatDeepSeek
from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
)

from app.config import settings
from app.services.langchain_llm import build_chat_prompt
from app.services.llm import (
    LLMConnectionError,
    LLMResponseError,
    LLMResult,
    LLMTimeoutError,
    LLMToolCall,
    LLMUpstreamError,
)


@dataclass
class _HttpObservation:
    """每次调用独享，原始消息只供内存转换，不写日志或持久化完整响应。"""

    upstream_status: int | None = None
    raw_message: dict | None = None


def parse_tool_calls(message_data: dict) -> list[LLMToolCall]:
    """提取原始工具请求字段，不解析arguments或执行工具。

    arguments原文保留，即使其中JSON非法也交给工具处理层校验。
    缺少id/function等协议字段的异常交给外层转换成模型响应错误。
    """
    return [
        LLMToolCall(
            call_id=tool_call["id"],
            name=tool_call["function"]["name"],
            arguments=tool_call["function"]["arguments"],
        )
        for tool_call in message_data.get("tool_calls") or []
    ]


async def _invoke_observed_chat(
    message: str,
    history: list[dict[str, str]] | None,
    system_prompt: str,
    observation: _HttpObservation,
    *,
    tools: list[dict] | None = None,
    additional_messages: list[dict] | None = None,
    memory_context: str = "",
    rag_context: str = "",
) -> AIMessage:
    """调用模板与模型，并在实际HTTP响应到达时记录状态。

    SDK异常原样向上抛出。关闭缓存及SDK重试，使观测对应本次唯一请求；
    两个HTTP客户端由本层创建并关闭，异步模型调用只使用异步客户端。
    """
    async def record_response(response: Response) -> None:
        observation.upstream_status = response.status_code
        # 非流式响应先读入缓冲，SDK稍后仍能读取同一正文。
        await response.aread()
        try:
            message_data = response.json()["choices"][0]["message"]
        except (JSONDecodeError, UnicodeDecodeError, KeyError, IndexError, TypeError):
            # 不让HTTP错误正文/非法JSON在钩子中冒充连接错误；交给SDK及外层分类。
            return
        if isinstance(message_data, dict):
            observation.raw_message = message_data

    reference_messages = []
    if memory_context:
        reference_messages.append({
            "role": "user",
            "content": memory_context,
        })

    if rag_context:
        reference_messages.append({
            "role": "user",
            "content": rag_context,
        })

    with Client() as sync_http:
        async with AsyncClient(
            event_hooks={"response": [record_response]},
        ) as async_http:
            model = ChatDeepSeek(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                api_base=settings.openai_base_url,
                timeout=60.0,
                max_retries=0,
                cache=False,
                http_client=sync_http,
                http_async_client=async_http,
            )
            prompt = build_chat_prompt()
            prompt.messages.insert(1, MessagesPlaceholder(
                variable_name="reference_messages", optional=True,
            ))
            prompt.append(MessagesPlaceholder(
                variable_name="additional_messages", optional=True,
            ))
            bound_model = (
                model.bind_tools(tools, tool_choice="auto")
                if tools is not None else model
            )
            chain = prompt | bound_model
            response = await chain.ainvoke({
                "system_prompt": system_prompt,
                "reference_messages": reference_messages,
                "history": history or [],
                "message": message,
                "additional_messages": additional_messages or [],
            })

    if observation.upstream_status is None:
        raise RuntimeError("Model returned without an observed HTTP response.")
    return response


async def generate_langchain_result(
    message: str,
    history: list[dict[str, str]] | None = None,
    tools: list[dict] | None = None,
    additional_messages: list[dict] | None = None,
    *,
    system_prompt: str = "You are a helpful assistant.",
    memory_context: str = "",
    rag_context: str = "",
) -> LLMResult:
    """返回项目结果与原始工具请求，将SDK及协议解析错误转换为既有异常。

    tools由应用提供，额外交互消息在当前问题后传递；工具参数不在本层解码。
    未传工具声明时，意外工具响应按不可用响应处理，不能丢弃请求冒充完成。
    空字符串沿原生单次调用语义保留，由Agent/RAG等上层判断最终正文是否可用。
    耗时覆盖客户端创建、框架请求与解析及关闭，不等同于纯HTTP网络耗时。
    未拿到HTTP响应的本地配置错误原样传播，不冒充上游返回了坏响应。
    """
    observation = _HttpObservation()
    started_at = perf_counter()

    try:
        response = await _invoke_observed_chat(
            message, history, system_prompt, observation,
            tools=tools, additional_messages=additional_messages,
            memory_context=memory_context,
            rag_context=rag_context,
        )

        if observation.raw_message is None:
            raise ValueError("Mssing raw model message.")


        message_data = observation.raw_message
        tool_calls = parse_tool_calls(message_data)
        answer = message_data["content"]

        if answer is not None and not isinstance(answer, str):
            raise ValueError("Expected string or null content.")

        if not tools and tool_calls:
            raise ValueError("Received an unexpected tool request.")

    except (APITimeoutError, APIConnectionError, APIStatusError) as exc:
        if isinstance(exc, APITimeoutError):
            error_type = LLMTimeoutError
        elif isinstance(exc, APIConnectionError):
            error_type = LLMConnectionError
        else:
            error_type = LLMUpstreamError

        upstream_status = (
            exc.status_code
            if isinstance(exc, APIStatusError)
            else observation.upstream_status
        )

        raise error_type(
            "LangChain model request failed.",
            model=settings.openai_model,
            upstream_status=upstream_status,
            latency_ms=(perf_counter() - started_at) * 1000,
        ) from exc

    except (
        APIResponseValidationError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
    ) as exc:
        if observation.upstream_status is None:
            raise

        raise LLMResponseError(
            "LangChain returned an invalid response.",
            model=settings.openai_model,
            upstream_status=observation.upstream_status,
            latency_ms=(perf_counter() - started_at) * 1000,
        ) from exc

    usage = response.usage_metadata or {}

    return LLMResult(
        answer=answer,
        model=settings.openai_model,
        upstream_status=observation.upstream_status,
        latency_ms=(perf_counter() - started_at) * 1000,
        prompt_tokens=usage.get("input_tokens"),
        completion_tokens=usage.get("output_tokens"),
        total_tokens=usage.get("total_tokens"),
        tool_calls=tool_calls,
    )
