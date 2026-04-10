import chromadb
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

chroma_client = chromadb.PersistentClient(path="./chroma_db")

def get_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text
    )
    return result["embedding"]

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def embed_and_store(session_id: str, text: str):
    collection = chroma_client.get_or_create_collection(name=session_id)
    chunks = chunk_text(text)
    embeddings = [get_embedding(chunk) for chunk in chunks]
    ids = [f"{session_id}_chunk_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, embeddings=embeddings, ids=ids)
    return len(chunks)

def get_relevant_chunks(session_id: str, query: str, n_results: int = 3) -> list[str]:
    collection = chroma_client.get_or_create_collection(name=session_id)
    query_embedding = get_embedding(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    return results["documents"][0]