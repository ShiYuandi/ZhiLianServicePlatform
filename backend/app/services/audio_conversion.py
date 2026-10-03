from __future__ import annotations

import asyncio
import os
import tempfile

from app.core.errors import AppError


async def to_pcm(data: bytes, timeout: int = 60) -> bytes:
    """使用 FFmpeg 转成 16kHz/16bit/单声道 PCM；WAV 已是 PCM 时仍交给 FFmpeg 统一处理。"""
    in_name = out_name = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as src:
            src.write(data)
            in_name = src.name
        out_name = in_name + ".pcm"
        proc = await asyncio.create_subprocess_exec("ffmpeg", "-v", "error", "-i", in_name, "-f", "s16le", "-ar", "16000", "-ac", "1", out_name, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            raise AppError("AUDIO_CONVERT_FAILED", "音频转码失败", 422)
        return open(out_name, "rb").read()
    except FileNotFoundError as exc:
        raise AppError("FFMPEG_NOT_INSTALLED", "服务器未安装 FFmpeg，暂时无法处理音频", 503) from exc
    except asyncio.TimeoutError as exc:
        raise AppError("AUDIO_CONVERT_TIMEOUT", "音频转码超时", 422) from exc
    finally:
        for path in (in_name, out_name):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
