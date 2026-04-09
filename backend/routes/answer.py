from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.evaluator import evaluate_answer

router = APIRouter()

class AnswerRequest(BaseModel):
    session_id: str
    question: str
    context: str
    student_answer: str

@router.post("/answer")
def submit_answer(request: AnswerRequest):
    if not request.student_answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    result = evaluate_answer(request.context, request.question, request.student_answer)

    return {
        "session_id": request.session_id,
        "question": request.question,
        "student_answer": request.student_answer,
        "is_correct": result["is_correct"],
        "feedback": result["feedback"],
        "correct_answer": result["correct_answer"]
    }