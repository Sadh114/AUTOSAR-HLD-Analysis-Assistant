"""Thin wrapper around the FastAPI backend. Every function catches
network errors and returns a (success, data_or_message) tuple so the
Streamlit UI never crashes on a backend hiccup."""
import requests

from backend import config

BASE_URL = config.BACKEND_URL
TIMEOUT = 60


def _get(path, **kwargs):
    try:
        r = requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return True, r.json()
    except requests.exceptions.ConnectionError:
        return False, "Cannot reach the backend server. Is it running?"
    except requests.exceptions.Timeout:
        return False, "The backend took too long to respond."
    except requests.exceptions.HTTPError as e:
        return False, _extract_detail(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"


def _post(path, **kwargs):
    try:
        r = requests.post(f"{BASE_URL}{path}", timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return True, r.json()
    except requests.exceptions.ConnectionError:
        return False, "Cannot reach the backend server. Is it running?"
    except requests.exceptions.Timeout:
        return False, "The backend took too long to respond."
    except requests.exceptions.HTTPError as e:
        return False, _extract_detail(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"


def _extract_detail(e):
    try:
        return e.response.json().get("detail", str(e))
    except Exception:
        return str(e)


def health():
    return _get("/health")


def upload_pdf(filename, file_bytes):
    try:
        files = {"file": (filename, file_bytes, "application/pdf")}
        r = requests.post(f"{BASE_URL}/upload", files=files, timeout=180)
        r.raise_for_status()
        return True, r.json()
    except requests.exceptions.ConnectionError:
        return False, "Cannot reach the backend server. Is it running?"
    except requests.exceptions.Timeout:
        return False, "Uploading/processing the PDF took too long. Try a smaller file."
    except requests.exceptions.HTTPError as e:
        return False, _extract_detail(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"


def list_documents():
    return _get("/documents")


def delete_document(doc_id):
    try:
        r = requests.delete(f"{BASE_URL}/documents/{doc_id}", timeout=TIMEOUT)
        r.raise_for_status()
        return True, r.json()
    except Exception as e:
        return False, str(e)


def ask(question, doc_ids=None):
    return _post("/ask", json={"question": question, "doc_ids": doc_ids})


def extract_entities(doc_ids, use_llm=False):
    return _post("/extract", json={"doc_ids": doc_ids, "use_llm": use_llm})


def compare_documents(doc_id_a, filename_a, doc_id_b, filename_b):
    return _post(
        "/compare",
        json={
            "doc_id_a": doc_id_a,
            "filename_a": filename_a,
            "doc_id_b": doc_id_b,
            "filename_b": filename_b,
        },
    )


def get_history(limit=200):
    return _get("/history", params={"limit": limit})


def export_url(fmt):
    return f"{BASE_URL}/export/{fmt}"
