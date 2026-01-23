#!/usr/bin/env python3
"""
csv_script.py - Advanced DLL Export Analyzer

Tiered pipeline (best -> fallback):
1) Exports + headers + docs scan
2) Exports + headers
3) Exports + demangle
4) Exports only
5) DLL metadata only

This script runs dumpbin /exports on a specified DLL and generates:
- Raw dumpbin output text file
- CSV file with parsed export information including prototypes from headers
- Markdown report with documentation
- Tier summary showing which analysis levels succeeded

Usage:
    python csv_script.py --dll path/to/library.dll --headers include_dir --docs docs_dir
    python csv_script.py --dll path/to/library.dll --out output_dir
    python csv_script.py --exports-raw existing_raw.txt --headers include_dir

Requirements:
    - Must be run from Visual Studio x64 Native Tools Command Prompt
    - dumpbin.exe must be available in PATH (or specify with --dumpbin)
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Regex for parsing dumpbin export lines
# Format: ordinal hint RVA name [= forwarded_to]
# Example: 1    0 00077410 ZDICT_addEntropyTablesFromBuffer = ZDICT_addEntropyTablesFromBuffer
EXPORT_LINE_RE = re.compile(
    r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]{8}|--------)\s+([^\s=]+)(?:\s*=\s*(\S+))?"
)


def make_proto_regex(func_name: str) -> re.Pattern:
    """Create regex to find function prototype in header files."""
    escaped = re.escape(func_name)
    return re.compile(rf"(^|[^A-Za-z0-9_]){escaped}\s*\(", re.MULTILINE)


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
class MatchInfo:
    """Information extracted from header file about a function."""
    function: str
    return_type: str
    parameters: str
    doc_comment: str
    header_file: str
    line: int
    prototype: str


def run_cmd(cmd: List[str]) -> Tuple[int, str]:
    """Run a command and return (returncode, combined_output)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return proc.returncode, out
    except FileNotFoundError as exc:
        return 1, str(exc)
    except subprocess.TimeoutExpired:
        return 1, "Command timed out"


def check_tool_available(tool_path: str) -> bool:
    """Check if a tool is available and executable."""
    try:
        result = subprocess.run(
            [tool_path, "/?"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def parse_dumpbin_exports(text: str) -> List[ExportedFunc]:
    """
    Parse dumpbin /exports output and extract export information.
    
    The dumpbin output format:
        ordinal hint RVA      name [= forwarded_to]
              1    0 00077410 FunctionName
              2    1 00078A70 FunctionName2 = OtherDll.Function
              3    A -------- ForwardedFunc = KERNEL32.GetProcAddress
    
    Returns a list of ExportedFunc with ordinal, hint, RVA, name, and optional forwarding.
    """
    lines = text.splitlines()
    exports: List[ExportedFunc] = []
    in_table = False
    
    for ln in lines:
        # Detect start of export table
        if "ordinal" in ln.lower() and "name" in ln.lower():
            in_table = True
            continue
        
        if not in_table:
            continue
        
        # Detect end of export table (Summary section)
        if "summary" in ln.lower():
            break
        
        # Skip empty lines
        if not ln.strip():
            continue
        
        # Try to parse export line
        m = EXPORT_LINE_RE.match(ln)
        if not m:
            # Line doesn't match export format - might be end of table
            if exports:  # Only break if we've found at least some exports
                continue  # Keep trying in case of malformed lines
            continue
        
        try:
            ordinal = int(m.group(1))
            hint = m.group(2)  # Hex string (can be single digit)
            rva = m.group(3)   # 8 hex digits or "--------"
            name = m.group(4)
            forwarded_to = m.group(5) if m.group(5) else None
            
            if not name or name == "":
                continue
            
            exports.append(ExportedFunc(
                name=name,
                ordinal=ordinal,
                hint=hint,
                rva=rva,
                forwarded_to=forwarded_to
            ))
        except (ValueError, IndexError) as e:
            # Skip malformed lines
            continue
    
    # Deduplicate by function name
    seen = set()
    uniq = []
    for e in exports:
        if e.name not in seen:
            uniq.append(e)
            seen.add(e.name)
    
    # Debug output if no exports found
    if not uniq:
        print("ERROR: No exports parsed from dumpbin output", file=sys.stderr)
        print("First 50 lines of raw output for debugging:", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        for i, line in enumerate(lines[:50], 1):
            print(f"{i:3d}: {line}", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
    
    return uniq


def demangle_with_undname(exports: List[ExportedFunc], undname_path: str) -> bool:
    """
    Demangle C++ mangled names using undname.exe.
    
    Returns True if any names were successfully demangled.
    """
    ok = False
    for e in exports:
        if not e.name.startswith("?"):
            continue
        rc, out = run_cmd([undname_path, e.name])
        if rc == 0:
            for line in out.splitlines():
                line = line.strip()
                if line:
                    e.demangled = line
                    ok = True
                    break
    return ok


def iter_header_files(root: Path) -> List[Path]:
    """Find all header files in the given directory tree."""
    exts = {".h", ".hpp", ".hh", ".hxx", ".inl"}
    files = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return files


def build_comment_spans(text: str) -> Tuple[List[Tuple[int, int]], List[int]]:
    """Build a list of (start, end) character indices for all comments in the text."""
    spans: List[Tuple[int, int]] = []
    i = 0
    n = len(text)
    
    while i < n:
        # Single-line comment
        if text.startswith("//", i):
            start = i
            i = text.find("\n", i)
            if i == -1:
                spans.append((start, n))
                break
            spans.append((start, i))
            continue
        
        # Multi-line comment
        if text.startswith("/*", i):
            start = i
            end = text.find("*/", i + 2)
            if end == -1:
                spans.append((start, n))
                break
            spans.append((start, end + 2))
            i = end + 2
            continue
        
        i += 1
    
    starts = [s for s, _ in spans]
    return spans, starts


def in_comment_spans(idx: int, spans: List[Tuple[int, int]], starts: List[int]) -> bool:
    """Check if the given index is inside a comment span."""
    if not spans:
        return False
    pos = bisect_right(starts, idx) - 1
    if pos < 0:
        return False
    s, e = spans[pos]
    return s <= idx < e


def extract_doc_comment_above(text: str, start_index: int) -> str:
    """Extract documentation comment appearing immediately before the given index."""
    before = text[:start_index]
    lines = before.splitlines()
    if not lines:
        return ""
    if not lines[-1].strip():
        return ""

    i = len(lines) - 1
    line = lines[i].lstrip()
    
    # Doxygen-style single-line comments (/// or //!)
    if line.startswith("///") or line.startswith("//!"):
        block = []
        while i >= 0:
            l = lines[i].lstrip()
            if l.startswith("///") or l.startswith("//!"):
                block.append(l[3:].lstrip())
                i -= 1
            else:
                break
        block.reverse()
        return "\n".join(block).strip()

    # Doxygen-style multi-line comments (/** or /*!)
    if "*/" in lines[i]:
        block_lines = []
        while i >= 0:
            block_lines.append(lines[i])
            if "/*" in lines[i]:
                break
            i -= 1
        block_lines.reverse()
        opening = block_lines[0].lstrip()
        if not (opening.startswith("/**") or opening.startswith("/*!")):
            return ""
        block_text = "\n".join(block_lines)
        block_text = re.sub(r"^\s*/\*\*?\s?", "", block_text)
        block_text = re.sub(r"\s?\*/\s*$", "", block_text)
        cleaned = []
        for l in block_text.splitlines():
            l = re.sub(r"^\s*\*\s?", "", l)
            cleaned.append(l.rstrip())
        return "\n".join(cleaned).strip()

    return ""


def extract_inline_comment(line_text: str) -> str:
    """Extract inline comment from a line of code."""
    idx = line_text.find("//")
    if idx != -1:
        return line_text[idx + 2:].strip()
    idx = line_text.find("/*")
    if idx != -1:
        end = line_text.find("*/", idx + 2)
        if end != -1:
            return line_text[idx + 2:end].strip()
    return ""


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def clean_return_type(text: str) -> str:
    """Clean up return type by removing storage class specifiers and calling conventions."""
    if not text:
        return ""
    text = re.sub(r"__declspec\s*\([^)]*\)", "", text)
    text = re.sub(r"__attribute__\s*\(\([^)]*\)\)", "", text)
    text = re.sub(r"\b(?:extern|static|inline|constexpr|consteval|constinit|friend)\b", "", text)
    text = re.sub(r"\b(?:__cdecl|__stdcall|__fastcall|__vectorcall|__thiscall)\b", "", text)
    text = re.sub(r"\b[A-Z][A-Z0-9_]*_(?:API|EXPORT|IMPORT|STATIC_API)\b", "", text)
    text = normalize_whitespace(text)
    return text


def find_prototype_in_header(file_path: Path, export_name: str) -> Optional[MatchInfo]:
    """
    Find function prototype in a header file.
    
    Searches for the function name and extracts:
    - Return type
    - Parameters
    - Documentation comment
    - Line number
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    rx = make_proto_regex(export_name)
    comment_spans, comment_starts = build_comment_spans(text)

    for m in rx.finditer(text):
        name_index = m.start(0)
        if in_comment_spans(name_index, comment_spans, comment_starts):
            continue

        line_start = text.rfind("\n", 0, name_index) + 1
        line_no = text.count("\n", 0, line_start) + 1

        # Skip preprocessor directives
        line_prefix = text[line_start:name_index].lstrip()
        if line_prefix.startswith("#"):
            continue

        # Find end of declaration (semicolon or opening brace)
        end_idx = None
        depth = 0
        i = line_start
        n = len(text)
        while i < n:
            if in_comment_spans(i, comment_spans, comment_starts):
                i += 1
                continue
            ch = text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif ch in (";", "{") and depth == 0:
                end_idx = i
                break
            i += 1

        if end_idx is None:
            continue

        proto = text[line_start:end_idx].strip()
        if f"{export_name}(" not in proto and f"{export_name} (" not in proto:
            continue

        # Extract inline comment
        line_end = text.find("\n", end_idx)
        if line_end == -1:
            line_end = len(text)
        inline_comment = extract_inline_comment(text[end_idx:line_end])
        doc = inline_comment or extract_doc_comment_above(text, line_start)

        # Parse prototype
        proto_one = normalize_whitespace(proto)
        idx = proto_one.find(export_name)
        if idx <= 0:
            continue
        before_name = proto_one[:idx].strip()
        after_name = proto_one[idx + len(export_name):].lstrip()

        # Extract parameters
        if not after_name.startswith("("):
            params = ""
        else:
            depth = 0
            params_chars = []
            for ch in after_name:
                if ch == "(":
                    depth += 1
                    if depth == 1:
                        continue
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
                if depth >= 1:
                    params_chars.append(ch)
            params = normalize_whitespace("".join(params_chars))

        return_type = clean_return_type(before_name)

        return MatchInfo(
            function=export_name,
            return_type=return_type,
            parameters=params,
            doc_comment=doc.strip(),
            header_file=str(file_path),
            line=line_no,
            prototype=proto_one,
        )

    return None


def build_signature(mi: MatchInfo) -> str:
    """Build a complete function signature from match info."""
    if mi.return_type:
        return f"{mi.return_type} {mi.function}({mi.parameters})".strip()
    return f"{mi.function}({mi.parameters})".strip()


def scan_docs_for_exports(docs_root: Path, exports: List[ExportedFunc], max_hits: int) -> Dict[str, List[str]]:
    """
    Scan documentation files for mentions of exported functions.
    
    Returns a dictionary mapping function names to lists of documentation file paths.
    """
    exts = {".md", ".txt", ".rst", ".adoc", ".dox"}
    files = [p for p in docs_root.rglob("*") if p.is_file() and p.suffix.lower() in exts]
    if not files:
        return {}

    file_texts: Dict[Path, str] = {}
    for p in files:
        try:
            file_texts[p] = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

    hits: Dict[str, List[str]] = {}
    for e in exports:
        name_re = re.compile(rf"\b{re.escape(e.name)}\b")
        for p, text in file_texts.items():
            if name_re.search(text):
                hits.setdefault(e.name, []).append(str(p))
                if len(hits[e.name]) >= max_hits:
                    break
    return hits


def write_csv(path: Path, exports: List[ExportedFunc], matches: Dict[str, MatchInfo], doc_hits: Dict[str, List[str]]) -> None:
    """Write export information to CSV file."""
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "Function", "Ordinal", "Hint", "RVA", "ForwardedTo",
            "ReturnType", "Parameters", "Signature",
            "DocComment", "HeaderFile", "Line", "Demangled", "DocFiles"
        ])
        for e in exports:
            mi = matches.get(e.name)
            if mi:
                signature = build_signature(mi)
                doc_one_line = normalize_whitespace(mi.doc_comment)
                doc_files = ";".join(doc_hits.get(e.name, []))
                w.writerow([
                    mi.function, e.ordinal or "", e.hint or "", e.rva or "", e.forwarded_to or "",
                    mi.return_type, mi.parameters,
                    signature, doc_one_line, mi.header_file, mi.line,
                    e.demangled or "", doc_files
                ])
            else:
                doc_files = ";".join(doc_hits.get(e.name, []))
                w.writerow([
                    e.name, e.ordinal or "", e.hint or "", e.rva or "", e.forwarded_to or "",
                    "", "", e.name, "", "", "",
                    e.demangled or "", doc_files
                ])


def write_report(path: Path, dll_path: Path, exports: List[ExportedFunc], matches: Dict[str, MatchInfo], doc_hits: Dict[str, List[str]]) -> None:
    """Write a markdown report with detailed API information."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# API Report: {dll_path.name}\n\n")
        f.write(f"Generated: {now}\n\n")
        f.write(f"Total Exports: {len(exports)}\n\n")
        
        for e in exports:
            f.write(f"## {e.name}\n\n")
            if e.ordinal is not None:
                f.write(f"**Ordinal:** {e.ordinal}\n\n")
            
            mi = matches.get(e.name)
            if mi:
                signature = build_signature(mi)
                f.write(f"**Signature:** `{signature}`\n\n")
                f.write(f"**Header:** `{mi.header_file}:{mi.line}`\n\n")
                if mi.doc_comment:
                    f.write("**Documentation:**\n\n")
                    f.write(mi.doc_comment.strip() + "\n\n")
                else:
                    f.write("**Documentation:** (none)\n\n")
            else:
                f.write("**Signature:** (not found in headers)\n\n")
                f.write("**Documentation:** (none)\n\n")
            
            if e.demangled:
                f.write(f"**Demangled:** `{e.demangled}`\n\n")
            
            if doc_hits.get(e.name):
                f.write("**Referenced in:**\n\n")
                for p in doc_hits[e.name]:
                    f.write(f"- `{p}`\n")
                f.write("\n")
            
            f.write("---\n\n")


def write_json(
    path: Path,
    dll_path: Path,
    exports: List[ExportedFunc],
    matches: Dict[str, MatchInfo],
    doc_hits: Dict[str, List[str]],
    tier: int,
    is_signed: bool = False,
    publisher: Optional[str] = None,
    architecture: str = "unknown"
) -> None:
    """
    Write discovery results to JSON using stable schema v2.0.0.
    
    This schema is designed to be forward-compatible:
    - New fields can be added to 'metadata' object without breaking consumers
    - 'invocables[].metadata' is extensible for future data
    - Core required fields will never be removed or renamed
    """
    
    # Calculate statistics
    total = len(exports)
    high_conf = sum(1 for e in exports if e.name in matches and matches[e.name].doc_comment)
    medium_conf = sum(1 for e in exports if e.name in matches and not matches[e.name].doc_comment)
    low_conf = total - high_conf - medium_conf
    match_rate = len([e for e in exports if e.name in matches]) / total if total > 0 else 0
    documented = sum(1 for e in exports if e.name in matches and matches[e.name].doc_comment)
    
    # Build invocables array
    invocables = []
    for e in exports:
        mi = matches.get(e.name)
        
        # Determine confidence
        if mi and mi.doc_comment:
            confidence = "high"
        elif mi:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Confidence factors
        confidence_factors = {
            "has_signature": mi is not None,
            "has_documentation": mi is not None and bool(mi.doc_comment),
            "has_parameters": mi is not None and bool(mi.parameters),
            "has_return_type": mi is not None and bool(mi.return_type),
            "is_forwarded": bool(e.forwarded_to),
            "is_ordinal_only": e.name.startswith("Ordinal") if e.name else False
        }
        
        # Signature details
        signature = {
            "return_type": mi.return_type if mi else None,
            "parameters": mi.parameters if mi else None,
            "calling_convention": None,  # Future enhancement
            "full_prototype": build_signature(mi) if mi else None
        }
        
        # Documentation
        documentation = {
            "summary": normalize_whitespace(mi.doc_comment)[:200] if mi and mi.doc_comment else None,
            "description": normalize_whitespace(mi.doc_comment) if mi and mi.doc_comment else None,
            "source_file": mi.header_file if mi else None,
            "source_line": mi.line if mi else None
        }
        
        # Evidence/provenance
        evidence = {
            "discovered_by": "exports.py",
            "header_file": mi.header_file if mi else None,
            "forwarded_to": e.forwarded_to,
            "demangled_name": e.demangled
        }
        
        # Build invocable object
        invocable = {
            "name": e.name,
            "kind": "dll_export",
            "ordinal": e.ordinal,
            "rva": e.rva,
            "confidence": confidence,
            "confidence_factors": confidence_factors,
            "signature": signature,
            "documentation": documentation,
            "evidence": evidence,
            "metadata": {}  # Extensible for future data
        }
        
        invocables.append(invocable)
    
    # Build full output
    output = {
        "schema_version": "2.0.0",
        "metadata": {
            "target_path": str(dll_path.absolute()),
            "target_name": dll_path.name,
            "target_type": "dll" if dll_path.suffix.lower() == ".dll" else "exe" if dll_path.suffix.lower() == ".exe" else "unknown",
            "architecture": architecture,
            "file_size_bytes": dll_path.stat().st_size if dll_path.exists() else 0,
            "is_signed": is_signed,
            "publisher": publisher,
            "analysis_timestamp": datetime.now().isoformat(),
            "pipeline_version": "1.0.0",
            "tier": tier,
            "schema_version": "2.0.0"
        },
        "invocables": invocables,
        "pipeline_results": {
            "modules_run": ["classify", "pe_parse", "exports", "headers_scan", "schema", "csv_script"],
            "modules_passed": ["exports", "schema", "csv_script"],
            "modules_warned": [] if matches else ["headers_scan"],
            "modules_failed": [],
            "total_duration_ms": 0  # TODO: track actual duration
        },
        "statistics": {
            "total_invocables": total,
            "high_confidence_count": high_conf,
            "medium_confidence_count": medium_conf,
            "low_confidence_count": low_conf,
            "signature_match_rate": match_rate,
            "documented_count": documented
        }
    }
    
    # Write with pretty formatting
    with path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def write_tier_summary(path: Path, entries: List[str]) -> None:
    """Write a summary of which tiers succeeded."""
    with path.open("w", encoding="utf-8") as f:
        f.write("# Tier Summary\n\n")
        for line in entries:
            f.write(line + "\n")


def generate_confidence_summary(
    exports: List,  # List[ExportedFunc]
    matches: Dict,
    out_dir: Path,
    dll_path: Path,
    tag: str = ""
) -> str:
    """Generate human-readable confidence summary and write to file."""
    
    # Score all exports based on their characteristics
    confidence_data = {'high': [], 'medium': [], 'low': []}
    reason_counts = {}
    
    for exp in exports:
        # Determine confidence level based on available information
        score = 0
        reasons = []
        
        # Base score: has export
        score += 2
        reasons.append('exported from DLL')
        
        # Header match: +3
        if exp.name in matches:
            score += 3
            reasons.append('matched to header prototype')
        
        # Demangled: +1
        if exp.demangled:
            score += 1
            reasons.append('demangled C++ name')
        
        # Forwarded: +1
        if exp.forwarded_to and exp.forwarded_to != exp.name:
            score += 1
            reasons.append('forwarded reference')
        
        # Assign confidence level
        if score >= 6:
            confidence = 'high'
        elif score >= 4:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        confidence_data[confidence].append({
            'name': exp.name,
            'reasons': reasons
        })
        
        # Track reason frequency
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    
    # Calculate percentages
    total = len(exports)
    high_pct = (len(confidence_data['high']) / total * 100) if total > 0 else 0
    med_pct = (len(confidence_data['medium']) / total * 100) if total > 0 else 0
    low_pct = (len(confidence_data['low']) / total * 100) if total > 0 else 0
    
    # ANSI color codes for terminal output
    RED = '\033[91m'      # Bright red
    YELLOW = '\033[93m'   # Bright yellow
    GREEN = '\033[92m'    # Bright green
    BLUE = '\033[94m'     # Bright blue
    RESET = '\033[0m'     # Reset to default
    
    # Generate summary text
    lines = [
        "CONFIDENCE ANALYSIS SUMMARY",
        "=" * 60,
        "",
        f"DLL: {dll_path.name}",
        f"Total Exports: {total}",
        f"Analysis Date: {datetime.now().isoformat()}",
        "",
        "CONFIDENCE BREAKDOWN",
        "-" * 60,
        f"{RED}LOW     Confidence: {len(confidence_data['low']):3d} exports ({low_pct:5.1f}%){RESET}",
        f"{YELLOW}MEDIUM  Confidence: {len(confidence_data['medium']):3d} exports ({med_pct:5.1f}%){RESET}",
        f"{GREEN}HIGH    Confidence: {len(confidence_data['high']):3d} exports ({high_pct:5.1f}%){RESET}",
        "",
    ]
    
    # Add reason breakdown
    if reason_counts:
        lines.extend([
            "CONFIDENCE FACTORS (by frequency)",
            "-" * 60,
        ])
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"  * {reason:<40s} {count:3d} ({pct:5.1f}%)")
        lines.append("")
    
    # Add improvement opportunities
    lines.extend([
        "WAYS TO IMPROVE CONFIDENCE",
        "-" * 60,
    ])
    
    improvements = []
    if len(matches) < total:
        improvements.append(f"  * Provide header files (.h/.hpp): Would match function prototypes")
        improvements.append(f"    and increase HIGH confidence exports (currently {len(matches)}/{total})")
    if 'demangled C++ name' not in reason_counts:
        improvements.append(f"  * Ensure undname.exe is available: Helps identify C++ mangled names")
    
    if improvements:
        for imp in improvements:
            lines.append(imp)
    else:
        lines.append("  * All major confidence factors are present!")
    
    lines.extend([
        "",
        "EXPORT SAMPLES BY CONFIDENCE LEVEL",
        "-" * 60,
    ])
    
    # Add sample exports from each tier (LOW, MEDIUM, HIGH)
    for level in ['low', 'medium', 'high']:
        data = confidence_data[level]
        
        # Select color based on confidence level
        if level == 'low':
            color = RED
            level_text = "LOW"
        elif level == 'medium':
            color = YELLOW
            level_text = "MEDIUM"
        else:
            color = GREEN
            level_text = "HIGH"
        
        lines.append(f"\n{color}{level_text} CONFIDENCE ({len(data)} exports):{RESET}")
        
        if data:
            # Show first 5 and last 2 if more than 7
            shown = data[:5] if len(data) <= 7 else data[:5] + [{'name': '...', 'reasons': []}] + data[-2:]
            for item in shown:
                if item['name'] == '...':
                    lines.append(f"  ... ({len(data) - 7} more)")
                else:
                    reasons_str = ', '.join(item['reasons']) if item['reasons'] else 'no info'
                    lines.append(f"{BLUE}  * {item['name']}")
                    lines.append(f"      -> {reasons_str}{RESET}")
    
    lines.append("")
    
    # Write to file
    summary_text = '\n'.join(lines)
    tag_str = f"_{tag}" if tag else ""
    summary_file = out_dir / f"{dll_path.stem}_confidence_summary{tag_str}.txt"
    summary_file.write_text(summary_text, encoding='utf-8')
    
    return summary_text


def get_default_output_dir() -> Path:
    """Get default output directory."""
    return Path.cwd() / "mcp_dumpbin_out"


def main():
    parser = argparse.ArgumentParser(
        description="Advanced DLL Export Analyzer with tiered pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full analysis with headers and docs
  python csv_script.py --dll C:\\path\\to\\libzstd.dll --headers C:\\zstd\\lib --docs C:\\zstd\\doc

  # Basic analysis without headers
  python csv_script.py --dll C:\\path\\to\\library.dll

  # Reuse existing dumpbin output
  python csv_script.py --exports-raw existing_exports.txt --headers include_dir

  # Custom output directory
  python csv_script.py --dll library.dll --out C:\\output --tag myanalysis

Note: This script must be run from Visual Studio x64 Native Tools Command Prompt
      or ensure dumpbin.exe is available in PATH.
        """
    )
    
    parser.add_argument(
        "--dll",
        type=str,
        help="Path to the DLL file to analyze"
    )
    
    parser.add_argument(
        "--headers",
        type=str,
        default="",
        help="Root folder to search for header files (optional)"
    )
    
    parser.add_argument(
        "--docs",
        type=str,
        default="",
        help="Root folder to search for documentation files (optional)"
    )
    
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Output directory (default: ./mcp_dumpbin_out)"
    )
    
    parser.add_argument(
        "--tag",
        type=str,
        default="",
        help="Optional tag added to output filenames (e.g., _v1)"
    )
    
    parser.add_argument(
        "--exports-raw",
        type=str,
        default="",
        help="Path to existing raw dumpbin output file (skips dumpbin execution)"
    )
    
    parser.add_argument(
        "--dumpbin",
        type=str,
        default="dumpbin",
        help="Path to dumpbin.exe (default: 'dumpbin' from PATH)"
    )
    
    parser.add_argument(
        "--undname",
        type=str,
        default="undname",
        help="Path to undname.exe (default: 'undname' from PATH)"
    )
    
    parser.add_argument(
        "--no-demangle",
        action="store_true",
        help="Skip undname demangle step"
    )
    
    parser.add_argument(
        "--max-doc-hits",
        type=int,
        default=2,
        help="Max documentation file hits per function (default: 2)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.dll and not args.exports_raw:
        parser.error("Either --dll or --exports-raw must be specified")
    
    # Determine DLL path
    dll_path = None
    if args.dll:
        dll_path = Path(args.dll).expanduser().resolve()
        if not dll_path.exists():
            print(f"Error: DLL file not found: {dll_path}", file=sys.stderr)
            return 1
    else:
        # Infer DLL name from exports-raw filename
        dll_path = Path(args.exports_raw).stem.replace("_exports_raw", "")
        dll_path = Path(dll_path + ".dll")
    
    # Determine output directory
    out_dir = Path(args.out).expanduser().resolve() if args.out else get_default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {out_dir}")
    
    # Get raw dumpbin output
    raw_written = False
    if args.exports_raw:
        raw_path = Path(args.exports_raw).expanduser().resolve()
        if not raw_path.exists():
            print(f"Error: Exports raw file not found: {raw_path}", file=sys.stderr)
            return 1
        print(f"Reading existing raw exports from: {raw_path}")
        exports_out = raw_path.read_text(encoding="utf-8", errors="replace")
    else:
        # Validate dumpbin availability
        dumpbin_path = args.dumpbin
        
        if args.dumpbin == "dumpbin":
            # Using default 'dumpbin' - check if it's in PATH
            if not check_tool_available(args.dumpbin):
                print(f"Error: dumpbin not found in PATH", file=sys.stderr)
                print("Please run this script from Visual Studio x64 Native Tools Command Prompt", file=sys.stderr)
                print("Or specify the path to dumpbin.exe using --dumpbin", file=sys.stderr)
                return 1
        else:
            # User provided explicit path - validate it exists
            dumpbin_check = Path(args.dumpbin)
            if not dumpbin_check.exists():
                print(f"Error: Specified dumpbin not found: {args.dumpbin}", file=sys.stderr)
                return 1
            print(f"Using specified dumpbin: {args.dumpbin}")
        
        # Build command and show debug info
        cmd = [dumpbin_path, "/nologo", "/exports", str(dll_path)]
        print(f"Running dumpbin /exports on: {dll_path}")
        print(f"Debug - Command argv: {cmd}")
        
        rc, exports_out = run_cmd(cmd)
        
        if rc != 0:
            print(f"Error: dumpbin /exports failed (rc={rc})", file=sys.stderr)
            print(exports_out, file=sys.stderr)
            return 1
        
        # Write raw output
        raw_output_path = out_dir / f"{dll_path.stem}_exports_raw.txt"
        raw_output_path.write_text(exports_out, encoding="utf-8", errors="replace")
        print(f"Raw output written to: {raw_output_path}")
        raw_written = True
    
    # Parse exports
    print("Parsing exports...")
    exports = parse_dumpbin_exports(exports_out)
    
    if not exports:
        print("Error: No exports parsed from dumpbin output", file=sys.stderr)
        return 1
    
    print(f"Found {len(exports)} unique exports")
    
    # Demangle C++ names if requested
    undname_ok = False
    if not args.no_demangle:
        if check_tool_available(args.undname):
            print(f"Demangling C++ names with {args.undname}...")
            undname_ok = demangle_with_undname(exports, args.undname)
            if undname_ok:
                print("  Demangling successful")
        else:
            print(f"Warning: undname not available, skipping demangling")
    
    # Scan headers for prototypes
    matches: Dict[str, MatchInfo] = {}
    if args.headers:
        hdr_root = Path(args.headers).expanduser().resolve()
        if not hdr_root.exists():
            print(f"Error: Header root not found: {hdr_root}", file=sys.stderr)
            return 1
        
        print(f"Scanning headers in: {hdr_root}")
        header_files = iter_header_files(hdr_root)
        print(f"  Found {len(header_files)} header files")
        
        for e in exports:
            candidates = [e.name]
            # Try demangled name as well
            if e.demangled:
                dm = e.demangled
                paren = dm.find("(")
                head = dm[:paren] if paren != -1 else dm
                base = head.split("::")[-1].strip().split()[-1]
                if base and base not in candidates:
                    candidates.append(base)
            
            found = None
            for cand in candidates:
                for hf in header_files:
                    mi = find_prototype_in_header(hf, cand)
                    if mi:
                        mi.function = e.name
                        found = mi
                        break
                if found:
                    break
            
            if found:
                matches[e.name] = found
        
        print(f"  Matched {len(matches)} exports to header prototypes")
    
    # Scan documentation files
    doc_hits: Dict[str, List[str]] = {}
    if args.docs:
        docs_root = Path(args.docs).expanduser().resolve()
        if not docs_root.exists():
            print(f"Error: Docs root not found: {docs_root}", file=sys.stderr)
            return 1
        
        print(f"Scanning documentation in: {docs_root}")
        doc_hits = scan_docs_for_exports(docs_root, exports, args.max_doc_hits)
        total_hits = sum(len(v) for v in doc_hits.values())
        print(f"  Found {total_hits} documentation references")
    
    # Generate outputs for each tier
    tag = f"_{args.tag}" if args.tag else ""
    tier_entries: List[str] = []
    
    # Tier 1: exports + headers + docs scan
    if args.headers and args.docs:
        csv_path = out_dir / f"{dll_path.stem}_tier1_api{tag}.csv"
        json_path = out_dir / f"{dll_path.stem}_tier1_api{tag}.json"
        md_path = out_dir / f"{dll_path.stem}_tier1_api{tag}.md"
        write_csv(csv_path, exports, matches, doc_hits)
        write_json(json_path, dll_path, exports, matches, doc_hits, tier=1)
        write_report(md_path, dll_path, exports, matches, doc_hits)
        tier_entries.append(f"- Tier 1 (exports + headers + docs): {csv_path}, {json_path}")
        print(f"Tier 1 output: {csv_path} + {json_path.name}")
    else:
        tier_entries.append("- Tier 1: skipped (requires --headers and --docs)")
    
    # Tier 2: exports + headers
    if args.headers:
        csv_path = out_dir / f"{dll_path.stem}_tier2_api{tag}.csv"
        json_path = out_dir / f"{dll_path.stem}_tier2_api{tag}.json"
        md_path = out_dir / f"{dll_path.stem}_tier2_api{tag}.md"
        write_csv(csv_path, exports, matches, {})
        write_json(json_path, dll_path, exports, matches, {}, tier=2)
        write_report(md_path, dll_path, exports, matches, {})
        tier_entries.append(f"- Tier 2 (exports + headers): {csv_path}, {json_path}")
        print(f"Tier 2 output: {csv_path} + {json_path.name}")
    else:
        tier_entries.append("- Tier 2: skipped (requires --headers)")
    
    # Tier 3: exports + demangle
    if undname_ok:
        csv_path = out_dir / f"{dll_path.stem}_tier3_api{tag}.csv"
        json_path = out_dir / f"{dll_path.stem}_tier3_api{tag}.json"
        md_path = out_dir / f"{dll_path.stem}_tier3_api{tag}.md"
        write_csv(csv_path, exports, {}, {})
        write_json(json_path, dll_path, exports, {}, {}, tier=3)
        write_report(md_path, dll_path, exports, {}, {})
        tier_entries.append(f"- Tier 3 (exports + demangle): {csv_path}, {json_path}")
        print(f"Tier 3 output: {csv_path} + {json_path.name}")
    else:
        tier_entries.append("- Tier 3: skipped (undname not available or no C++ symbols)")
    
    # Tier 4: exports only
    csv_path = out_dir / f"{dll_path.stem}_tier4_api{tag}.csv"
    json_path = out_dir / f"{dll_path.stem}_tier4_api{tag}.json"
    md_path = out_dir / f"{dll_path.stem}_tier4_api{tag}.md"
    write_csv(csv_path, exports, {}, {})
    write_json(json_path, dll_path, exports, {}, {}, tier=4)
    write_report(md_path, dll_path, exports, {}, {})
    tier_entries.append(f"- Tier 4 (exports only): {csv_path}, {json_path}")
    print(f"Tier 4 output: {csv_path} + {json_path.name}")
    
    # Tier 5: metadata only
    if dll_path.exists():
        meta_path = out_dir / f"{dll_path.stem}_tier5_metadata{tag}.md"
        with meta_path.open("w", encoding="utf-8") as f:
            f.write("# DLL Metadata\n\n")
            f.write(f"**Path:** `{dll_path}`\n\n")
            f.write(f"**Size:** {dll_path.stat().st_size:,} bytes\n\n")
            f.write(f"**Modified:** {datetime.fromtimestamp(dll_path.stat().st_mtime)}\n\n")
            f.write(f"**Exports:** {len(exports)}\n\n")
        tier_entries.append(f"- Tier 5 (metadata): {meta_path}")
        print(f"Tier 5 output: {meta_path}")
    else:
        tier_entries.append("- Tier 5: skipped (DLL path unknown)")
    
    # Write tier summary
    summary_path = out_dir / f"{dll_path.stem}_tiers{tag}.md"
    write_tier_summary(summary_path, tier_entries)
    
    # Generate and display confidence summary
    confidence_summary = generate_confidence_summary(exports, matches, out_dir, dll_path, args.tag)
    
    print(f"\n{'='*60}")
    print(confidence_summary)
    print(f"{'='*60}")
    
    print("Completed successfully!")
    print(f"{'='*60}")
    if raw_written:
        print(f"Raw exports: {out_dir / f'{dll_path.stem}_exports_raw.txt'}")
    print(f"Tier summary: {summary_path}")
    print(f"Confidence summary: {out_dir / f'{dll_path.stem}_confidence_summary{tag}.txt'}")
    print(f"\nOutputs generated: CSV + JSON + Markdown for each tier")
    print(f"All outputs saved to: {out_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
