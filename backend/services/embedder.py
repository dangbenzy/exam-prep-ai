import os
import re
import threading
import time
from typing import Any


SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", "25"))
CHUNK_TARGET_MIN = int(os.getenv("CHUNK_TARGET_MIN", "300"))
CHUNK_TARGET_MAX = int(os.getenv("CHUNK_TARGET_MAX", "500"))
CHUNK_SPLIT_OVERLAP = int(os.getenv("CHUNK_SPLIT_OVERLAP", "60"))


DEFAULT_PREFERENCES = {
    "scope": "all",
    "page_ranges": [],
    "chapters": [],
}

FRONT_MATTER_TITLES = {
    "table of contents",
    "contents",
    "preface",
    "foreword",
    "acknowledgements",
    "acknowledgment",
    "dedication",
    "copyright",
    "about the author",
    "introduction",
}


_sessions: dict[str, dict[str, Any]] = {}
_session_lock = threading.Lock()


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _normalize_range(page_range: tuple[int, int]) -> dict[str, int]:
    start, end = page_range
    return {
        "start": min(start, end),
        "end": max(start, end),
    }


def _sentence_split(text: str) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _paragraph_split(text: str) -> list[str]:
    paragraphs = []
    current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_lines:
                paragraphs.append(" ".join(current_lines).strip())
                current_lines = []
            continue

        current_lines.append(line)

    if current_lines:
        paragraphs.append(" ".join(current_lines).strip())

    return [paragraph for paragraph in paragraphs if paragraph]


def _is_heading(line: str) -> bool:
    candidate = line.strip()
    if not candidate:
        return False
    if len(candidate) > 90:
        return False
    if candidate.endswith((".", "?", "!", ";")):
        return False

    words = candidate.split()
    if len(words) > 12:
        return False

    if re.match(r"^(chapter|module|section|part|unit|lesson)\b", candidate, re.IGNORECASE):
        return True
    if re.match(r"^\d+(\.\d+)*\s+[A-Za-z]", candidate):
        return True
    if candidate.isupper() and len(words) <= 8:
        return True

    titled_words = sum(1 for word in words if word[:1].isupper())
    return len(words) > 0 and titled_words >= max(1, len(words) - 1)


def _split_long_text(text: str, max_size: int = CHUNK_TARGET_MAX) -> list[str]:
    sentences = _sentence_split(text)
    if not sentences:
        cleaned = _clean_text(text)
        return [cleaned] if cleaned else []

    chunks = []
    current = ""

    for sentence in sentences:
        proposal = sentence if not current else f"{current} {sentence}"
        if len(proposal) <= max_size:
            current = proposal
            continue

        if current:
            chunks.append(current.strip())
            overlap = current[-CHUNK_SPLIT_OVERLAP:].strip()
            current = f"{overlap} {sentence}".strip() if overlap else sentence
        else:
            start = 0
            while start < len(sentence):
                end = start + max_size
                piece = sentence[start:end].strip()
                if piece:
                    chunks.append(piece)
                if end >= len(sentence):
                    current = ""
                    break
                start = max(0, end - CHUNK_SPLIT_OVERLAP)

    if current:
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def _estimate_chunk_capacity(text: str) -> int:
    sentence_count = len(_sentence_split(text))
    text_length = len(text)

    if text_length >= 700 or sentence_count >= 8:
        return 3
    if text_length >= 420 or sentence_count >= 4:
        return 2
    return 1


def _page_matches_preferences(page_data: dict[str, Any], preferences: dict[str, Any]) -> bool:
    scope = preferences["scope"]

    if scope == "all":
        return True

    if scope == "pages":
        page_number = page_data["page"]
        for page_range in preferences["page_ranges"]:
            if page_range["start"] <= page_number <= page_range["end"]:
                return True
        return False

    if scope == "chapters":
        chapter = page_data.get("chapter")
        return bool(chapter and chapter in preferences["chapters"])

    return False


def _is_front_matter_page(page_data: dict[str, Any]) -> bool:
    lines = [line.strip() for line in page_data.get("text", "").splitlines() if line.strip()]
    if not lines:
        return True

    first_lines = [line.lower() for line in lines[:6]]
    joined_first_lines = " ".join(first_lines)

    if any(title in joined_first_lines for title in FRONT_MATTER_TITLES):
        return True

    dot_leader_lines = sum(1 for line in lines[:20] if re.search(r"\.{3,}\s*\d+$", line))
    page_number_lines = sum(1 for line in lines[:20] if re.fullmatch(r"\d+", line))

    if dot_leader_lines >= 2:
        return True

    cleaned_text = _clean_text(page_data.get("text", ""))
    if len(cleaned_text) < 120 and page_number_lines >= 1:
        return True

    return False


def _trim_leading_front_matter(pages_with_metadata: list[dict[str, Any]]) -> list[dict[str, Any]]:
    first_examinable_index = 0

    for index, page_data in enumerate(pages_with_metadata):
        chapter = page_data.get("chapter")
        if chapter or not _is_front_matter_page(page_data):
            first_examinable_index = index
            break
    else:
        return pages_with_metadata

    return pages_with_metadata[first_examinable_index:]


def _extract_structured_units(page_data: dict[str, Any]) -> list[dict[str, Any]]:
    units = []
    current_heading = page_data.get("chapter")
    buffer = []

    for raw_line in page_data.get("text", "").splitlines():
        line = raw_line.strip()
        if not line:
            if buffer:
                units.append(
                    {
                        "heading": current_heading,
                        "text": " ".join(buffer).strip(),
                    }
                )
                buffer = []
            continue

        if _is_heading(line):
            if buffer:
                units.append(
                    {
                        "heading": current_heading,
                        "text": " ".join(buffer).strip(),
                    }
                )
                buffer = []
            current_heading = line
            continue

        buffer.append(line)

    if buffer:
        units.append(
            {
                "heading": current_heading,
                "text": " ".join(buffer).strip(),
            }
        )

    if units:
        return units

    return [
        {
            "heading": current_heading,
            "text": paragraph,
        }
        for paragraph in _paragraph_split(page_data.get("text", ""))
    ]


def _build_chunks_for_preferences(
    pages_with_metadata: list[dict[str, Any]],
    preferences: dict[str, Any],
) -> list[dict[str, Any]]:
    chunks = []
    source_order = 0
    candidate_pages = pages_with_metadata

    if preferences["scope"] == "all":
        candidate_pages = _trim_leading_front_matter(candidate_pages)

    for page_data in candidate_pages:
        if not _page_matches_preferences(page_data, preferences):
            continue

        for unit in _extract_structured_units(page_data):
            unit_text = _clean_text(unit["text"])
            if len(unit_text) < 80:
                continue

            pieces = [unit_text]
            if len(unit_text) > CHUNK_TARGET_MAX:
                pieces = _split_long_text(unit_text, CHUNK_TARGET_MAX)

            for piece in pieces:
                cleaned_piece = _clean_text(piece)
                if len(cleaned_piece) < 80:
                    continue

                source_order += 1
                page_number = page_data["page"]
                chunks.append(
                    {
                        "id": f"page-{page_number}-chunk-{source_order}",
                        "text": cleaned_piece,
                        "page_start": page_number,
                        "page_end": page_number,
                        "chapter": page_data.get("chapter"),
                        "section_heading": unit.get("heading"),
                        "source_order": source_order,
                        "question_count": 0,
                        "question_history": [],
                        "max_questions": _estimate_chunk_capacity(cleaned_piece),
                    }
                )

    return chunks


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


def store_session_document(
    session_id: str,
    text: str,
    pages_with_metadata: list[dict[str, Any]],
    chapters: list[str],
    total_pages: int,
) -> int:
    if not text.strip() and not any(page.get("text", "").strip() for page in pages_with_metadata):
        return 0

    with _session_lock:
        _cleanup_locked()
        _sessions[session_id] = {
            "pages_with_metadata": [page.copy() for page in pages_with_metadata],
            "chunks": [],
            "updated_at": _now(),
            "preferences": DEFAULT_PREFERENCES.copy(),
            "chapters": list(chapters),
            "total_pages": total_pages,
            "last_chunk_id": None,
            "used_questions": set(),
        }

    return 0


def _build_progress_summary(session: dict[str, Any]) -> dict[str, int | str]:
    total_questions = sum(chunk["max_questions"] for chunk in session["chunks"])
    used_questions = sum(chunk["question_count"] for chunk in session["chunks"])
    remaining_questions = max(0, total_questions - used_questions)

    return {
        "used_questions": used_questions,
        "estimated_question_count": total_questions,
        "questions_remaining": remaining_questions,
        "fraction": f"{used_questions}/{total_questions}" if total_questions else "0/0",
    }


def get_session(session_id: str) -> dict[str, Any] | None:
    with _session_lock:
        _cleanup_locked()
        session = _sessions.get(session_id)
        if not session:
            return None

        session["updated_at"] = _now()
        return {
            "preferences": {
                "scope": session["preferences"]["scope"],
                "page_ranges": [page_range.copy() for page_range in session["preferences"]["page_ranges"]],
                "chapters": list(session["preferences"]["chapters"]),
            },
            "chapters": list(session["chapters"]),
            "total_pages": session["total_pages"],
            "chunk_count": len(session["chunks"]),
            "progress": _build_progress_summary(session),
        }


def set_session_preferences(
    session_id: str,
    scope: str,
    page_ranges: list[tuple[int, int]] | None = None,
    chapters: list[str] | None = None,
) -> dict[str, Any] | None:
    with _session_lock:
        _cleanup_locked()
        session = _sessions.get(session_id)
        if not session:
            return None

        normalized_ranges = [_normalize_range(page_range) for page_range in (page_ranges or [])]
        normalized_chapters = list(dict.fromkeys(chapters or []))
        preferences = {
            "scope": scope,
            "page_ranges": normalized_ranges,
            "chapters": normalized_chapters,
        }

        chunks = _build_chunks_for_preferences(session["pages_with_metadata"], preferences)

        session["preferences"] = preferences
        session["chunks"] = chunks
        session["updated_at"] = _now()
        session["last_chunk_id"] = None
        session["used_questions"].clear()

        return {
            "scope": scope,
            "page_ranges": [page_range.copy() for page_range in normalized_ranges],
            "chapters": list(normalized_chapters),
            "chunk_count": len(chunks),
            **_build_progress_summary(session),
        }


def get_next_chunk(session_id: str, exclude_chunk_ids: set[str] | None = None) -> dict[str, Any] | None:
    with _session_lock:
        _cleanup_locked()
        session = _sessions.get(session_id)
        if not session:
            return None

        excluded = exclude_chunk_ids or set()
        eligible_chunks = [
            chunk
            for chunk in session["chunks"]
            if chunk["question_count"] < chunk["max_questions"]
            and chunk["id"] not in excluded
        ]
        if not eligible_chunks:
            return None

        last_chunk_id = session.get("last_chunk_id")
        non_repeating = [chunk for chunk in eligible_chunks if chunk["id"] != last_chunk_id]
        candidates = non_repeating or eligible_chunks

        min_question_count = min(chunk["question_count"] for chunk in candidates)
        least_used = [
            chunk for chunk in candidates if chunk["question_count"] == min_question_count
        ]
        selected = min(least_used, key=lambda chunk: chunk["source_order"])
        session["updated_at"] = _now()

        return {
            key: (value.copy() if isinstance(value, list) else value)
            for key, value in selected.items()
        }


def _normalize_question(question: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()


def is_question_repeated(session_id: str, chunk_id: str, question: str) -> bool:
    normalized_question = _normalize_question(question)
    if not normalized_question:
        return True

    with _session_lock:
        _cleanup_locked()
        session = _sessions.get(session_id)
        if not session:
            return True

        if normalized_question in session["used_questions"]:
            return True

        for chunk in session["chunks"]:
            if chunk["id"] != chunk_id:
                continue

            for previous in chunk["question_history"]:
                previous_normalized = _normalize_question(previous)
                if previous_normalized == normalized_question:
                    return True
                if previous_normalized and (
                    normalized_question in previous_normalized
                    or previous_normalized in normalized_question
                ):
                    return True

        return False


def record_chunk_question(session_id: str, chunk_id: str, question: str) -> bool:
    normalized_question = _normalize_question(question)
    if not normalized_question:
        return False

    with _session_lock:
        _cleanup_locked()
        session = _sessions.get(session_id)
        if not session:
            return False

        for chunk in session["chunks"]:
            if chunk["id"] != chunk_id:
                continue

            chunk["question_count"] += 1
            chunk["question_history"].append(question)
            session["used_questions"].add(normalized_question)
            session["last_chunk_id"] = chunk_id
            session["updated_at"] = _now()
            return True

        return False


def get_progress(session_id: str) -> dict[str, int | str] | None:
    with _session_lock:
        _cleanup_locked()
        session = _sessions.get(session_id)
        if not session:
            return None

        session["updated_at"] = _now()
        return _build_progress_summary(session)
