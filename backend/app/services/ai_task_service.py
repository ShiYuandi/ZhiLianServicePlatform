from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models.ai_task import AITask


ACTIVE_STATUSES = ("pending", "processing")
TERMINAL_STATUSES = ("succeeded", "failed", "expired")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def count_inflight(db: AsyncSession, service_id: int) -> int:
    return int(await db.scalar(select(func.count(AITask.id)).where(AITask.service_id == service_id, AITask.status.in_(ACTIVE_STATUSES))) or 0)


async def count_recent(db: AsyncSession, service_id: int, task_type: str, since: datetime) -> int:
    return int(await db.scalar(select(func.count(AITask.id)).where(AITask.service_id == service_id, AITask.task_type == task_type, AITask.created_at >= since)) or 0)


async def find_idempotent(db: AsyncSession, service_id: int, task_type: str, key: str | None) -> AITask | None:
    if not key:
        return None
    return await db.scalar(select(AITask).where(AITask.service_id == service_id, AITask.task_type == task_type, AITask.idempotency_key == key))


async def create_task(
    db: AsyncSession,
    *,
    service_id: int,
    task_type: str,
    model_id: int | None,
    model_name: str | None,
    model_code: str | None,
    provider: str | None,
    model_snapshot: dict | None = None,
    input_object_key: str | None = None,
    prompt: str | None = None,
    options: dict | None = None,
    idempotency_key: str | None = None,
    max_attempts: int = 3,
) -> tuple[AITask, bool]:
    task_type = {"speech": "speech_recognition", "image": "image_generation"}.get(task_type, task_type)
    if task_type not in {"speech_recognition", "image_generation"}:
        raise AppError("TASK_TYPE_INVALID", "任务类型不受支持", 422)
    existing = await find_idempotent(db, service_id, task_type, idempotency_key)
    if existing:
        return existing, True
    task = AITask(
        id=str(uuid.uuid4()), service_id=service_id, task_type=task_type,
        status="pending", idempotency_key=idempotency_key,
        model_id=model_id, model_name=model_name, model_code=model_code,
        provider=provider, model_snapshot=model_snapshot,
        input_object_key=input_object_key, prompt=prompt, options=options,
        max_attempts=max_attempts,
    )
    db.add(task)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await find_idempotent(db, service_id, task_type, idempotency_key)
        if existing:
            return existing, True
        raise AppError("TASK_CREATE_FAILED", "任务创建失败，请稍后重试", 409)
    await db.refresh(task)
    return task, False


async def get_task(db: AsyncSession, task_id: str, service_id: int | None = None) -> AITask:
    conditions = [AITask.id == task_id]
    if service_id is not None:
        conditions.append(AITask.service_id == service_id)
    task = await db.scalar(select(AITask).where(*conditions))
    if not task:
        raise AppError("AI_TASK_NOT_FOUND", "任务不存在", 404)
    return task


async def claim_tasks(db: AsyncSession, worker_id: str, settings: Settings, limit: int | None = None) -> list[AITask]:
    now = utcnow()
    limit = limit or settings.worker_batch_size
    # MySQL supports SKIP LOCKED; SQLite tests simply serialize this transaction.
    stmt = (select(AITask).where(or_(AITask.status == "pending", and_(AITask.status == "processing", AITask.lease_expires_at < now))).order_by(AITask.created_at).limit(limit).with_for_update(skip_locked=True))
    tasks = list((await db.scalars(stmt)).all())
    for task in tasks:
        task.status = "processing"
        task.worker_id = worker_id
        task.lease_expires_at = now + timedelta(seconds=settings.worker_lease_seconds)
        task.started_at = task.started_at or now
        task.attempts += 1
    if tasks:
        await db.commit()
    return tasks


async def renew_lease(db: AsyncSession, task_id: str, worker_id: str, settings: Settings) -> AITask:
    task = await get_task(db, task_id)
    if task.status != "processing" or task.worker_id != worker_id:
        raise AppError("TASK_LEASE_INVALID", "任务租约已失效", 409)
    task.lease_expires_at = utcnow() + timedelta(seconds=settings.worker_lease_seconds)
    await db.commit()
    return task


async def succeed_task(db: AsyncSession, task_id: str, worker_id: str, *, text: str | None = None, result_object_key: str | None = None, result_expires_at: datetime | None = None) -> AITask:
    task = await get_task(db, task_id)
    if task.status != "processing" or task.worker_id != worker_id:
        raise AppError("TASK_LEASE_INVALID", "任务租约已失效", 409)
    task.status = "succeeded"
    task.result_text = text
    task.result_object_key = result_object_key
    task.result_expires_at = result_expires_at
    task.input_object_key = None
    task.completed_at = utcnow()
    task.lease_expires_at = None
    await db.commit()
    return task


async def fail_task(db: AsyncSession, task_id: str, worker_id: str, *, code: str, message: str, retryable: bool = False, settings: Settings | None = None) -> AITask:
    task = await get_task(db, task_id)
    if task.status != "processing" or task.worker_id != worker_id:
        raise AppError("TASK_LEASE_INVALID", "任务租约已失效", 409)
    if retryable and task.attempts < task.max_attempts:
        task.status = "pending"
        task.worker_id = None
        task.lease_expires_at = None
    else:
        task.status = "failed"
        task.completed_at = utcnow()
        task.lease_expires_at = None
        task.input_object_key = None
    task.error_code, task.error_message = code[:64], message[:1000]
    await db.commit()
    return task


async def recover_expired_leases(db: AsyncSession) -> int:
    result = await db.execute(update(AITask).where(AITask.status == "processing", AITask.lease_expires_at < utcnow()).values(status="pending", worker_id=None, lease_expires_at=None))
    await db.commit()
    return int(result.rowcount or 0)


async def expire_results(db: AsyncSession, storage, now: datetime | None = None) -> int:
    now = now or utcnow()
    tasks = list((await db.scalars(select(AITask).where(AITask.status == "succeeded", AITask.result_expires_at.is_not(None), AITask.result_expires_at < now))).all())
    for task in tasks:
        if task.result_object_key:
            try:
                await storage.delete(task.result_object_key)
            except Exception:
                continue
        task.status = "expired"
        task.result_object_key = None
    if tasks:
        await db.commit()
    return len(tasks)
