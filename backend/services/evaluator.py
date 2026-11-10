import json
import os
import re

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

def evaluate_answer(chunk: str, question: str, student_answer: str) -> dict:
    prompt = f"""You are an exam evaluator.

Context:
{chunk}

Question:
{question}

Student's Answer:
{student_answer}

Evaluate whether the student's answer is correct based only on the context.
Return a JSON object with exactly these keys:
- "correct_answer": "N/A" when correct; otherwise give a concise, complete answer that directly answers the question using the context
- "feedback": one concise explanation that starts with "You were right!" when correct or "Your answer was wrong." when incorrect
- "is_correct": a boolean
Never leave "correct_answer" empty when the answer is incorrect.
"""

    generation_options = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_completion_tokens": 768,
        "response_format": {"type": "json_object"},
    }
    if model.startswith("openai/gpt-oss-"):
        generation_options.update(
            reasoning_effort="low",
            include_reasoning=False,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "answer_evaluation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "correct_answer": {"type": "string"},
                            "feedback": {"type": "string"},
                            "is_correct": {"type": "boolean"},
                        },
                        "required": ["correct_answer", "feedback", "is_correct"],
                        "additionalProperties": False,
                    },
                },
            },
        )

    response = client.chat.completions.create(**generation_options)
    raw = (response.choices[0].message.content or "").strip()

    try:
        parsed = json.loads(raw)
        is_correct = parsed.get("is_correct", False)
        if isinstance(is_correct, str):
            is_correct = is_correct.strip().lower() in {"true", "correct", "yes"}

        feedback = str(parsed.get("feedback") or "").strip()
        correct_answer = str(parsed.get("correct_answer") or "").strip()
    except (json.JSONDecodeError, AttributeError, TypeError):
        # Keep older/custom model outputs usable if they ignore JSON mode.
        result_match = re.search(r"^\s*(?:RESULT:\s*)?(CORRECT|INCORRECT)\b", raw, re.IGNORECASE | re.MULTILINE)
        is_correct = bool(result_match and result_match.group(1).upper() == "CORRECT")
        feedback_match = re.search(
            r"^\s*FEEDBACK:\s*(.*?)(?=^\s*CORRECT ANSWER:|\Z)",
            raw,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        answer_match = re.search(r"^\s*CORRECT ANSWER:\s*(.*)\Z", raw, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        feedback = feedback_match.group(1).strip() if feedback_match else ""
        correct_answer = answer_match.group(1).strip() if answer_match else ""

    if not is_correct and (not correct_answer or correct_answer.upper() == "N/A"):
        correct_answer = feedback or "Please review the supplied source context for the correct answer."

    return {
        "is_correct": bool(is_correct),
        "feedback": feedback,
        "correct_answer": "N/A" if is_correct else correct_answer,
    }
