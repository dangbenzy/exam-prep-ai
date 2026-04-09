from services.pdf_parser import extract_text_from_pdf
from services.embedder import embed_and_store, get_relevant_chunks
from services.question_gen import generate_question
from services.evaluator import evaluate_answer

# Extract text
with open("test.pdf", "rb") as f:
    file_bytes = f.read()

text = extract_text_from_pdf(file_bytes)
print(f"Extracted {len(text)} characters")

# Embed and store
num_chunks = embed_and_store("test_session_4", text)
print(f"Stored {num_chunks} chunks")

# Get relevant chunks and generate question
import random
all_chunks = get_relevant_chunks("test_session_4", random.choice([
    "key concepts",
    "main ideas", 
    "important details",
    "definitions",
    "processes"
]))
combined = " ".join(all_chunks)
question = generate_question(combined)
print(f"\nGenerated Question:\n{question}")

# Simulate student answer
student_answer = input("\nYour answer: ")

# Evaluate
result = evaluate_answer(combined, question, student_answer)
print(f"\nResult: {'✅ CORRECT' if result['is_correct'] else '❌ INCORRECT'}")
print(f"Feedback: {result['feedback']}")
if not result['is_correct']:
    print(f"Correct Answer: {result['correct_answer']}")