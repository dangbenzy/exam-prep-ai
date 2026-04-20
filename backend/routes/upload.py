import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from services.embedder import store_session_document
from services.pdf_parser import extract_text_with_metadata


router = APIRouter()


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    metadata = extract_text_with_metadata(file_bytes)
    text = metadata["text"]

    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    session_id = str(uuid.uuid4())
    num_chunks = store_session_document(
        session_id=session_id,
        text=text,
        pages_with_metadata=metadata["pages_with_metadata"],
        chapters=metadata["chapters"],
        total_pages=metadata["total_pages"],
    )

    return {
        "session_id": session_id,
        "message": "PDF uploaded and processed successfully",
        "chunks_stored": num_chunks,
        "total_pages": metadata["total_pages"],
        "chapters": metadata["chapters"],
    }
