"""严格知识库问答的框架编排，复用原生预算与引用协议。

检索后仅将预算内片段交给模型，无可用片段时跳过回答模型。
保留原始 AIMessage 供调用方观察；不接入 HTTP、数据库或原生调用记录契约。
"""

from dataclasses import dataclass
from pathlib import Path

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_deepseek import ChatDeepSeek

from app.config import settings
from app.services.agent import AGENT_SYSTEM_PROMPT
from app.services.langchain_retrieval import build_notes_retriever
from app.services.rag import DocumentChunk, RetrievedChunk
from app.services.rag_answer import CITATION_WARNING, NO_MATERIAL_ANSWER
from app.services.rag_citations import check_citations
from app.services.rag_context import RagContext, build_rag_context


RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "{rag_context}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{message}"),
])


@dataclass(frozen=True)
class LangChainRagAnswer:
    """展示文本与实际合法引用来源，原始响应保留正文、工具字段和元数据。

    response=None 表示没有调用回答模型；sources 只包含实际合法引用的片段，
    不含所有检索命中。引用ID合法不代表原文一定支持回答结论。
    """

    answer: str
    sources: list[DocumentChunk]
    invalid_ids: list[str]
    response: AIMessage | None


class LangChainRagAnswerError(Exception):
    """缺少有效最终文本时，保留实际模型响应，不冒充未调用或资料为空。"""

    def __init__(self, response: AIMessage) -> None:
        super().__init__("LangChain RAG returned no usable final answer.")
        self.response = response


def documents_to_context(
    documents: list[Document], *, max_chars: int = 4000
) -> RagContext:
    """将本项目检索适配器的 Document 转回原生片段，复用已有整片预算。

    输入须保留 source/chunk_index/start/end/distance 元数据；
    不接受任意外部 Document，也不在这里重新检索或修补缺失出处。
    """
    hits = [
        RetrievedChunk(
            chunk=DocumentChunk(
                source=document.metadata["source"],
                chunk_index=document.metadata["chunk_index"],
                start=document.metadata["start"],
                end=document.metadata["end"],
                text=document.page_content,
            ),
            distance=document.metadata["distance"],
        )
        for document in documents
    ]
    return build_rag_context(hits, max_chars=max_chars)


async def answer_with_langchain_rag(
    message: str,
    persist_directory: Path,
    history: list[dict[str, str]] | None = None,
    *,
    top_k: int = 3,
    max_chars: int = 4000,
    callbacks: list[AsyncCallbackHandler] | None = None,
) -> LangChainRagAnswer:
    """严格问答：检索、预算、模板与模型、最后按实际交付片段检查引用。

    空检索或预算无片段时不调用回答模型；检索、SDK和回调配置沿既有组件。
    空白正文抛 LangChainRagAnswerError 并保留原响应，其他故障继续传播。
    """
    if max_chars < 0:
        raise ValueError("max_chars must be non-negative.")

    retriver = build_notes_retriever(
        persist_directory,
        top_k=top_k,
    )
    documents = await retriver.ainvoke(message)
    context = documents_to_context(documents, max_chars=max_chars)

    if not context.sources:
        return LangChainRagAnswer(
            answer=NO_MATERIAL_ANSWER,
            sources=[],
            invalid_ids=[],
            response=None,
        )

    model = ChatDeepSeek(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        api_base=settings.openai_base_url,
        timeout=60.0,
        max_retries=0,
    )
    chain = RAG_PROMPT | model

    response = await chain.ainvoke(
        {
            "system_prompt": AGENT_SYSTEM_PROMPT,
            "rag_context": context.content,
            "history": history or [],
            "message": message,
        },
        config={"callbacks": callbacks or []}
    )

    if (
        not isinstance(response.content, str)
        or not response.content.strip()
    ):
        raise LangChainRagAnswerError(response)

    checked = check_citations(response.content, context.sources)
    answer = response.content

    for citation_id in checked.invalid_ids:
        answer = answer.replace(
            f"[{citation_id}]",
            "[引用未找到]",
        )

    if checked.invalid_ids:
        answer = f"{answer}\n\n{CITATION_WARNING}"

    return LangChainRagAnswer(
        answer=answer,
        sources=checked.valid_sources,
        invalid_ids=checked.invalid_ids,
        response=response,
    )
