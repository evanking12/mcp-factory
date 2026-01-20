"""
schema.py - Data models and output writers for invocable records.

Defines the core data structures for representing exported functions and
provides writers for CSV, JSON, and Markdown output formats.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ExportedFunc:
    """Represents an exported function from a DLL."""
    name: str
    ordinal: Optional[int] = None
    hint: Optional[str] = None
    rva: Optional[str] = None
    forwarded_to: Optional[str] = None
    demangled: Optional[str] = None


@dataclass
class Invocable:
    """Unified record for any callable (export, COM object, CLI command, etc)."""
    name: str
    source_type: str  # "export" | "com" | "cli" | "dotnet"
    ordinal: Optional[int] = None
    hint: Optional[str] = None
    rva: Optional[str] = None
    return_type: Optional[str] = None
    parameters: Optional[str] = None
    signature: Optional[str] = None
    doc_comment: Optional[str] = None
    header_file: Optional[str] = None
    header_line: Optional[int] = None
    demangled: Optional[str] = None
    doc_files: Optional[str] = None  # semicolon-separated
    confidence: str = "medium"  # "low", "medium", "high"
    confidence_reasons: Optional[List[str]] = None
    is_forwarded: bool = False
    publisher: Optional[str] = None
    is_signed: bool = False


@dataclass
class MatchInfo:
    """Information extracted from header file about a function."""
    function: str
    return_type: str
    parameters: str
    doc_comment: str
    header_file: str
    line: int
    prototype: str


def write_csv(
    path: Path,
    exports: List[ExportedFunc],
    matches: Dict[str, MatchInfo],
    doc_hits: Dict[str, List[str]],
    is_signed: bool = False,
    publisher: str = None
) -> None:
    """Write exports to CSV file with matched headers and documentation."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Function', 'Ordinal', 'Hint', 'RVA', 'ForwardedTo',
            'ReturnType', 'Parameters', 'Signature', 'DocComment',
            'HeaderFile', 'Line', 'Demangled', 'DocFiles', 'IsSigned', 'Publisher'
        ])

        for exp in exports:
            mi = matches.get(exp.name)
            docs = doc_hits.get(exp.name, [])

            writer.writerow([
                exp.name,
                exp.ordinal or '',
                exp.hint or '',
                exp.rva or '',
                exp.forwarded_to or '',
                mi.return_type if mi else '',
                mi.parameters if mi else '',
                mi.prototype if mi else '',
                mi.doc_comment if mi else '',
                mi.header_file if mi else '',
                mi.line if mi else '',
                exp.demangled or '',
                ';'.join(docs) if docs else '',
                'Yes' if is_signed else 'No',
                publisher or ''
            ])


def write_json(
    path: Path,
    exports: List[ExportedFunc],
    matches: Dict[str, MatchInfo],
    doc_hits: Dict[str, List[str]]
) -> None:
    """Write exports to JSON file (for MCP schema generation)."""
    import json

    path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for exp in exports:
        mi = matches.get(exp.name)
        docs = doc_hits.get(exp.name, [])

        record = {
            'name': exp.name,
            'ordinal': exp.ordinal,
            'hint': exp.hint,
            'rva': exp.rva,
            'forwarded_to': exp.forwarded_to,
            'demangled': exp.demangled,
        }

        if mi:
            record.update({
                'return_type': mi.return_type,
                'parameters': mi.parameters,
                'signature': mi.prototype,
                'doc_comment': mi.doc_comment,
                'header_file': str(mi.header_file),
                'header_line': mi.line,
            })

        if docs:
            record['doc_files'] = docs

        records.append(record)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)


def write_markdown(
    path: Path,
    dll_path: Path,
    exports: List[ExportedFunc],
    matches: Dict[str, MatchInfo],
    doc_hits: Dict[str, List[str]]
) -> None:
    """Write exports to Markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# API Report: {dll_path.name}\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total Exports: {len(exports)}\n\n")

        for exp in exports:
            mi = matches.get(exp.name)
            docs = doc_hits.get(exp.name, [])

            f.write(f"## {exp.name}\n\n")

            if exp.ordinal:
                f.write(f"**Ordinal:** {exp.ordinal}\n\n")

            if mi:
                f.write(f"**Signature:** `{mi.prototype}`\n\n")
                f.write(f"**Header:** `{mi.header_file}:{mi.line}`\n\n")

                if mi.doc_comment:
                    f.write(f"**Documentation:**\n\n{mi.doc_comment}\n\n")

                if docs:
                    f.write(f"**Referenced in:**\n\n")
                    for doc in docs:
                        f.write(f"- `{doc}`\n")
                    f.write("\n")

            if exp.demangled and exp.demangled != exp.name:
                f.write(f"**Demangled:** `{exp.demangled}`\n\n")

            f.write("---\n\n")


def write_tier_summary(path: Path, entries: List[str]) -> None:
    """Write summary of all tiers generated."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write("# Tier Summary\n\n")
        f.write("Tiers successfully generated:\n\n")
        for entry in entries:
            f.write(f"- {entry}\n")
        f.write("\n")
        f.write("See individual tier files for detailed analysis.\n")
