from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import decrypt_model_credential, mask_secret
from app.schemas.model_common import generated_model_code


async def list_models(
    db: AsyncSession,
    model_type: type,
    page: int,
    page_size: int,
    keyword: str | None,
    provider: str | None,
    enabled: bool | None,
) -> tuple[list[Any], int]:
    filters = [model_type.archived_at.is_(None)]
    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        filters.append(
            or_(model_type.model_name.like(term), model_type.model_code.like(term))
        )
    if provider:
        filters.append(model_type.provider == provider)
    if enabled is not None:
        filters.append(model_type.enabled == enabled)
    total = int(await db.scalar(select(func.count(model_type.id)).where(*filters)) or 0)
    stmt = (
        select(model_type)
        .where(*filters)
        .order_by(
            model_type.sort_order.asc(),
            model_type.updated_at.desc(),
            model_type.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list((await db.scalars(stmt)).all()), total


def apply_common(model: Any, payload: Any) -> None:
    model.model_name = payload.model_name
    if payload.model_code:
        model.model_code = payload.model_code
    elif not getattr(model, "model_code", None):
        model.model_code = generated_model_code(payload.model_name, payload.provider)
    model.provider = payload.provider
    model.sort_order = payload.sort_order
    model.doc_url = payload.doc_url
    model.remark = payload.remark
    model.enabled = payload.enabled


async def commit_model(db: AsyncSession, duplicate_message: str) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError("MODEL_CODE_EXISTS", duplicate_message, 409) from exc


def masked_credential(value: str | None, settings: Settings) -> str | None:
    if not value:
        return None
    return mask_secret(decrypt_model_credential(value, settings))


def common_out(model: Any) -> dict[str, Any]:
    return {
        "id": model.id,
        "model_name": model.model_name,
        "model_code": model.model_code,
        "sort_order": model.sort_order,
        "doc_url": model.doc_url,
        "remark": model.remark,
        "enabled": model.enabled,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }
