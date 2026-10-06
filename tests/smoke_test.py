"""
Offline smoke test: exercises ingestion -> embedding -> vector store ->
extraction -> compare -> database, without requiring an LLM API key
(the LLM call itself is skipped/mocked here; it's tested separately
via the live backend once a key is configured).
Run with:  venv\\Scripts\\python tests\\smoke_test.py
"""
import sys
from pathlib import Path

# Windows consoles default to cp1252, which cannot encode emoji used in
# status output below; force UTF-8 so this script runs cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import fitz  # PyMuPDF

from backend import config, database, ingestion, embed_store, extraction, compare


def make_sample_pdf(path: Path, variant: int = 1):
    doc = fitz.open()
    page = doc.new_page()
    title = "AUTOSAR HLD Overview" if variant == 1 else "AUTOSAR HLD Overview v2"
    body = (
        "1. Component Overview\n"
        "The NetworkManagerComponent provides the NetworkStateInterface to consumers.\n"
        "Component: ComFacade\n"
        "Interface: ComFacadeInterface\n"
        "PPort: ComFacade_PPort\n"
        "Signal: EngineSpeed_Signal\n\n"
        "2. Dependencies\n"
        "ComFacade depends on NetworkManagerComponent for signal routing."
    )
    if variant == 2:
        body += "\n\n3. Revision Note\nAdded DiagnosticManagerComponent in this revision."

    page.insert_text((72, 72), title, fontsize=16)
    page.insert_text((72, 110), body, fontsize=10)
    doc.save(str(path))
    doc.close()


def run():
    created = []  # (doc_id, pdf_path) to clean up even if an assertion fails
    try:
        _run(created)
    finally:
        for doc_id, pdf_path in created:
            embed_store.delete_document_chunks(doc_id)
            database.delete_document(doc_id)
            pdf_path.unlink(missing_ok=True)
    print("\nALL SMOKE TESTS PASSED ✅")


def _run(created):
    print("== 1. DB init ==")
    database.init_db()
    print("OK")

    print("== 2. Ingest sample PDF A ==")
    pdf_a = PROJECT_ROOT / "tests" / "_sample_a.pdf"
    make_sample_pdf(pdf_a, variant=1)
    result_a = ingestion.ingest_pdf(pdf_a.read_bytes(), "sample_a.pdf")
    created.append((result_a.doc_id, pdf_a))
    assert result_a.chunks, "No chunks extracted from sample A"
    print(f"OK - {len(result_a.chunks)} chunks, {result_a.pages} pages")

    print("== 3. Ingest sample PDF B (revision) ==")
    pdf_b = PROJECT_ROOT / "tests" / "_sample_b.pdf"
    make_sample_pdf(pdf_b, variant=2)
    result_b = ingestion.ingest_pdf(pdf_b.read_bytes(), "sample_b.pdf")
    created.append((result_b.doc_id, pdf_b))
    assert result_b.chunks, "No chunks extracted from sample B"
    print(f"OK - {len(result_b.chunks)} chunks, {result_b.pages} pages")

    print("== 4. Embed + store ==")
    embed_store.add_chunks(result_a.chunks)
    embed_store.add_chunks(result_b.chunks)
    database.add_document(result_a.doc_id, "sample_a.pdf", result_a.pages, len(result_a.chunks))
    database.add_document(result_b.doc_id, "sample_b.pdf", result_b.pages, len(result_b.chunks))
    count = embed_store.collection_count()
    assert count >= len(result_a.chunks) + len(result_b.chunks)
    print(f"OK - {count} chunks in vector store")

    print("== 5. Vector query ==")
    hits = embed_store.query("What does ComFacade depend on?", doc_ids=[result_a.doc_id])
    assert hits, "No hits returned from vector query"
    print(f"OK - top hit page {hits[0]['metadata']['page']}, distance {hits[0]['distance']:.4f}")

    print("== 6. Entity extraction ==")
    rows = extraction.extract_entities([result_a.doc_id, result_b.doc_id])
    assert rows, "No entities extracted"
    print(f"OK - {len(rows)} entities found: {[r['name'] for r in rows[:5]]}")

    print("== 7. Document comparison ==")
    findings = compare.compare_documents(result_a.doc_id, "sample_a.pdf", result_b.doc_id, "sample_b.pdf")
    assert any(f["status"] == "Entity added" and "DiagnosticManagerComponent" in f["section"] for f in findings), \
        "Compare missed the component added in revision B"
    print(f"OK - {len(findings)} comparison findings")


if __name__ == "__main__":
    run()
