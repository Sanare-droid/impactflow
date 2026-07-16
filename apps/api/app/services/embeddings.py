"""Portable text embeddings + chunking for RAG (hash fallback; OpenAI optional)."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBED_DIMS = 256


def chunk_text(text: str, *, max_chars: int = 700) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs or [raw]:
        if len(buf) + len(para) + 1 <= max_chars:
            buf = f"{buf}\n{para}".strip() if buf else para
        else:
            if buf:
                chunks.append(buf)
            if len(para) <= max_chars:
                buf = para
            else:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i : i + max_chars])
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def hash_embed(text: str, dims: int = EMBED_DIMS) -> list[float]:
    vec = [0.0] * dims
    tokens = re.findall(r"[a-z0-9]{2,}", (text or "").lower())
    if not tokens:
        return vec
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dims
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        vec[idx] += sign
    return _l2_normalize(vec)


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


async def embed_text(text: str) -> tuple[list[float], str]:
    """Return (vector, model_name). Uses OpenAI when configured, else hash-v1."""
    if settings.openai_api_key:
        try:
            vec = await _openai_embed(text)
            if vec:
                return vec, "openai-text-embedding-3-small"
        except Exception as exc:  # noqa: BLE001
            logger.warning("openai_embed_failed falling back to hash: %s", exc)
    return hash_embed(text), "hash-v1"


async def _openai_embed(text: str) -> Optional[list[float]]:
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": "text-embedding-3-small",
                "input": text[:8000],
                "dimensions": EMBED_DIMS,
            },
        )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        embedding = data["data"][0]["embedding"]
        return _l2_normalize([float(x) for x in embedding])
