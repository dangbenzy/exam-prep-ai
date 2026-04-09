import chromadb
from chromadb.utils import embedding_functions

chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def embed_and_store(session_id: str, text: str):
    collection = chroma_client.get_or_create_collection(
        name=session_id,
        embedding_function=embedding_fn
    )
    chunks = chunk_text(text)
    ids = [f"{session_id}_chunk_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids)
    return len(chunks)

def get_relevant_chunks(session_id: str, query: str, n_results: int = 3) -> list[str]:
    collection = chroma_client.get_or_create_collection(
        name=session_id,
        embedding_function=embedding_fn
    )
    results = collection.query(query_texts=[query], n_results=n_results)
    return results["documents"][0]