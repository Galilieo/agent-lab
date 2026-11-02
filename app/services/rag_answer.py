"""严格知识库问答编排与共用的回答引用收尾。

严格问答在生成前检索；收尾函数只处理已经生成的回答与本轮交付资料。
返回展示文本、合法引用来源和原始调用结果，不负责普通 Agent 的工具循环。
"""

from dataclasses import dataclass
from pathlib import Path

from app.services.agent import AgentResult, run_agent
from app.services.llm import LLMResult
from app.services.rag import DocumentChunk
from app.services.rag_citations import check_citations
from app.services.rag_context import build_rag_context
from app.services.rag_retrieval import retrieve


NO_MATERIAL_ANSWER = "现有资料中没有可用于回答的片段，请补充资料后再试。"
CITATION_WARNING = "提示：部分引用无法对应到本轮资料，请核对原文。"


@dataclass(frozen=True)
class RagAnswer:
    """sources 只含正文引用且 ID 属于本轮白名单的片段，按首次引用顺序去重。

    ID 合法不证明语义支持；answer 可包含应用标注，model_calls 保留原始调用结果。
    """

    answer: str
    sources: list[DocumentChunk]
    invalid_ids: list[str]
    model_calls: list[LLMResult]


class RagAnswerError(Exception):
    """Agent 没有有效最终正文；保留实际调用，不能冒充空资料或丢失轨迹。"""

    def __init__(self, completed_model_calls: list[LLMResult]) -> None:
        super().__init__("RAG Agent returned no usable final answer.")
        self.completed_model_calls = completed_model_calls.copy()


def finalize_rag_answer(
    result: AgentResult,
    sources: list[DocumentChunk],
) -> RagAnswer:
    """按调用方交付的片段检查引用，返回展示文本和实际合法引用来源。

    不检索或请求模型，不修改 AgentResult、片段列表或原始模型调用结果。
    空来源不等于拒答：无引用的正常回答保留，未知引用仍需标注。
    缺少有效正文时抛 RagAnswerError，并保留已经发生的调用。
    """
    if not isinstance(result.answer, str) or not result.answer.strip():
        raise RagAnswerError(result.model_calls)

    checked = check_citations(result.answer, sources)
    answer = result.answer

    for citation_id in checked.invalid_ids:
        answer = answer.replace(
            f"[{citation_id}]",
            "[引用未找到]",
        )

    if checked.invalid_ids:
        answer = f"{answer}\n\n{CITATION_WARNING}"

    return RagAnswer(
        answer=answer,
        sources=checked.valid_sources,
        invalid_ids=checked.invalid_ids,
        model_calls=result.model_calls,
    )


async def answer_with_rag(
    message: str,
    persist_directory: Path,
    history: list[dict[str, str]] | None = None,
    *,
    memory_context: str = "",
    top_k: int = 3,
    max_chars: int = 4000,
) -> RagAnswer:
    """检索后整片选择，空资料短路；生成后检查引用并标注未知 ID。

    本函数用于限定依据知识库作答的请求；调用方选择是否进入此路径。
    无资料指检索为空或预算后无入选片段，此时跳过回答模型；已有片段也可能
    不包含答案，由模型如实说明。检索/Agent 异常继续传播，不冒充资料缺失。
    """
    if max_chars < 0:
        raise ValueError("max_chars must be non-negative.")

    hits = await retrieve(
        message,
        persist_directory,
        top_k=top_k,
    )
    context = build_rag_context(hits, max_chars=max_chars)

    if not context.sources:
        return RagAnswer(
            answer=NO_MATERIAL_ANSWER,
            sources=[],
            invalid_ids=[],
            model_calls=[],
        )

    result = await run_agent(
        message=message,
        history=history,
        memory_context=memory_context,
        rag_context=context.content,
    )

    return finalize_rag_answer(result, context.sources)
