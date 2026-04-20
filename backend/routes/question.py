from fastapi import APIRouter, HTTPException

from services.embedder import get_next_chunk, get_progress, is_question_repeated, record_chunk_question
from services.question_gen import generate_question


router = APIRouter()


def _build_question_response(session_id: str):
    attempted_chunk_ids = set()

    for _ in range(4):
        chunk = get_next_chunk(session_id, exclude_chunk_ids=attempted_chunk_ids)

        if not chunk:
            raise HTTPException(status_code=409, detail="All question opportunities in this quiz scope have been used")

        try:
            question = generate_question(
                chunk=chunk["text"],
                previous_questions=chunk.get("question_history", []),
                section_heading=chunk.get("section_heading"),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="Question generation failed. Please try again in a moment.",
            ) from exc

        if is_question_repeated(session_id, chunk["id"], question):
            attempted_chunk_ids.add(chunk["id"])
            continue

        if not record_chunk_question(session_id, chunk["id"], question):
            raise HTTPException(status_code=404, detail="Session not found")

        progress = get_progress(session_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Session not found")

        page_numbers = sorted(
            {
                page_number
                for page_number in range(
                    chunk["page_start"] or 0,
                    (chunk["page_end"] or -1) + 1,
                )
                if page_number > 0
            }
        )
        chapters = [chunk["chapter"]] if chunk.get("chapter") else []

        return {
            "session_id": session_id,
            "question": question,
            "context": chunk["text"],
            "source": {
                "pages": page_numbers,
                "chapters": chapters,
                "section_heading": chunk.get("section_heading"),
                "chunk_id": chunk["id"],
            },
            "progress": progress,
        }

    raise HTTPException(status_code=409, detail="Could not generate a new distinct question for this quiz scope")


@router.get("/question/{session_id}")
def get_question(session_id: str):
    return _build_question_response(session_id)


@router.post("/question/{session_id}/skip")
def skip_question(session_id: str):
    return _build_question_response(session_id)
