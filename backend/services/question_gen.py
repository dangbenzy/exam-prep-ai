import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def generate_question(
    chunk: str,
    previous_questions: list[str] | None = None,
    section_heading: str | None = None,
) -> str:
    history_block = ""
    if previous_questions:
        formatted_history = "\n".join(f"- {question}" for question in previous_questions[-3:])
        history_block = f"""
Do not repeat or closely paraphrase any of these earlier questions from this quiz:
{formatted_history}
"""

    heading_block = f"\nSection heading: {section_heading}\n" if section_heading else ""

    prompt = f"""You are an exam question generator.

Given the following text, generate ONE complete, clear, distinct exam-style question that tests understanding of the content.
Use only the supplied text and focus on one examinable idea. Return only the question on one line, ending with a question mark.
Do not return a fragment, an answer, an explanation, or repeat/closely paraphrase an earlier question.
{history_block}
{heading_block}
Text:
{chunk}

Question:"""

    generation_options = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_completion_tokens": 256,
    }
    if model.startswith("openai/gpt-oss-"):
        generation_options.update(reasoning_effort="low", include_reasoning=False)

    response = client.chat.completions.create(**generation_options)
    choice = response.choices[0]
    question = (choice.message.content or "").strip().replace("\n", " ")
    question = " ".join(question.split()).strip(" `\"'“”‘’")

    if choice.finish_reason == "length":
        raise ValueError("The model truncated the question before completing it")

    if len(question.split()) < 3 or not question.endswith("?"):
        raise ValueError("The model did not return a complete question")

    return question
