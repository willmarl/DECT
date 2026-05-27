"""Runtime limit for parallel FR / LLM calls (UI slider + .env default)."""

import threading
from contextlib import contextmanager

from config import MAX_PARALLEL_FRS as _ENV_DEFAULT

_lock = threading.Lock()
_limit = _ENV_DEFAULT
_semaphore = threading.Semaphore(_limit)


def get_max_parallel_frs() -> int:
    with _lock:
        return _limit


def set_max_parallel_frs(n: int) -> int:
    """Set cap for concurrent LLM calls. Call before starting a pipeline run."""
    global _semaphore, _limit
    n = max(1, min(99, int(n)))
    with _lock:
        _limit = n
        _semaphore = threading.Semaphore(n)
    return n


@contextmanager
def llm_slot():
    _semaphore.acquire()
    try:
        yield
    finally:
        _semaphore.release()
