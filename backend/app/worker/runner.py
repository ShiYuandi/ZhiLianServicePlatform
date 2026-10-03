from __future__ import annotations

import asyncio
import logging
import uuid

from app.core.errors import AppError
from app.db.session import get_session_factory
from app.services import ai_task_service
from app.worker.executors import image, speech
from app.services.object_storage import get_object_storage

log = logging.getLogger(__name__)


async def process_once(settings, worker_id: str | None = None) -> int:
    worker_id = worker_id or f"worker-{uuid.uuid4().hex[:12]}"
    async with get_session_factory()() as db:
        tasks = await ai_task_service.claim_tasks(db, worker_id, settings)
    for task in tasks:
        try:
            async with get_session_factory()() as db:
                if task.task_type == "speech_recognition":
                    await speech.execute(task, db, settings, worker_id)
                else:
                    await image.execute(task, db, settings, worker_id)
        except Exception as exc:
            code = getattr(exc, "code", "TASK_EXECUTION_FAILED")
            retryable = bool(getattr(exc, "retryable", False))
            log.warning("ai task failed task_id=%s code=%s", task.id, code)
            if task.input_object_key and (not retryable or task.attempts >= task.max_attempts):
                try:
                    storage = get_object_storage(settings.app_env, settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, settings.minio_bucket, settings.minio_secure)
                    await storage.delete(task.input_object_key)
                except Exception:
                    log.warning("failed to remove task input task_id=%s", task.id)
            async with get_session_factory()() as db:
                try:
                    await ai_task_service.fail_task(db, task.id, worker_id, code=code, message=str(exc), retryable=retryable, settings=settings)
                except AppError:
                    pass
    return len(tasks)


async def run_forever(settings) -> None:
    worker_id = f"worker-{uuid.uuid4().hex[:12]}"
    while True:
        processed = await process_once(settings, worker_id)
        if not processed:
            await asyncio.sleep(settings.worker_poll_interval_seconds)
