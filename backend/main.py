"""FastAPI backend for the AUTOSAR HLD Document Analysis Assistant."""
import io
import json
import time
import traceback

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd

from backend import config
from backend import database
from backend import ingestion
from backend import embed_store
from backend import rag
from backend import extraction
from backend import compare as compare_mod

app = FastAPI(title="AUTOSAR HLD Document Analysis Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    database.init_db()


def _friendly_error(prefix: str, exc: Exception) -> HTTPException:
    # Full trace goes to server logs only; the client gets a clean message.
    traceback.print_exc()
    return HTTPException(status_code=500, detail=f"{prefix}: {exc.__class__.__name__} - {exc}")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "documents_indexed": len(database.list_documents()),
        "chunks_in_vector_store": embed_store.collection_count(),
        "llm_provider": config.LLM_PROVIDER,
        "llm_model": config.GROQ_MODEL if config.LLM_PROVIDER == "groq" else config.GEMINI_MODEL,
        "ocr_available": ingestion.OCR_AVAILABLE,
    }


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        result = ingestion.ingest_pdf(content, file.filename)
        if not result.chunks:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No readable text could be extracted from this PDF, even with OCR. "
                    "Please check the file and try again."
                ),
            )

        # Re-uploading a file with the same name replaces the earlier copy
        # instead of silently creating a duplicate that doubles every answer.
        for old in database.list_documents():
            if old["filename"] == result.filename:
                embed_store.delete_document_chunks(old["doc_id"])
                database.delete_document(old["doc_id"])

        embed_store.add_chunks(result.chunks)
        database.add_document(
            doc_id=result.doc_id,
            filename=result.filename,
            pages=result.pages,
            chunks=len(result.chunks),
            ocr_pages=result.ocr_pages,
        )

        return {
            "doc_id": result.doc_id,
            "filename": result.filename,
            "pages": result.pages,
            "chunks": len(result.chunks),
            "ocr_pages": result.ocr_pages,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise _friendly_error("Failed to process the uploaded PDF", e)


@app.get("/documents")
def get_documents():
    try:
        return database.list_documents()
    except Exception as e:
        raise _friendly_error("Failed to load document list", e)


@app.delete("/documents/{doc_id}")
def remove_document(doc_id: str):
    try:
        embed_store.delete_document_chunks(doc_id)
        database.delete_document(doc_id)
        return {"deleted": doc_id}
    except Exception as e:
        raise _friendly_error("Failed to delete document", e)


@app.post("/ask")
def ask_question(payload: dict = Body(...)):
    question = (payload.get("question") or "").strip()
    doc_ids = payload.get("doc_ids") or None

    if not question:
        raise HTTPException(status_code=400, detail="Please provide a non-empty question.")

    try:
        result = rag.answer_question(question, doc_ids=doc_ids)
        database.log_query(
            doc_ids or [],
            question,
            result["answer"],
            result["citations"],
            result["confidence"],
        )
        return result
    except Exception as e:
        raise _friendly_error("Failed to answer the question", e)


@app.post("/extract")
def extract_entities(payload: dict = Body(...)):
    doc_ids = payload.get("doc_ids") or []
    if not doc_ids:
        raise HTTPException(status_code=400, detail="Please select at least one document.")
    try:
        return extraction.extract_entities(doc_ids, use_llm=bool(payload.get("use_llm")))
    except Exception as e:
        raise _friendly_error("Failed to extract architecture entities", e)


@app.post("/compare")
def compare_documents(payload: dict = Body(...)):
    doc_id_a = payload.get("doc_id_a")
    doc_id_b = payload.get("doc_id_b")

    if not doc_id_a or not doc_id_b:
        raise HTTPException(status_code=400, detail="Please select two documents to compare.")
    if doc_id_a == doc_id_b:
        raise HTTPException(status_code=400, detail="Please select two different documents.")

    names = {d["doc_id"]: d["filename"] for d in database.list_documents()}
    filename_a = payload.get("filename_a") or names.get(doc_id_a, "Document A")
    filename_b = payload.get("filename_b") or names.get(doc_id_b, "Document B")

    try:
        return compare_mod.compare_documents(doc_id_a, filename_a, doc_id_b, filename_b)
    except Exception as e:
        raise _friendly_error("Failed to compare documents", e)


@app.get("/history")
def get_history(limit: int = 200):
    try:
        return database.list_queries(limit=limit)
    except Exception as e:
        raise _friendly_error("Failed to load history", e)


@app.get("/export/{fmt}")
def export_history(fmt: str):
    fmt = fmt.lower()
    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="Export format must be 'json' or 'csv'.")

    try:
        history = database.list_queries(limit=10000)
        if fmt == "json":
            buf = io.BytesIO(json.dumps(history, indent=2).encode("utf-8"))
            return StreamingResponse(
                buf,
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=qa_history.json"},
            )
        else:
            flat = []
            for h in history:
                flat.append(
                    {
                        "asked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(h["asked_at"])),
                        "documents": ", ".join(h["doc_ids"]),
                        "question": h["question"],
                        "answer": h["answer"],
                        "confidence": h["confidence"],
                        "citation_count": len(h["citations"]),
                    }
                )
            df = pd.DataFrame(flat)
            buf = io.BytesIO()
            df.to_csv(buf, index=False)
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=qa_history.csv"},
            )
    except Exception as e:
        raise _friendly_error("Failed to export history", e)
