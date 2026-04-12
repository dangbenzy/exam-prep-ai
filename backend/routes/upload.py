from fastapi import APIRouter, UploadFile, File, HTTPException
from services.pdf_parser import extract_text_from_pdf
from services.embedder import store_session_chunks
import uuid

router = APIRouter()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_bytes = await file.read()
    
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    text = extract_text_from_pdf(file_bytes)
    
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")
    
    session_id = str(uuid.uuid4())
    num_chunks = store_session_chunks(session_id, text)
    
    return {
        "session_id": session_id,
        "message": "PDF uploaded and processed successfully",
        "chunks_stored": num_chunks
    }
