import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def evaluate_answer(chunk: str, question: str, student_answer: str) -> dict:
    prompt = f"""You are an exam evaluator.

Context:
{chunk}

Question:
{question}

Student's Answer:
{student_answer}

Evaluate if the student's answer is correct based on the context.
Respond in exactly this format:
RESULT: CORRECT or INCORRECT
FEEDBACK: If correct, start with "You were right!" and explain why the answer is correct. If incorrect, start with "Your answer was wrong." and explain why.
CORRECT ANSWER: the correct answer if wrong, or "N/A" if correct
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200
    )

    raw = response.choices[0].message.content.strip()

    result = {"is_correct": False, "feedback": "", "correct_answer": ""}

    for line in raw.split("\n"):
        if line.startswith("RESULT:"):
            result["is_correct"] = "CORRECT" in line.upper() and "INCORRECT" not in line.upper()
        elif line.startswith("FEEDBACK:"):
            result["feedback"] = line.replace("FEEDBACK:", "").strip()
        elif line.startswith("CORRECT ANSWER:"):
            result["correct_answer"] = line.replace("CORRECT ANSWER:", "").strip()

    return result