from __future__ import annotations

import asyncio
import io
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol


class ObjectStorageError(RuntimeError):
    """对象存储不可用或对象操作失败。"""


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    etag: str


class ObjectStorage(Protocol):
    async def put(
        self, object_key: str, data: bytes, content_type: str
    ) -> StoredObject: ...

    async def get(self, object_key: str) -> tuple[bytes, str, str]: ...

    async def delete(self, object_key: str) -> None: ...


def create_object_key(service_id: int, slot: str, extension: str) -> str:
    safe_extension = extension.lower().lstrip(".")
    return f"xiaozhi-services/{service_id}/{slot}/{uuid.uuid4().hex}.{safe_extension}"


class MemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str, str]] = {}

    async def put(
        self, object_key: str, data: bytes, content_type: str
    ) -> StoredObject:
        etag = uuid.uuid5(uuid.NAMESPACE_OID, data.hex()).hex
        self.objects[object_key] = (data, content_type, etag)
        return StoredObject(object_key=object_key, etag=etag)

    async def get(self, object_key: str) -> tuple[bytes, str, str]:
        try:
            return self.objects[object_key]
        except KeyError as exc:
            raise ObjectStorageError("对象不存在") from exc

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


class MinioObjectStorage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool,
    ) -> None:
        try:
            from minio import Minio
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise ObjectStorageError("MinIO 客户端依赖未安装") from exc

        endpoint = endpoint.strip()
        endpoint = endpoint.removeprefix("http://").removeprefix("https://")
        self.bucket = bucket
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def _ensure_bucket(self) -> None:
        """首次写入时创建环境专用 Bucket，重复调用安全可重入。"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    async def put(
        self, object_key: str, data: bytes, content_type: str
    ) -> StoredObject:
        def sync_put() -> StoredObject:
            try:
                self._ensure_bucket()
                result = self.client.put_object(
                    self.bucket,
                    object_key,
                    io.BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
                return StoredObject(object_key=object_key, etag=result.etag.strip('"'))
            except Exception as exc:  # pragma: no cover - external service
                raise ObjectStorageError("MinIO 写入失败") from exc

        return await asyncio.to_thread(sync_put)

    async def get(self, object_key: str) -> tuple[bytes, str, str]:
        def sync_get() -> tuple[bytes, str, str]:
            response = None
            try:
                response = self.client.get_object(self.bucket, object_key)
                data = response.read()
                content_type = response.headers.get(
                    "Content-Type", "application/octet-stream"
                )
                etag = response.headers.get("ETag", "").strip('"')
                return data, content_type, etag
            except Exception as exc:  # pragma: no cover - external service
                raise ObjectStorageError("MinIO 读取失败") from exc
            finally:
                if response is not None:
                    response.close()
                    response.release_conn()

        return await asyncio.to_thread(sync_get)

    async def delete(self, object_key: str) -> None:
        def sync_delete() -> None:
            try:
                self.client.remove_object(self.bucket, object_key)
            except Exception as exc:  # pragma: no cover - external service
                raise ObjectStorageError("MinIO 删除失败") from exc

        await asyncio.to_thread(sync_delete)


@lru_cache(maxsize=8)
def get_object_storage(
    app_env: str,
    endpoint: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    secure: bool,
) -> ObjectStorage:
    if app_env == "test":
        return MemoryObjectStorage()
    return MinioObjectStorage(endpoint, access_key, secret_key, bucket, secure)
