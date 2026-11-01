import hashlib
import time

from .config import settings

_papers: dict[str, tuple[float, dict]] = {}


def _purge() -> None:
    now = time.time()
    for key in [k for k, (ts, _) in _papers.items() if now - ts > settings.cache_ttl_seconds]:
        del _papers[key]


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def put(paper_id: str, paper: dict) -> None:
    _purge()
    _papers[paper_id] = (time.time(), paper)


def get(paper_id: str) -> dict | None:
    _purge()
    entry = _papers.get(paper_id)
    return entry[1] if entry else None
