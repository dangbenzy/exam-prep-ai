from fastapi import APIRouter, HTTPException
from services.embedder import get_relevant_chunks
from services.question_gen import generate_question

router = APIRouter()

asked_questions = {}

@router.get("/question/{session_id}")
def get_question(session_id: str):
    chunks = get_relevant_chunks(session_id)

    if not chunks:
        raise HTTPException(status_code=404, detail="No content found for this session")

    combined = " ".join(chunks)
    question = generate_question(combined)

    if session_id not in asked_questions:
        asked_questions[session_id] = []

    asked_questions[session_id].append(question)

    return {
        "session_id": session_id,
        "question": question,
        "context": combined
    }
