"""Simple two-document comparison: matches sections by title similarity
and flags likely inconsistencies (added/removed/modified sections)."""
import difflib

from backend import embed_store, extraction


def _sections_for_doc(doc_id: str):
    collection = embed_store.get_collection()
    data = collection.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
    # Chunk ids are sequence-numbered: sort so section text is in document order.
    ordered = sorted(
        zip(data.get("ids", []), data.get("documents", []), data.get("metadatas", [])),
        key=lambda t: t[0],
    )
    sections = {}
    for _, text, meta in ordered:
        title = meta.get("section", "Untitled")
        sections.setdefault(title, {"page": meta.get("page"), "text": ""})
        sections[title]["text"] += ("\n" + text)
    return sections


def _line_changes(text_a: str, text_b: str, limit: int = 4) -> str:
    """Short human-readable summary of lines added/removed between two texts."""
    lines_a = [l.strip() for l in text_a.splitlines() if l.strip()]
    lines_b = [l.strip() for l in text_b.splitlines() if l.strip()]
    removed = [l for l in lines_a if l not in lines_b]
    added = [l for l in lines_b if l not in lines_a]
    parts = []
    if added:
        parts.append("Added: " + "; ".join(l[:90] for l in added[:limit]))
    if removed:
        parts.append("Removed: " + "; ".join(l[:90] for l in removed[:limit]))
    return " ".join(parts)


def _entity_findings(doc_id_a: str, filename_a: str, doc_id_b: str, filename_b: str):
    """Architecture-level diff: components/interfaces/ports/signals added or removed."""
    def names(doc_id):
        return {(r["type"], r["name"]) for r in extraction.extract_entities([doc_id])}

    ents_a, ents_b = names(doc_id_a), names(doc_id_b)
    findings = []
    for etype, name in sorted(ents_b - ents_a):
        findings.append(
            {
                "status": "Entity added",
                "section": f"{etype}: {name}",
                "detail": f"{etype} '{name}' is present in '{filename_b}' but not in '{filename_a}'.",
            }
        )
    for etype, name in sorted(ents_a - ents_b):
        findings.append(
            {
                "status": "Entity removed",
                "section": f"{etype}: {name}",
                "detail": f"{etype} '{name}' is present in '{filename_a}' but not in '{filename_b}'.",
            }
        )
    return findings


def compare_documents(doc_id_a: str, filename_a: str, doc_id_b: str, filename_b: str):
    sections_a = _sections_for_doc(doc_id_a)
    sections_b = _sections_for_doc(doc_id_b)

    titles_a = list(sections_a.keys())
    titles_b = list(sections_b.keys())

    matched_b = set()
    findings = []

    for title_a in titles_a:
        best_match, best_ratio = None, 0.0
        for title_b in titles_b:
            if title_b in matched_b:
                continue
            ratio = difflib.SequenceMatcher(None, title_a.lower(), title_b.lower()).ratio()
            if ratio > best_ratio:
                best_ratio, best_match = ratio, title_b

        if best_match and best_ratio > 0.55:
            matched_b.add(best_match)
            text_ratio = difflib.SequenceMatcher(
                None, sections_a[title_a]["text"], sections_b[best_match]["text"]
            ).ratio()
            if text_ratio < 0.999:
                findings.append(
                    {
                        "status": "Modified",
                        "section": title_a,
                        "detail": (
                            f"Section content differs between '{filename_a}' "
                            f"(p.{sections_a[title_a]['page']}) and '{filename_b}' "
                            f"(p.{sections_b[best_match]['page']}) "
                            f"(similarity {text_ratio:.0%}). "
                            + _line_changes(
                                sections_a[title_a]["text"], sections_b[best_match]["text"]
                            )
                        ),
                    }
                )
        else:
            findings.append(
                {
                    "status": "Only in A",
                    "section": title_a,
                    "detail": (
                        f"Section '{title_a}' appears in '{filename_a}' "
                        f"(p.{sections_a[title_a]['page']}) but has no clear match in '{filename_b}'."
                    ),
                }
            )

    for title_b in titles_b:
        if title_b not in matched_b:
            findings.append(
                {
                    "status": "Only in B",
                    "section": title_b,
                    "detail": (
                        f"Section '{title_b}' appears in '{filename_b}' "
                        f"(p.{sections_b[title_b]['page']}) but has no clear match in '{filename_a}'."
                    ),
                }
            )

    findings.extend(_entity_findings(doc_id_a, filename_a, doc_id_b, filename_b))
    return findings
