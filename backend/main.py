from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Exam Prep AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import upload, question, answer

app.include_router(upload.router)
app.include_router(question.router)
app.include_router(answer.router)

@app.get("/")
def root():
    return {"message": "Exam Prep AI is running"}