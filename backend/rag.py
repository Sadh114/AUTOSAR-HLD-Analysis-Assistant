"""RAG query pipeline: retrieve grounded chunks, call an LLM, return a
cited, confidence-scored answer. Never raises to the caller -- always
returns a structured, user-safe response even if the LLM call fails."""
import re

import requests

from backend import config
from backend import embed_store

SYSTEM_PROMPT = (
    "You are an AUTOSAR High-Level Design (HLD) analysis assistant for automotive "
    "engineers. Answer ONLY using the provided context excerpts. If the context does "
    "not contain enough information to answer confidently, say so explicitly instead "
    "of guessing. Be precise, use engineering terminology, and keep answers concise. "
    "Never invent component names, interfaces, or signals that are not present in the "
    "provided context."
)


def _build_context_block(hits):
    parts = []
    for i, h in enumerate(hits, start=1):
        meta = h["metadata"]
        parts.append(
            f"[Source {i} | {meta.get('filename')} | Page {meta.get('page')} | "
            f"Section: {meta.get('section')}]\n{h['text']}"
        )
    return "\n\n".join(parts)


def _confidence_from_hits(hits) -> str:
    if not hits:
        return "No evidence found"
    distances = [h["distance"] for h in hits if h.get("distance") is not None]
    if not distances:
        return "Unknown"
    avg_dist = sum(distances) / len(distances)
    # cosine distance: lower is better (0 = identical)
    if avg_dist < 0.35:
        return "High"
    if avg_dist < 0.6:
        return "Medium"
    return "Low"


_NO_ANSWER_RE = re.compile(
    r"(does not|doesn't|do not|don't|did not) (contain|include|mention|provide|have|cover)"
    r"|no (relevant )?information|not (present|provided|mentioned|covered|available) in"
    r"|cannot (find|answer)|can't (find|answer)|unable to (find|answer)",
    re.IGNORECASE,
)


def _is_no_answer(answer_text: str) -> bool:
    """True when the model itself says the context can't answer the question."""
    # Only short replies count: a long, substantive answer may contain a phrase
    # like "does not mention" about one detail while still being grounded.
    return len(answer_text) < 350 and bool(_NO_ANSWER_RE.search(answer_text))


def _call_groq(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        # Reasoning models (gpt-oss) spend completion tokens on hidden reasoning;
        # a small cap can be used up before any answer text is produced.
        "max_tokens": 3000,
    }
    if "gpt-oss" in config.GROQ_MODEL:
        payload["reasoning_effort"] = "low"
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    content = (data["choices"][0]["message"].get("content") or "").strip()
    if not content:
        raise ValueError("empty completion")
    return content


def _call_gemini(prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 700},
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _call_llm(prompt: str):
    """Returns (answer_text, error_message_or_None)."""
    try:
        if config.LLM_PROVIDER == "gemini":
            if not config.GEMINI_API_KEY:
                return None, "GEMINI_API_KEY is not configured. Add it to your .env file."
            return _call_gemini(prompt), None
        else:
            if not config.GROQ_API_KEY:
                return None, "GROQ_API_KEY is not configured. Add it to your .env file."
            return _call_groq(prompt), None
    except requests.exceptions.Timeout:
        return None, "The AI service timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("error", {}).get("message", "")
        except Exception:
            detail = (e.response.text or "")[:200] if e.response is not None else ""
        status = e.response.status_code if e.response is not None else "?"
        return None, f"The AI service returned an error (HTTP {status}): {detail or e}"
    except requests.exceptions.RequestException as e:
        return None, f"The AI service could not be reached ({e.__class__.__name__}: {e})."
    except (KeyError, IndexError, ValueError):
        return None, "The AI service returned an unexpected response format."
    except Exception as e:  # last-resort safety net
        return None, f"Unexpected error while generating the answer: {e}"


def answer_question(question: str, doc_ids=None, top_k: int = None):
    """Full RAG flow. Always returns a dict, never raises."""
    try:
        hits = embed_store.query(question, doc_ids=doc_ids, top_k=top_k)
    except Exception as e:
        return {
            "answer": "Could not search the document knowledge base. Please re-upload your documents.",
            "citations": [],
            "confidence": "Error",
            "error": str(e),
        }

    if not hits:
        return {
            "answer": (
                "No relevant content was found in the selected document(s) for this "
                "question. Try rephrasing, or confirm the document was ingested successfully."
            ),
            "citations": [],
            "confidence": "No evidence found",
            "error": None,
        }

    context_block = _build_context_block(hits)
    prompt = (
        f"Context excerpts from AUTOSAR HLD document(s):\n\n{context_block}\n\n"
        f"Engineer's question: {question}\n\n"
        "Answer using only the context above, and reference source numbers like [Source 1] "
        "where relevant."
    )

    answer_text, error = _call_llm(prompt)
    confidence = _confidence_from_hits(hits)

    if error:
        # Graceful degradation: still return retrieved evidence even if the LLM failed.
        fallback = (
            "The AI model could not generate a written answer right now, but here is the "
            "most relevant retrieved evidence from your documents:\n\n" + context_block
        )
        return {
            "answer": fallback,
            "citations": _citations_from_hits(hits),
            "confidence": confidence,
            "error": error,
        }

    if _is_no_answer(answer_text):
        # The model found nothing relevant, so the retrieved chunks are noise:
        # don't present them as supporting citations.
        return {
            "answer": answer_text,
            "citations": [],
            "confidence": "No evidence found",
            "error": None,
        }

    return {
        "answer": answer_text,
        "citations": _citations_from_hits(hits),
        "confidence": confidence,
        "error": None,
    }


def _citations_from_hits(hits):
    citations = []
    for h in hits:
        meta = h["metadata"]
        citations.append(
            {
                "filename": meta.get("filename"),
                "page": meta.get("page"),
                "section": meta.get("section"),
                "excerpt": (h["text"][:220] + "...") if len(h["text"]) > 220 else h["text"],
            }
        )
    return citations
