import os
import random
import threading
import time


SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", "25"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
MAX_CHUNKS_PER_SESSION = int(os.getenv("MAX_CHUNKS_PER_SESSION", "30"))


_sessions: dict[str, dict] = {}
_session_lock = threading.Lock()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    cleaned = " ".join(text.split())
    chunks = []
    start = 0

    while start < len(cleaned):
        end = start + chunk_size
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap

    return chunks[:MAX_CHUNKS_PER_SESSION]


def _now() -> float:
    return time.time()


def _cleanup_locked() -> None:
    current = _now()
    expired = [
        session_id
        for session_id, session in _sessions.items()
        if current - session["updated_at"] > SESSION_TTL_SECONDS
    ]

    for session_id in expired:
        _sessions.pop(session_id, None)

    while len(_sessions) > MAX_ACTIVE_SESSIONS:
        oldest_session_id = min(_sessions, key=lambda session_id: _sessions[session_id]["updated_at"])
        _sessions.pop(oldest_session_id, None)


def store_session_chunks(session_id: str, text: str) -> int:
    chunks = chunk_text(text)
    if not chunks:
        return 0

    with _session_lock:
        _cleanup_locked()
        _sessions[session_id] = {
            "chunks": chunks,
            "used_indexes": set(),
            "updated_at": _now(),
        }

    return len(chunks)


def get_relevant_chunks(session_id: str, n_results: int = 3) -> list[str]:
    with _session_lock:
        _cleanup_locked()
        session = _sessions.get(session_id)
        if not session:
            return []

        chunks = session["chunks"]
        used_indexes = session["used_indexes"]
        available_indexes = [index for index in range(len(chunks)) if index not in used_indexes]

        if len(available_indexes) < n_results:
            used_indexes.clear()
            available_indexes = list(range(len(chunks)))

        sample_size = min(n_results, len(available_indexes))
        selected_indexes = random.sample(available_indexes, k=sample_size)
        used_indexes.update(selected_indexes)
        session["updated_at"] = _now()

        return [chunks[index] for index in selected_indexes]
