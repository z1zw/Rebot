"""Context compression strategy constants."""

from __future__ import annotations

COMPRESS_NONE = "none"
COMPRESS_RECENT_ONLY = "recent_only"
COMPRESS_HEAD_TAIL = "head_tail"
COMPRESS_SUMMARY_STUB = "summary_stub"
COMPRESS_SUMMARY_XML = "summary_xml"
COMPRESS_GRAPH_SPARSE = "graph_sparse"

COMPRESS_STRATEGIES = (
    COMPRESS_NONE,
    COMPRESS_RECENT_ONLY,
    COMPRESS_HEAD_TAIL,
    COMPRESS_SUMMARY_STUB,
    COMPRESS_SUMMARY_XML,
    COMPRESS_GRAPH_SPARSE,
)


def normalize_compress_type(value: str | None) -> str:
    strategy = (value or COMPRESS_SUMMARY_STUB).lower().strip()
    if strategy in {"no_compress", "none"}:
        return COMPRESS_NONE
    if strategy in {"summary", "auto", "compress"}:
        return COMPRESS_SUMMARY_STUB
    if strategy in {"summary_xml", "xml", "code_digest", "xml_digest"}:
        return COMPRESS_SUMMARY_XML
    if strategy in {"graph_sparse", "graph", "sparse", "graph_matrix"}:
        return COMPRESS_GRAPH_SPARSE
    if strategy in {"tail", "recent"}:
        return COMPRESS_RECENT_ONLY
    if strategy in {"head_tail", "window"}:
        return COMPRESS_HEAD_TAIL
    if strategy in COMPRESS_STRATEGIES:
        return strategy
    return COMPRESS_SUMMARY_STUB
