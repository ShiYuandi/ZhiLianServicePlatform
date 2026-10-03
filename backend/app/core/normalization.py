import hashlib
import re
import unicodedata

# 语音识别会把同一句话识别成全角数字（１１５）、带标点（你好。）、带空格等不同写法，
# 屏幕上看起来一样但字节不同。匹配键因此统一：NFKC 折叠全角、忽略大小写、丢弃全部空白和标点。
_NON_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)


def normalize_device_name(name: str) -> str:
    """设备名称匹配键：忽略前后空格和大小写。"""
    return name.strip().casefold()


def normalize_question(question: str) -> str:
    text = unicodedata.normalize("NFKC", question).casefold()
    return _NON_WORD_RE.sub("", text)


def question_fingerprint(question: str) -> str:
    return hashlib.sha256(normalize_question(question).encode("utf-8")).hexdigest()


def validate_table_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("表名不能为空")
    if ".." in cleaned or any(char in cleaned for char in ("/", "\\", "\x00")):
        raise ValueError("表名包含不允许的字符")
    if any(ord(char) < 32 for char in cleaned):
        raise ValueError("表名包含控制字符")
    return cleaned
