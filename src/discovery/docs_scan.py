"""
docs_scan.py - Documentation file scanning and correlation.

Searches documentation files for mentions of exported functions
and links them back to the exports.
"""

from pathlib import Path
from typing import Dict, List

from schema import ExportedFunc


def scan_docs_for_exports(
    docs_root: Path, exports: List[ExportedFunc], max_hits: int = 2
) -> Dict[str, List[str]]:
    """Scan documentation directory for mentions of exported functions.
    
    Args:
        docs_root: Root directory to search for documentation
        exports: List of exported functions to search for
        max_hits: Maximum number of documentation files to link per export
        
    Returns:
        Dict mapping export name to list of documentation file paths
    """
    results: Dict[str, List[str]] = {}

    doc_extensions = {".md", ".txt", ".rst", ".adoc", ".htm", ".html"}
    doc_files = [
        p
        for p in docs_root.rglob("*")
        if p.is_file() and p.suffix.lower() in doc_extensions
    ]

    for exp in exports:
        hits = []

        for doc_file in doc_files:
            if len(hits) >= max_hits:
                break

            try:
                content = doc_file.read_text(encoding="utf-8", errors="replace")
                if exp.name in content:
                    hits.append(str(doc_file))
            except Exception:
                pass

        if hits:
            results[exp.name] = hits

    return results
