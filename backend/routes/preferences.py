from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from services.embedder import get_session, set_session_preferences


router = APIRouter()


class PreferenceRequest(BaseModel):
    scope: str
    page_ranges: list[str] = []
    chapters: list[str] = []

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"all", "pages", "chapters"}:
            raise ValueError("scope must be one of: all, pages, chapters")
        return normalized


def _parse_page_range(page_range: str) -> tuple[int, int]:
    value = page_range.strip()
    if not value:
        raise ValueError("Page range cannot be empty")

    if "-" in value:
        start_str, end_str = value.split("-", 1)
        start = int(start_str.strip())
        end = int(end_str.strip())
    else:
        start = int(value)
        end = start

    if start < 1 or end < 1:
        raise ValueError("Page numbers must be 1 or greater")

    return start, end


@router.post("/preferences/{session_id}")
def save_preferences(session_id: str, request: PreferenceRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    page_ranges: list[tuple[int, int]] = []

    if request.scope == "pages":
        if not request.page_ranges:
            raise HTTPException(status_code=400, detail="Select at least one page or range")

        try:
            page_ranges = [_parse_page_range(page_range) for page_range in request.page_ranges]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        for start, end in page_ranges:
            if start > session["total_pages"] or end > session["total_pages"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Page selection must be between 1 and {session['total_pages']}",
                )

    chapters: list[str] = []

    if request.scope == "chapters":
        if not request.chapters:
            raise HTTPException(status_code=400, detail="Select at least one chapter")

        available_chapters = set(session["chapters"])
        chapters = [chapter for chapter in request.chapters if chapter in available_chapters]

        if not chapters:
            raise HTTPException(status_code=400, detail="Selected chapters are not available in this document")

    preferences = set_session_preferences(
        session_id=session_id,
        scope=request.scope,
        page_ranges=page_ranges,
        chapters=chapters,
    )

    if not preferences:
        raise HTTPException(status_code=404, detail="Session not found")

    if preferences["chunk_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No quiz content could be generated from the selected scope",
        )

    return {
        "session_id": session_id,
        "preferences": preferences,
    }
