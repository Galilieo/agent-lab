"""将模型的语义检索请求转换为校验后的检索和预算选择，不生成回答。

调用方提供索引目录与限制，接收 RagContext；工具消息回传和来源登记由调用方完成。
"""

from pathlib import Path

from app.services.llm import LLMToolCall
from app.services.rag_context import RagContext, build_rag_context
from app.services.rag_retrieval import retrieve
from app.tools import SearchKnowledgeArguments


async def execute_knowledge_search(
    tool_call: LLMToolCall,
    persist_directory: Path,
    *,
    top_k: int = 3,
    max_chars: int = 4000,
) -> RagContext:
    """只检索和选择片段；空结果正常返回，参数与服务错误继续传播。

    content 是准备回传模型的参考文本，sources 与该文本中的片段一一对应。
    本函数不写入 tool 消息或登记来源；调用方完成回传后才能把 sources 作为
    本轮已交付资料。空检索或预算无入选项都返回空 RagContext，不直接结束 Agent。
    model_validate_json 校验 arguments；目录、TopK 和预算来自调用方。
    """
    if tool_call.name != "search_knowledge":
        raise ValueError("Unsupported knowledge tool.")

    if max_chars < 0:
        raise ValueError("max_chars must be non-negative.")

    arguments = SearchKnowledgeArguments.model_validate_json(
        tool_call.arguments
    )

    hits = await retrieve(
        arguments.query,
        persist_directory,
        top_k=top_k,
    )

    return build_rag_context(hits, max_chars=max_chars)
