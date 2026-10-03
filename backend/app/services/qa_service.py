from __future__ import annotations

import logging
from collections import Counter
from difflib import SequenceMatcher

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.normalization import (
    normalize_question,
    question_fingerprint,
    validate_table_name,
)
from app.models.qa import QaItem, QaTable
from app.schemas.qa import QaItemCreate, QaTableCreate


logger = logging.getLogger(__name__)

# 模糊匹配相似度阈值：归一化问题相似度达到该值才允许命中。
# 0.8 会把"你们几点关门"错配到"你们几点开门"（0.833），因此取 0.9。
QA_FUZZY_MATCH_THRESHOLD = 0.9

# 否定字出现在两问差异字符中时拒绝命中，避免"有/没有"这类一字反转语义的错配。
QA_FUZZY_NEGATION_CHARS = frozenset("不没无非别勿未莫")


def _negation_differs(question: str, candidate: str) -> bool:
    diff = (Counter(question) - Counter(candidate)) + (
        Counter(candidate) - Counter(question)
    )
    return bool(QA_FUZZY_NEGATION_CHARS & set(diff))


def strip_wake_prefix(wake_texts: list[str], question: str) -> str | None:
    """剥离语音问题开头的唤醒词（如“小智，你们几点开门”→“你们几点开门”）。

    返回剥离后的归一化问题；未配置唤醒词或问题不含唤醒词前缀时返回 None。
    """

    normalized = normalize_question(question)
    for wake in sorted(wake_texts or [], key=len, reverse=True):
        prefix = normalize_question(wake)
        if prefix and normalized.startswith(prefix) and len(normalized) > len(prefix):
            return normalized[len(prefix) :]
    return None


async def get_table_or_404(db: AsyncSession, table_id: int) -> QaTable:
    table = await db.scalar(
        select(QaTable)
        .options(selectinload(QaTable.xiaozhi_services))
        .where(QaTable.id == table_id)
    )
    if not table:
        raise AppError("QA_TABLE_NOT_FOUND", "问答表不存在", 404)
    return table


async def get_table_by_name(db: AsyncSession, name: str) -> QaTable:
    table = await db.scalar(select(QaTable).where(QaTable.name == name.strip()))
    if not table:
        raise AppError("QA_TABLE_NOT_FOUND", "问答表不存在", 404)
    return table


async def list_tables(
    db: AsyncSession, page: int, page_size: int, keyword: str | None
) -> tuple[list[dict], int]:
    filters = []
    if keyword:
        filters.append(QaTable.name.contains(keyword.strip()))
    count_stmt = select(func.count(QaTable.id)).where(*filters)
    total = int(await db.scalar(count_stmt) or 0)
    item_count = func.count(QaItem.id).label("item_count")
    stmt = (
        select(QaTable, item_count)
        .outerjoin(QaItem, QaItem.table_id == QaTable.id)
        .where(*filters)
        .group_by(QaTable.id)
        .order_by(QaTable.updated_at.desc(), QaTable.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": table.id,
            "name": table.name,
            "description": table.description,
            "item_count": count,
            "created_at": table.created_at,
            "updated_at": table.updated_at,
        }
        for table, count in rows
    ], total


async def create_table(db: AsyncSession, payload: QaTableCreate) -> QaTable:
    try:
        name = validate_table_name(payload.name)
    except ValueError as exc:
        raise AppError("INVALID_TABLE_NAME", str(exc), 422) from exc
    table = QaTable(name=name, description=(payload.description or "").strip() or None)
    db.add(table)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError("QA_TABLE_EXISTS", "同名问答表已存在", 409) from exc
    await db.refresh(table)
    return table


async def update_table(
    db: AsyncSession, table_id: int, payload: QaTableCreate
) -> QaTable:
    table = await get_table_or_404(db, table_id)
    try:
        table.name = validate_table_name(payload.name)
    except ValueError as exc:
        raise AppError("INVALID_TABLE_NAME", str(exc), 422) from exc
    table.description = (payload.description or "").strip() or None
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError("QA_TABLE_EXISTS", "同名问答表已存在", 409) from exc
    await db.refresh(table)
    return table


async def delete_table(db: AsyncSession, table_id: int) -> None:
    table = await get_table_or_404(db, table_id)
    if table.xiaozhi_services:
        raise AppError("QA_TABLE_IN_USE", "问答表已被小智中间件服务使用，不能删除", 409)
    await db.delete(table)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError(
            "QA_TABLE_IN_USE", "问答表已被小智中间件服务使用，不能删除", 409
        ) from exc


async def find_fixed_answer(
    db: AsyncSession,
    table_id: int,
    question: str,
    *,
    request_id: str = "-",
    attempt: str = "original",
    log_details: bool = True,
) -> str | None:
    normalized = normalize_question(question)
    fingerprint = question_fingerprint(question)
    if log_details:
        logger.info(
            "event=qa_lookup_start request_id=%s table_id=%s attempt=%s "
            "raw_question=%r normalized=%r threshold=%.4f",
            request_id,
            table_id,
            attempt,
            question,
            normalized,
            QA_FUZZY_MATCH_THRESHOLD,
        )
    item = await db.scalar(
        select(QaItem).where(
            QaItem.table_id == table_id,
            QaItem.question_fingerprint == fingerprint,
        )
    )
    if item and item.normalized_question == normalized:
        if log_details:
            logger.info(
                "event=qa_match_success request_id=%s table_id=%s attempt=%s "
                "match_type=exact item_id=%s candidate_question=%r score=1.0000",
                request_id,
                table_id,
                attempt,
                item.id,
                item.question,
            )
        return item.answer
    if log_details:
        logger.info(
            "event=qa_exact_miss request_id=%s table_id=%s attempt=%s "
            "fingerprint_candidate_id=%s",
            request_id,
            table_id,
            attempt,
            item.id if item else None,
        )
    return await find_fuzzy_answer(
        db,
        table_id,
        normalized,
        request_id=request_id,
        attempt=attempt,
        log_details=log_details,
    )


async def find_fuzzy_answer(
    db: AsyncSession,
    table_id: int,
    normalized: str,
    *,
    request_id: str = "-",
    attempt: str = "original",
    log_details: bool = True,
) -> str | None:
    """在未精确命中的情况下按相似度模糊匹配，取达到阈值的最高分答案。

    命中需同时满足：相似度不低于阈值，且差异字符不含否定字
    （防止"你们几点关门"错配到"你们几点开门"这类一字反转语义的情况）。
    """

    if not normalized:
        if log_details:
            logger.info(
                "event=qa_match_failed request_id=%s table_id=%s attempt=%s "
                "reason=empty_question",
                request_id,
                table_id,
                attempt,
            )
        return None
    rows = await db.execute(
        select(QaItem.id, QaItem.question, QaItem.normalized_question, QaItem.answer)
        .where(QaItem.table_id == table_id)
        .order_by(QaItem.sort_order.asc(), QaItem.id.asc())
    )
    candidates = rows.all()
    best_score = 0.0
    best_answer: str | None = None
    best_item_id: int | None = None
    best_question: str | None = None
    highest_score = 0.0
    highest_item_id: int | None = None
    blocked_by_negation = False
    for item_id, candidate_question, candidate, answer in candidates:
        score = SequenceMatcher(None, normalized, candidate).ratio()
        negation_differs = _negation_differs(normalized, candidate)
        threshold_passed = score >= QA_FUZZY_MATCH_THRESHOLD
        eligible = threshold_passed and not negation_differs
        if score > highest_score:
            highest_score = score
            highest_item_id = item_id
        if threshold_passed and negation_differs:
            blocked_by_negation = True
        if log_details:
            logger.info(
                "event=qa_candidate request_id=%s table_id=%s attempt=%s item_id=%s "
                "candidate_question=%r candidate_normalized=%r score=%.4f "
                "threshold_passed=%s negation_differs=%s eligible=%s",
                request_id,
                table_id,
                attempt,
                item_id,
                candidate_question,
                candidate,
                score,
                threshold_passed,
                negation_differs,
                eligible,
            )
        if eligible and score > best_score:
            best_score = score
            best_answer = answer
            best_item_id = item_id
            best_question = candidate_question
    if log_details:
        if best_answer is not None:
            logger.info(
                "event=qa_match_success request_id=%s table_id=%s attempt=%s "
                "match_type=fuzzy item_id=%s candidate_question=%r score=%.4f "
                "candidate_count=%s",
                request_id,
                table_id,
                attempt,
                best_item_id,
                best_question,
                best_score,
                len(candidates),
            )
        else:
            reason = (
                "table_empty"
                if not candidates
                else "negation_guard"
                if blocked_by_negation
                else "below_threshold"
            )
            logger.info(
                "event=qa_match_failed request_id=%s table_id=%s attempt=%s "
                "reason=%s candidate_count=%s highest_item_id=%s highest_score=%.4f",
                request_id,
                table_id,
                attempt,
                reason,
                len(candidates),
                highest_item_id,
                highest_score,
            )
    return best_answer


async def list_items(
    db: AsyncSession, table_id: int, page: int, page_size: int, keyword: str | None
) -> tuple[list[QaItem], int]:
    await get_table_or_404(db, table_id)
    filters = [QaItem.table_id == table_id]
    if keyword:
        term = f"%{keyword.strip()}%"
        filters.append(or_(QaItem.question.like(term), QaItem.answer.like(term)))
    total = int(await db.scalar(select(func.count(QaItem.id)).where(*filters)) or 0)
    stmt = (
        select(QaItem)
        .where(*filters)
        .order_by(QaItem.sort_order.asc(), QaItem.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list((await db.scalars(stmt)).all()), total


def build_item(table_id: int, payload: QaItemCreate) -> QaItem:
    normalized = normalize_question(payload.question)
    return QaItem(
        table_id=table_id,
        question=payload.question.strip(),
        answer=payload.answer.strip(),
        normalized_question=normalized,
        question_fingerprint=question_fingerprint(payload.question),
        sort_order=payload.sort_order,
    )


async def _commit_item(db: AsyncSession, item: QaItem) -> QaItem:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError("DUPLICATE_QUESTION", "同一问答表中已存在等价问题", 409) from exc
    await db.refresh(item)
    return item


async def create_item(db: AsyncSession, table_id: int, payload: QaItemCreate) -> QaItem:
    await get_table_or_404(db, table_id)
    item = build_item(table_id, payload)
    db.add(item)
    return await _commit_item(db, item)


async def update_item(db: AsyncSession, item_id: int, payload: QaItemCreate) -> QaItem:
    item = await db.get(QaItem, item_id)
    if not item:
        raise AppError("QA_ITEM_NOT_FOUND", "问答项不存在", 404)
    item.question = payload.question.strip()
    item.answer = payload.answer.strip()
    item.normalized_question = normalize_question(payload.question)
    item.question_fingerprint = question_fingerprint(payload.question)
    item.sort_order = payload.sort_order
    return await _commit_item(db, item)


async def delete_item(db: AsyncSession, item_id: int) -> None:
    item = await db.get(QaItem, item_id)
    if not item:
        raise AppError("QA_ITEM_NOT_FOUND", "问答项不存在", 404)
    await db.delete(item)
    await db.commit()


def validate_batch_duplicates(items: list[QaItemCreate]) -> None:
    seen: dict[str, int] = {}
    for row, payload in enumerate(items, start=1):
        fingerprint = question_fingerprint(payload.question)
        if fingerprint in seen:
            raise AppError(
                "DUPLICATE_QUESTION",
                f"第 {row} 行与第 {seen[fingerprint]} 行问题重复",
                422,
            )
        seen[fingerprint] = row


async def batch_create_items(
    db: AsyncSession, table_id: int, items: list[QaItemCreate]
) -> list[QaItem]:
    await get_table_or_404(db, table_id)
    validate_batch_duplicates(items)
    records = [build_item(table_id, payload) for payload in items]
    db.add_all(records)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError("DUPLICATE_QUESTION", "导入内容与已有问题重复", 409) from exc
    for item in records:
        await db.refresh(item)
    return records


async def replace_items(
    db: AsyncSession, table_id: int, items: list[QaItemCreate]
) -> int:
    await get_table_or_404(db, table_id)
    validate_batch_duplicates(items)
    try:
        await db.execute(delete(QaItem).where(QaItem.table_id == table_id))
        db.add_all([build_item(table_id, payload) for payload in items])
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError("DUPLICATE_QUESTION", "替换内容中存在重复问题", 409) from exc
    return len(items)


async def all_items(db: AsyncSession, table_id: int) -> list[QaItem]:
    await get_table_or_404(db, table_id)
    stmt = (
        select(QaItem)
        .where(QaItem.table_id == table_id)
        .order_by(QaItem.sort_order.asc(), QaItem.id.asc())
    )
    return list((await db.scalars(stmt)).all())
