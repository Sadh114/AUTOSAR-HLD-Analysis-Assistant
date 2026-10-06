"""
Live end-to-end test against a RUNNING backend (needs a configured LLM key):
upload -> ask -> off-topic ask -> extract -> compare -> history/export -> delete.
Start the backend first:  venv\Scripts\python -m uvicorn backend.main:app --port 8000
Run with:                 venv\Scripts\python tests\api_test.py
"""
import sys
from pathlib import Path

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://127.0.0.1:8000"
SAMPLES = Path(__file__).resolve().parent.parent / "sample_documents"


def check(cond, msg):
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        sys.exit(1)


def upload(name):
    with open(SAMPLES / name, "rb") as f:
        r = requests.post(f"{BASE}/upload", files={"file": (name, f, "application/pdf")}, timeout=120)
    check(r.status_code == 200, f"upload {name}")
    return r.json()["doc_id"]


def post(path, **body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=120)
    return r


check(requests.get(f"{BASE}/health", timeout=10).json()["status"] == "ok", "health")

a = upload("BodyControlModule_HLD_RevA.pdf")
b = upload("BodyControlModule_HLD_RevB.pdf")
docs = requests.get(f"{BASE}/documents").json()
check(sum(d["filename"] == "BodyControlModule_HLD_RevA.pdf" for d in docs) == 1, "re-upload does not duplicate")

r = post("/ask", question="What interfaces does the Body Control Module expose?", doc_ids=[a]).json()
check(r["answer"].strip() and r["error"] is None, "ask returns an answer")
check("LightingControlInterface" in r["answer"] and r["citations"], "answer is grounded and cited")

r = post("/ask", question="What is the capital of France?").json()
check(r["citations"] == [] and r["confidence"] == "No evidence found", "off-topic question has no citations")

r = post("/extract", doc_ids=[a]).json()
names = {x["name"] for x in r}
check({"LightingManagerComponent", "DoorStatusInterface", "HeadlampState_Signal"} <= names, "extraction finds entities")

r = post("/compare", doc_id_a=a, doc_id_b=b).json()
check(any(f["status"] == "Entity added" and "MirrorControlComponent" in f["section"] for f in r), "compare finds added component")
# AI-assisted extraction must find entities written in a style the regexes miss.
import fitz
pdf = fitz.open()
pdf.new_page().insert_text((72, 100), "The WipeLogic element reads RainSense through the port RainIn.", fontsize=10)
custom = requests.post(
    f"{BASE}/upload", files={"file": ("zz_custom_style.pdf", pdf.tobytes(), "application/pdf")}, timeout=120
).json()["doc_id"]
check(post("/extract", doc_ids=[custom]).json() == [], "regex-only extraction misses custom naming style")
llm_names = {x["name"] for x in post("/extract", doc_ids=[custom], use_llm=True).json()}
check({"WipeLogic", "RainIn"} <= llm_names, "AI-assisted extraction finds custom-style entities")
requests.delete(f"{BASE}/documents/{custom}")

check(post("/compare", doc_id_a=a, doc_id_b=a).status_code == 400, "compare rejects identical docs")

tmp = upload("PowertrainControl_HLD.pdf")
check(requests.delete(f"{BASE}/documents/{tmp}").status_code == 200, "delete document")
check(all(d["doc_id"] != tmp for d in requests.get(f"{BASE}/documents").json()), "deleted document is gone")
check(post("/extract", doc_ids=[tmp]).json() == [], "deleted document has no indexed content")
upload("PowertrainControl_HLD.pdf")  # restore the sample library

check(len(requests.get(f"{BASE}/history").json()) >= 2, "history is logged")
check("question" in requests.get(f"{BASE}/export/csv").text, "csv export")
check(requests.get(f"{BASE}/export/json").json(), "json export")
check(requests.get(f"{BASE}/export/xml").status_code == 400, "bad export format rejected")
check(post("/upload").status_code in (400, 422), "upload without file rejected")

print("\nALL API TESTS PASSED ✅")
