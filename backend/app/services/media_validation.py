from __future__ import annotations

import io

from app.core.errors import AppError


IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
AUDIO_TYPES = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/ogg", "audio/webm", "application/ogg"}


def validate_image(data: bytes) -> str:
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            return Image.MIME.get(image.format, "application/octet-stream")
    except Exception as exc:
        raise AppError("IMAGE_INVALID", "上传文件不是有效图片", 422) from exc


def validate_audio(data: bytes, content_type: str | None = None) -> str:
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "audio/wav"
    if data.startswith(b"ID3") or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    if data.startswith(b"OggS"):
        return "audio/ogg"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    if content_type in AUDIO_TYPES:
        return content_type
    raise AppError("AUDIO_INVALID", "上传文件不是支持的音频格式", 422)
