# Exam Prep AI

Exam Prep AI is an AI-powered exam preparation tool that quizzes students from uploaded course materials.

## What It Does

- Upload a PDF containing notes, slides, or reading material
- Extract text from the PDF with PyMuPDF
- Create short in-memory study chunks for the current session
- Generate an exam-style question from the uploaded material
- Evaluate the student's answer and return feedback

## How It Works

The app has a lightweight frontend and a FastAPI backend.

Main flow:

1. The user uploads a PDF.
2. The backend extracts the text from the PDF.
3. The text is split into chunks and stored in memory for the active session.
4. A question is generated from selected chunks using Groq.
5. The student's answer is checked against the question context using Groq.

This version does not persist a vector database during deployment. Session content is kept in memory with limits and expiry so repeated tests do not keep growing memory usage.

## Project Structure

```text
exam-prep-ai/
|- backend/
|  |- main.py
|  |- routes/
|  |- services/
|  |- requirements.txt
|- frontend/
|  |- index.html
|- .github/workflows/
|  |- deploy.yml
|- Dockerfile
|- README.md
```

## Tech Stack

- **Backend** — FastAPI
- **ASGI Server** — Uvicorn
- **LLM** — Groq
- **PDF Parsing** — PyMuPDF
- **Frontend** — HTML, CSS, JavaScript
- **Deployment** — Render
- **Containerization** — Docker
- **CI** — GitHub Actions

## Live Demo

https://exam-prep-ai-87aq.onrender.com

## Local Setup

### 1. Clone the project

```bash
git clone https://github.com/dangbenzy/exam-prep-ai.git
cd exam-prep-ai
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Add environment variables

Create `backend/.env` and add:

```env
GROQ_API_KEY=your_groq_api_key
```

Optional memory/session tuning:

```env
SESSION_TTL_SECONDS=3600
MAX_ACTIVE_SESSIONS=25
CHUNK_SIZE=1200
CHUNK_OVERLAP=150
MAX_CHUNKS_PER_SESSION=30
```

### 5. Run the app

From the `backend` folder:

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## API Endpoints

- `POST /upload`
  Upload a PDF and create a study session.

- `GET /question/{session_id}`
  Generate the next question for the uploaded material.

- `POST /answer`
  Submit a student's answer and get feedback.

## Deployment

The project includes a root `Dockerfile` for deployment.

Important deployment notes:

- `backend/.env`, `backend/venv`, `backend/chroma_db`, PDFs, and cache files are excluded from the Docker build context with `.dockerignore`
- sessions are stored in memory instead of a persistent local vector database
- this reduces memory growth on free hosting tiers

### Render

To deploy on Render:

1. Connect the GitHub repository
2. Use the root `Dockerfile`
3. Add `GROQ_API_KEY` in Render environment variables
4. Keep Render set to deploy after CI checks pass

## CI

GitHub Actions is configured to run backend checks on pushes and pull requests.

Current CI workflow:

- installs backend dependencies
- compiles the backend Python files

Workflow file:

`/.github/workflows/deploy.yml`

## Current Limitations

- session data is not shared across restarts
- there is no user authentication yet
- CI currently performs compile checks, not full automated test coverage
- the frontend is intentionally simple and single-page

## Future Improvements

- add unit and integration tests
- add question difficulty levels
- improve answer grading structure
- support multiple file uploads
- store study history for users
- improve frontend design and UX

## Author

**Gbenga Daniel Ilori**  
[GitHub](https://github.com/dangbenzy) · [LinkedIn](https://linkedin.com/in/gbenga-ilori)
