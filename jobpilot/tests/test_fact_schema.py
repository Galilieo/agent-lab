"""用真实 PostgreSQL 验证事实库的数据库约束。

这些规则写在数据库里，即使应用代码有缺陷也不会被绕过：
组合外键保证跨表归属一致，触发器保证已发布事实只追加，CHECK 保证来源与出处匹配。
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.db.models import (
    AiRun,
    Fact,
    FactDraft,
    FactSet,
    ResumeDocument,
    User,
)

RAW_TEXT = "项目：课程排班面板\n负责实现按周次筛选课程的功能。"
QUOTE = "负责实现按周次筛选课程的功能。"
SPAN_START = RAW_TEXT.index(QUOTE)

Factory = async_sessionmaker[AsyncSession]


async def add_user(session_factory: Factory, email: str) -> UUID:
    async with session_factory.begin() as session:
        user = User(email=email, hashed_password="test")
        session.add(user)
        await session.flush()
        return user.user_id


async def add_document(session_factory: Factory, user_id: UUID) -> UUID:
    async with session_factory.begin() as session:
        document = ResumeDocument(user_id=user_id, raw_text=RAW_TEXT)
        session.add(document)
        await session.flush()
        return document.doc_id


async def add_fact_set(session_factory: Factory, user_id: UUID, version: int) -> UUID:
    async with session_factory.begin() as session:
        fact_set = FactSet(user_id=user_id, version=version)
        session.add(fact_set)
        await session.flush()
        return fact_set.fact_set_id


def resume_fact(
    user_id: UUID, fact_set_id: UUID, doc_id: UUID, **overrides: Any
) -> Fact:
    """一条合法的、来自简历的事实；测试用 overrides 改出非法组合。"""
    values: dict[str, Any] = {
        "user_id": user_id,
        "fact_set_id": fact_set_id,
        "lineage_id": uuid4(),
        "experience": "课程排班面板",
        "kind": "action",
        "responsibility": "own",
        "text": "实现按周次筛选课程的功能",
        "has_number": False,
        "source": "resume",
        "source_doc_id": doc_id,
        "source_quote": QUOTE,
        "span_start": SPAN_START,
        "span_end": SPAN_START + len(QUOTE),
        "quote_verified": True,
    } | overrides
    return Fact(**values)


async def violated_constraint(session_factory: Factory, row: Any) -> str:
    """插入一行，返回数据库拒绝它时报告的约束名。"""
    with pytest.raises(IntegrityError) as error:
        async with session_factory.begin() as session:
            session.add(row)
    return error.value.orig.diag.constraint_name


# ---------- 组合外键：跨表归属必须是同一用户 ----------


async def test_cross_user_references_are_rejected(session_factory: Factory) -> None:
    """A 的事实、运行、草稿都不能挂到 B 的版本上，A 的事实也不能引用 B 的原文。"""
    user_a = await add_user(session_factory, "a@facts.invalid")
    user_b = await add_user(session_factory, "b@facts.invalid")
    doc_a = await add_document(session_factory, user_a)
    doc_b = await add_document(session_factory, user_b)
    set_a = await add_fact_set(session_factory, user_a, 1)
    set_b = await add_fact_set(session_factory, user_b, 1)

    cases = [
        (resume_fact(user_a, set_b, doc_a), "fk_fact_fact_set_id_fact_set"),
        (resume_fact(user_a, set_a, doc_b), "fk_fact_source_doc_id_resume_document"),
        (
            AiRun(user_id=user_a, kind="tailor", fact_set_id=set_b),
            "fk_ai_run_fact_set_id_fact_set",
        ),
        (
            FactDraft(user_id=user_a, base_fact_set_id=set_b),
            "fk_fact_draft_base_fact_set_id_fact_set",
        ),
    ]
    for row, constraint in cases:
        assert await violated_constraint(session_factory, row) == constraint

    # 同一用户的组合都能写入，证明上面的拒绝来自归属不一致而不是数据本身。
    async with session_factory.begin() as session:
        session.add(resume_fact(user_a, set_a, doc_a))
        session.add(AiRun(user_id=user_a, kind="tailor", fact_set_id=set_a))
        session.add(FactDraft(user_id=user_a, base_fact_set_id=set_a))


# ---------- 只追加：已发布事实不能修改，但账号删除时能级联删除 ----------


async def test_published_fact_rejects_update_but_cascades_on_account_delete(
    session_factory: Factory,
) -> None:
    """引用原文和版本的外键延迟到提交时检查，所以账号删除能一次级联删干净。"""
    user = await add_user(session_factory, "a@facts.invalid")
    doc = await add_document(session_factory, user)
    fact_set = await add_fact_set(session_factory, user, 1)
    async with session_factory.begin() as session:
        session.add(resume_fact(user, fact_set, doc))
        session.add(AiRun(user_id=user, kind="tailor", fact_set_id=fact_set))
        session.add(FactDraft(user_id=user, base_fact_set_id=fact_set))

    with pytest.raises(DBAPIError, match="append-only"):
        async with session_factory.begin() as session:
            await session.execute(update(Fact).values(text="实现了筛选功能"))

    async with session_factory.begin() as session:
        await session.execute(delete(User).where(User.user_id == user))
    async with session_factory() as reader:
        for table in (Fact, FactSet, ResumeDocument, FactDraft, AiRun):
            assert (await reader.scalars(select(table))).all() == []


# ---------- 来源与出处：简历事实必须带已校验的片段和位置 ----------


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"quote_verified": False}, "ck_fact_source"),
        ({"span_start": None, "span_end": None}, "ck_fact_source"),
        ({"source_quote": None}, "ck_fact_source"),
        ({"source": "user"}, "ck_fact_source"),  # 用户补充却带着简历出处
        ({"span_end": SPAN_START}, "ck_fact_span"),  # 空范围
        ({"kind": "skill"}, "ck_fact_kind"),
        ({"responsibility": "owner"}, "ck_fact_responsibility"),
    ],
    ids=[
        "unverified-quote",
        "missing-span",
        "missing-quote",
        "user-with-resume-source",
        "empty-span",
        "unknown-kind",
        "unknown-responsibility",
    ],
)
async def test_fact_source_and_value_checks(
    session_factory: Factory, overrides: dict[str, Any], constraint: str
) -> None:
    user = await add_user(session_factory, "a@facts.invalid")
    doc = await add_document(session_factory, user)
    fact_set = await add_fact_set(session_factory, user, 1)

    row = resume_fact(user, fact_set, doc, **overrides)

    assert await violated_constraint(session_factory, row) == constraint


async def test_user_supplied_fact_needs_no_document(session_factory: Factory) -> None:
    user = await add_user(session_factory, "a@facts.invalid")
    fact_set = await add_fact_set(session_factory, user, 1)

    async with session_factory.begin() as session:
        session.add(
            resume_fact(
                user,
                fact_set,
                None,  # type: ignore[arg-type]
                source="user",
                source_quote=None,
                span_start=None,
                span_end=None,
                quote_verified=False,
            )
        )


# ---------- 版本号与 lineage ----------


async def test_versions_and_lineage_uniqueness(session_factory: Factory) -> None:
    """同一 lineage 可以出现在不同版本，同一版本内不能重复；版本号按用户唯一。"""
    user = await add_user(session_factory, "a@facts.invalid")
    doc = await add_document(session_factory, user)
    v1 = await add_fact_set(session_factory, user, 1)
    v2 = await add_fact_set(session_factory, user, 2)
    lineage = uuid4()

    async with session_factory.begin() as session:
        session.add(resume_fact(user, v1, doc, lineage_id=lineage))
        session.add(resume_fact(user, v2, doc, lineage_id=lineage, text="改后的说法"))

    duplicate = resume_fact(user, v1, doc, lineage_id=lineage)
    assert await violated_constraint(session_factory, duplicate) == "uq_fact_user_id"
    second_v1 = FactSet(user_id=user, version=1)
    assert await violated_constraint(session_factory, second_v1) == (
        "uq_fact_set_user_id"
    )
