"""Heuristic structured extraction of AUTOSAR architecture entities
(components, interfaces, ports, signals) from ingested chunk text."""
import json
import re

from backend import embed_store, rag

_ID = r"([A-Za-z][A-Za-z0-9_\-]{2,})"

PATTERNS = {
    "Component": [
        r"\b([A-Z][A-Za-z0-9_]{2,}(?:SWC|Swc|Component|Manager|Handler|Controller|Composition))\b",
        r"\b(?:Software Component|Application SWC|Atomic SWC|SWC|Composition|ComponentPrototype)s?[:\s]+" + _ID,
        r"\bComponent[:\s]+" + _ID,
    ],
    "Interface": [
        r"\b([A-Za-z0-9_]+(?:Interface|_If|_IF))\b",
        r"\b(?:Sender-?Receiver|Client-?Server|Mode-?Switch|NvData|Port)?\s?(?:Port)?Interface[:\s]+" + _ID,
        r"\bPortInterface[:\s]+" + _ID,
    ],
    "Port": [
        r"\b(?:P-?Port|R-?Port|PR-?Port)[:\s]+" + _ID,
        r"\b([A-Za-z0-9_]+_(?:PPort|RPort|PRPort|PPORT|RPORT))\b",
        r"\bPort[:\s]+" + _ID,
    ],
    "Signal": [
        r"\b(?:I-?Signal|Signal)[:\s]+" + _ID,
        r"\b([A-Za-z0-9_]+_Sig(?:nal)?)\b",
    ],
    "Runnable": [
        r"\bRunnable(?: Entity)?[:\s]+" + _ID,
        r"\b(Run_[A-Za-z0-9_]+|[A-Za-z0-9_]+_Runnable)\b",
    ],
}

# Words the loose "Keyword: <word>" patterns can capture from ordinary prose.
STOPWORDS = {
    "the", "and", "for", "that", "which", "with", "from", "this", "into", "between",
    "provides", "requires", "depends", "shall", "will", "are", "has", "have", "its",
    "to", "of", "is", "in", "on", "a", "an", "as", "by", "or", "not", "all", "each",
    "name", "type", "description", "overview", "design", "layer", "list", "table",
}


def _clean(name: str) -> str:
    return name.strip().strip(".,:;()[]").strip()


def extract_entities(doc_ids: list, use_llm: bool = False):
    """Scan all chunks for the given documents and return structured rows.

    use_llm=True additionally asks the LLM to list entities, which catches
    naming styles the regex patterns do not know. Falls back to regex-only
    results if the LLM call fails."""
    collection = embed_store.get_collection()
    where = {"doc_id": {"$in": doc_ids}} if len(doc_ids) > 1 else {"doc_id": doc_ids[0]}
    data = collection.get(where=where, include=["documents", "metadatas"])

    rows = []
    seen = set()
    # Chroma returns chunks in arbitrary order; ids are sequence-numbered, so
    # sorting by id walks each document front to back and the first occurrence
    # (the defining section) wins the dedup below.
    ordered = sorted(
        zip(data.get("ids", []), data.get("documents", []), data.get("metadatas", [])),
        key=lambda t: t[0],
    )
    for _, text, meta in ordered:
        for entity_type, patterns in PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    groups = [g for g in match.groups() if g]
                    name = _clean(groups[-1]) if groups else _clean(match.group(0))
                    if not name or len(name) < 3 or name.lower() in STOPWORDS:
                        continue
                    key = (entity_type, name.lower(), meta.get("filename"))
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "type": entity_type,
                            "name": name,
                            "filename": meta.get("filename"),
                            "page": meta.get("page"),
                            "section": meta.get("section"),
                        }
                    )
    if use_llm:
        for row in _llm_entities(ordered):
            key = (row["type"], row["name"].lower(), row["filename"])
            if key not in seen:
                seen.add(key)
                rows.append(row)
    rows.sort(key=lambda r: (r["type"], r["name"].lower()))
    return rows


LLM_TYPES = {"component": "Component", "interface": "Interface", "port": "Port",
             "signal": "Signal", "runnable": "Runnable"}
LLM_BATCH_CHARS = 6000

_LLM_PROMPT = (
    "List every AUTOSAR architecture entity named in the document text below. "
    "Types: component, interface, port, signal, runnable. Use ONLY names that appear "
    "verbatim in the text; do not invent any. Reply with a JSON array only, e.g. "
    '[{"type": "component", "name": "WiperCtrl_SWC"}].\n\nTEXT:\n'
)


def _parse_llm_json(text: str):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return []
    return [d for d in data if isinstance(d, dict)]


def _llm_entities(ordered):
    """ordered: (id, text, metadata) triples in document order -> entity rows."""
    # Group chunks per file, then send each file's text in size-limited batches.
    per_file = {}
    for _, text, meta in ordered:
        per_file.setdefault(meta.get("filename"), []).append((text, meta))

    rows = []
    for filename, items in per_file.items():
        batches, current, size = [], [], 0
        for text, meta in items:
            if current and size + len(text) > LLM_BATCH_CHARS:
                batches.append(current)
                current, size = [], 0
            current.append((text, meta))
            size += len(text)
        if current:
            batches.append(current)

        for batch in batches:
            joined = "\n\n".join(t for t, _ in batch)
            answer, error = rag._call_llm(_LLM_PROMPT + joined)
            if error or not answer:
                continue
            for item in _parse_llm_json(answer):
                etype = LLM_TYPES.get(str(item.get("type", "")).lower())
                name = _clean(str(item.get("name", "")))
                # Hallucination guard: the name must literally occur in the batch text.
                if not etype or len(name) < 3 or name.lower() in STOPWORDS or name not in joined:
                    continue
                owner = next((m for t, m in batch if name in t), batch[0][1])
                rows.append(
                    {
                        "type": etype,
                        "name": name,
                        "filename": filename,
                        "page": owner.get("page"),
                        "section": owner.get("section"),
                    }
                )
    return rows
