"""检查回答中的 RAG 引用映射；展示、修正和拒答由调用层决定。"""

from dataclasses import dataclass
import re

from app.services.rag import DocumentChunk


@dataclass(frozen=True)
class CitationCheck:
    """仅报告来源映射，不证明片段支持回答结论。"""

    valid_sources: list[DocumentChunk]
    invalid_ids: list[str]


def check_citations(
    answer: str,
    sources: list[DocumentChunk],
) -> CitationCheck:
    """检查约定的 [source::chunk_index] 标记，按首次出现顺序去重。

    sources 应来自本轮已交给模型的预算内片段；多次工具检索时由调用方汇总。
    识别方括号内含 :: 的项目引用标记，不做完整 Markdown 解析或语义核验。
    合法来源和无效 ID 各自去重，不修改正文中重复角标或输入的来源列表。
    不含 :: 的普通方括号不匹配，没有引用时返回两个空列表。
    """
    # 以本轮片段建白名单；不按模型给出的路径重新读取磁盘或整个索引。
    by_id = {
        f"{chunk.source}::{chunk.chunk_index}": chunk for chunk in sources
    }

    valid_sources = []
    invalid_ids = []
    seen = set()

    citation_ids = re.findall(
        r"\[([^\[\]\r\n]*::[^\[\]\r\n]*)\]",
        answer,
    )

    for citation_id in citation_ids:
        if citation_id in seen:
            continue

        seen.add(citation_id)
        chunk = by_id.get(citation_id)

        if chunk is None:
            invalid_ids.append(citation_id)
        else:
            valid_sources.append(chunk)

    return CitationCheck(
        valid_sources=valid_sources,
        invalid_ids=invalid_ids,
    )
