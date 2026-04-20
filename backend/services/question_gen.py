import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_question(
    chunk: str,
    previous_questions: list[str] | None = None,
    section_heading: str | None = None,
) -> str:
    history_block = ""
    if previous_questions:
        formatted_history = "\n".join(f"- {question}" for question in previous_questions[-3:])
        history_block = f"""
Do not repeat or closely paraphrase any of these earlier questions from the same source chunk:
{formatted_history}
"""

    heading_block = f"\nSection heading: {section_heading}\n" if section_heading else ""

    prompt = f"""You are an exam question generator.

Given the following text, generate ONE clear, distinct exam-style question that tests understanding of the content.
Use only the supplied text. Focus on one examinable idea. Return ONLY the question.
Avoid generic wording and avoid repeating earlier questions.
{history_block}
{heading_block}
Text:
{chunk}

Question:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=120,
    )

    return response.choices[0].message.content.strip()
