"""
Central configuration. Imported first by every other module so that
model/library cache directories are redirected onto the D: drive
BEFORE any heavy library (sentence-transformers, chromadb, huggingface_hub)
gets imported anywhere in the process. This keeps the project fully
self-contained under this folder and avoids writing anything to C:.
"""
import logging
import os
from pathlib import Path

# ChromaDB's optional posthog telemetry occasionally raises a harmless,
# already-caught exception on this chromadb/posthog version combo; it logs
# a "Failed to send telemetry event" warning each time. Silence just that
# logger so real errors elsewhere are not lost in the noise.
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma_db"
CACHE_DIR = DATA_DIR / "cache"
HF_CACHE_DIR = CACHE_DIR / "hf"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "app.db"

for d in (UPLOADS_DIR, CHROMA_DIR, CACHE_DIR, HF_CACHE_DIR, EXPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Redirect all model / hub caches onto D: (must happen before importing
# sentence_transformers / huggingface_hub / transformers anywhere).
os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
os.environ.setdefault("HF_HUB_CACHE", str(HF_CACHE_DIR))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(HF_CACHE_DIR))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Load .env (kept local, never committed) for API keys. override=True so
# the project's .env always wins over a stray shell/session environment
# variable left over from earlier experimentation (otherwise python-dotenv
# silently keeps whatever was already in os.environ).
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=True)
except Exception:
    pass

EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq").lower()  # "groq" or "gemini"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")  # optional explicit path to tesseract.exe

BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

CHUNK_MAX_CHARS = 1200
CHUNK_OVERLAP_CHARS = 150
TOP_K_RETRIEVAL = 5
