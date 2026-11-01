# Paper Analyzer

Upload a research-paper PDF, pick an analysis, and get the result in the browser. Everything runs locally with an open-source model via [Ollama](https://ollama.com). Nothing is stored: results live in memory for one hour, and you can download them.

## Analyses

Summarize · Section-by-section · One-line summary · Methodology diagram · Presentation slides (`.pptx`) · Problem scope and contribution · Key results · Dataset info · Limitations

## Setup (Windows)

1. Install [Ollama](https://ollama.com/download) and pull a model: `ollama pull llama3.1:8b-instruct-q4_K_M`
2. Install Node.js LTS (`winget install OpenJS.NodeJS.LTS`) and Python 3.11+.
3. Backend:
   ```
   cd backend
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   .venv\Scripts\python -m uvicorn app.main:app --port 8000
   ```
4. Frontend (new terminal):
   ```
   cd frontend
   npm install
   npm run dev
   ```
5. Open http://localhost:5173

## Configuration

Environment variables, prefix `PA_` (see `backend/app/config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `PA_MODEL` | `llama3.1:8b-instruct-q4_K_M` | Ollama model name |
| `PA_NUM_CTX` | `4096` | Context window; larger needs more VRAM |
| `PA_CHUNK_CHARS` | `7000` | Max text per model call; keep it below the context window |
| `PA_MAX_UPLOAD_MB` | `20` | Upload size limit |
| `PA_CACHE_TTL_SECONDS` | `3600` | How long papers and jobs stay in memory |

With a larger GPU, raise `PA_NUM_CTX` (e.g. 16384) and `PA_CHUNK_CHARS` (e.g. 30000) for better results on long papers.

## Tests

```
cd backend
.venv\Scripts\python -m pytest
```

## Limitations

- Scanned (image-only) PDFs are not supported; there is no OCR.
- Small local models can miss details or misstate numbers. Check important results against the paper.
- "Inferred" limitations are the model's own opinion, not the authors'.
