# AUTOSAR HLD Document Analysis Assistant

An AI-assisted RAG (Retrieval-Augmented Generation) application for automotive
engineers. Upload AUTOSAR High-Level Design (HLD) PDF documents and ask
natural-language questions, get architecture-entity extraction, compare
document revisions, and export the full Q&A audit history — all grounded in
your own documents with page-level citations.

Themed as an "Engineering Blueprint" UI: dark navy blueprint-grid background,
cyan schematic accents, monospace technical typography.

Everything runs **locally and for free**:
- Embeddings + vector search run on your machine (Sentence-Transformers + ChromaDB) — no cost, no external calls.
- Only the final answer generation calls a free-tier LLM API (Groq or Gemini).
- All data, caches, and the virtual environment live **inside this project folder**, nothing is written elsewhere.

---

## 1. Prerequisites

- Python 3.10+
- (Optional, for scanned PDFs) [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki). If it is not installed the app still works; OCR is simply skipped for scanned pages.
- A free API key from **either**:
  - [Groq](https://console.groq.com) (recommended: fast, generous free tier), or
  - [Google AI Studio / Gemini](https://aistudio.google.com/app/apikey)

## 2. Setup (run once)

```powershell
git clone <this-repo-url>
cd AUTOSAR_HLD_Assistant

python -m venv venv
venv\Scripts\pip install -r requirements.txt

copy .env.example .env
notepad .env    # paste your GROQ_API_KEY (or GEMINI_API_KEY and set LLM_PROVIDER=gemini)
```

The first run downloads the small embedding model (~90 MB) into `data/cache/`.
Five sample HLD PDFs are in `sample_documents/` so you can try the app straight away.

## 3. Run (single command)

```powershell
.\start.ps1
```

or, from a plain cmd prompt:

```cmd
start.bat
```

This launches the FastAPI backend in one window and the Streamlit UI in your
browser automatically (usually at `http://localhost:8501`).

**Manual alternative** (two terminals), if you prefer:

```powershell
# Terminal 1
venv\Scripts\python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2
venv\Scripts\python -m streamlit run frontend\app.py
```

## 4. Using the app

1. Open the sidebar → drag & drop one or more AUTOSAR HLD PDF files.
2. Wait for ingestion to finish (extraction → chunking → embedding → vector store).
3. Go to **💬 Ask** → type a question (or click an example) → get a cited, confidence-scored answer.
4. Go to **🧩 Extraction** → run the structured component/interface/signal extraction.
5. Go to **🔍 Compare** → pick two document versions to flag section-level inconsistencies.
6. Go to **📜 History & Export** → download the full Q&A audit trail as JSON or CSV.

## 5. Project structure

```
AUTOSAR_HLD_Assistant/
├── backend/
│   ├── config.py       # paths, cache locations, env vars
│   ├── database.py     # SQLite audit log (documents, Q&A history)
│   ├── ingestion.py     # PDF extraction, OCR fallback, heading-aware chunking
│   ├── embed_store.py   # Sentence-Transformers embeddings + ChromaDB
│   ├── rag.py           # retrieval + LLM call + citations + confidence
│   ├── extraction.py    # component/interface/signal heuristic extraction
│   ├── compare.py       # two-document section-level diff
│   └── main.py          # FastAPI app & REST endpoints
├── frontend/
│   ├── api_client.py    # thin HTTP client to the backend (error-safe)
│   ├── theme.py          # "Engineering Blueprint" custom CSS
│   └── app.py            # Streamlit UI
├── tests/
│   ├── smoke_test.py   # offline pipeline test
│   └── api_test.py     # live end-to-end API test
├── data/                 # uploads, chroma_db, cache, exports, app.db (all local, gitignored)
├── requirements.txt
├── .env.example
├── start.bat / start.ps1
└── README.md
```

## 6. Notes on design decisions

- **RAG, not fine-tuning**: answers are grounded strictly in retrieved chunks from your own uploaded PDFs; the system prompt explicitly forbids inventing component/interface names not present in context.
- **Confidence indicator**: derived from vector-similarity distance of retrieved chunks (High / Medium / Low / No evidence found) — a simple, transparent heuristic rather than a black-box score.
- **Graceful degradation everywhere**: if the LLM API key is missing or the API call fails, the app still shows the raw retrieved evidence instead of crashing, with a clear inline note explaining what happened.
- **Comparison** reports section-level changes (with the lines added/removed) plus an architecture-level diff of components, interfaces, ports and signals.
- **Re-uploading** a file with the same name replaces the earlier copy rather than duplicating it.
- **Tests**: `venv\Scripts\python tests\smoke_test.py` runs the offline pipeline test (no API key needed). With the backend running, `venv\Scripts\python testspi_test.py` exercises every endpoint end to end, including a live LLM answer.
- **Unanswerable questions**: if the model says the documents don't cover a question, the answer is shown with confidence "No evidence found" and no citations, instead of listing unrelated chunks.
- **Extraction coverage**: recognises `Component:`/`Software Component:`/`SWC:`/`Composition:` and `*Component`/`*SWC`/`*Manager`-style names, `Interface:` (incl. Sender-Receiver / Client-Server) and `*_If`, P/R/PR-ports, `Signal:`/`I-Signal:`, and `Runnable:`. Tick **AI-assisted** on the Extraction tab to also have the LLM list entities, which handles any naming style; names it returns are kept only if they literally appear in the document text (hallucination guard).
- **No paid infrastructure required**: ChromaDB and Sentence-Transformers run entirely on your machine; only the LLM call uses a hosted free-tier API.
- **Self-contained**: model cache, vector store, database and uploaded files are all rooted under `data/` in the project folder.

## 7. Free deployment options

- **Local demo**: exactly as described above.
- **Docker**: a `Dockerfile` and `docker-compose.yml` are included (`docker compose up --build`); the UI is on port 8501 and the API on 8000. Built and verified (image ~680 MB, CPU-only PyTorch); your `.env` and `./data` folder are mounted in, so keys and indexed documents carry over.
- **Streamlit Community Cloud**: host the frontend for free; the backend + ChromaDB can run on a small always-on process (or be merged into a single Streamlit app for simplicity) since ChromaDB needs a persistent local file, not a separate paid server.
