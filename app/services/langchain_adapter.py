"""普通文本模型调用的项目契约适配，保留框架教学入口。

HTTP观察仅保存实际状态码，框架负责消息与SDK协议；适配层返回项目LLMResult。
本入口不声明工具、不执行Agent循环、不保存数据库或决定本服务的HTTP状态。
"""

from dataclasses import dataclass
from time import perf_counter

from httpx import AsyncClient, Client, Response
from langchain_core.messages import AIMessage
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
    LLMUpstreamError,
)


@dataclass
class _HttpObservation:
    """每次适配调用独享，只记录HTTP响应状态，不保存正文或请求头。"""

    upstream_status: int | None = None


async def _invoke_observed_chat(
    message: str,
    history: list[dict[str, str]] | None,
    system_prompt: str,
    observation: _HttpObservation,
) -> AIMessage:
    """调用模板与模型，并在实际HTTP响应到达时记录状态。

    SDK异常原样向上抛出。关闭缓存及SDK重试，使观测对应本次唯一请求；
    两个HTTP客户端由本层创建并关闭，异步模型调用只使用异步客户端。
    """
    async def record_response(response: Response) -> None:
        observation.upstream_status = response.status_code

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
            chain = build_chat_prompt() | model
            response = await chain.ainvoke({
                "system_prompt": system_prompt,
                "history": history or [],
                "message": message,
            })

    if observation.upstream_status is None:
        raise RuntimeError("Model returned without an observed HTTP response.")
    return response


async def generate_langchain_result(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    system_prompt: str = "You are a helpful assistant.",
) -> LLMResult:
    """普通文本调用返回项目结果，将SDK及响应解析错误转换为既有异常。

    不声明工具，意外工具响应应按不可用响应处理，不能丢弃工具请求冒充完成。
    空字符串沿原生单次调用语义保留，由Agent/RAG等上层判断最终正文是否可用。
    耗时覆盖客户端创建、框架请求与解析及关闭，不等同于纯HTTP网络耗时。
    未拿到HTTP响应的本地配置错误原样传播，不冒充上游返回了坏响应。
    """
    observation = _HttpObservation()
    started_at = perf_counter()

    try:
        response = await _invoke_observed_chat(
            message, history, system_prompt, observation,
        )

        if (
            not isinstance(response.content, str)
            or response.tool_calls
            or response.invalid_tool_calls
        ):
            raise ValueError("Expected a plain text model response.")

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
        answer=response.content,
        model=settings.openai_model,
        upstream_status=observation.upstream_status,
        latency_ms=(perf_counter() - started_at) * 1000,
        prompt_tokens=usage.get("input_tokens"),
        completion_tokens=usage.get("output_tokens"),
        total_tokens=usage.get("total_tokens"),
        tool_calls=[],
    )
