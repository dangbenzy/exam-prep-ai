from fastapi import APIRouter, HTTPException
from services.embedder import get_relevant_chunks
from services.question_gen import generate_question
import random

router = APIRouter()

asked_questions = {}

@router.get("/question/{session_id}")
def get_question(session_id: str):
    queries = [
        "key concepts",
        "main ideas",
        "important details",
        "definitions",
        "processes and methods",
        "causes and effects",
        "examples and applications"
    ]

    query = random.choice(queries)
    chunks = get_relevant_chunks(session_id, query)

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