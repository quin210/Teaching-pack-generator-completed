import os
import re


def safe_key(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[^a-zA-Z0-9._/-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s


def r2_public_url(key: str) -> str:
    base = os.getenv("R2_PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        raise RuntimeError("Missing R2_PUBLIC_BASE_URL env var")
    key = key.lstrip("/")
    return f"{base}/{key}"
