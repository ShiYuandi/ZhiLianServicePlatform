from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import get_session_factory
from app.models.ai_task import AITask
from app.services import ai_task_service
from app.services.object_storage import get_object_storage


async def run_cleanup(settings) -> int:
    storage = get_object_storage(settings.app_env, settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, settings.minio_bucket, settings.minio_secure)
    async with get_session_factory()() as db:
        expired = await ai_task_service.expire_results(db, storage)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.ai_task_input_retention_hours)
        stale = list((await db.scalars(select(AITask).where(AITask.input_object_key.is_not(None), AITask.created_at < cutoff, AITask.status.in_(("failed", "succeeded", "expired"))))).all())
        for task in stale:
            try:
                await storage.delete(task.input_object_key)
            except Exception:
                continue
            task.input_object_key = None
        if stale:
            await db.commit()
        return expired + len(stale)
