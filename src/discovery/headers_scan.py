"""
headers_scan.py - Header file scanning and prototype extraction.

Searches header files for function prototypes matching exports,
extracting signatures and documentation comments.
"""

import re
from bisect import bisect_right
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from schema import ExportedFunc, MatchInfo


def iter_header_files(root: Path) -> List[Path]:
    """Find all header files in the given directory tree."""
    exts = {".h", ".hpp", ".hh", ".hxx", ".inl"}
    files = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return files


def make_proto_regex(func_name: str) -> re.Pattern:
    """Create regex to find function prototype in header files."""
    escaped = re.escape(func_name)
    return re.compile(rf"(^|[^A-Za-z0-9_]){escaped}\s*\(", re.MULTILINE)


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
    text = re.sub(
        r"\b(?:extern|static|inline|constexpr|consteval|constinit|friend)\b", "", text
    )
    text = re.sub(
        r"\b(?:__cdecl|__stdcall|__fastcall|__vectorcall|__thiscall)\b", "", text
    )
    text = re.sub(r"\b[A-Z][A-Z0-9_]*_(?:API|EXPORT|IMPORT|STATIC_API)\b", "", text)
    text = normalize_whitespace(text)
    return text


def find_prototype_in_header(file_path: Path, export_name: str) -> Optional[MatchInfo]:
    """Find function prototype in a header file."""
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
        after_name = proto_one[idx + len(export_name) :].lstrip()

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


def scan_headers(
    headers_root: Path, exports: List[ExportedFunc]
) -> Dict[str, MatchInfo]:
    """Scan header files for function prototypes matching exports.
    
    Args:
        headers_root: Root directory to search for headers
        exports: List of exported functions to find prototypes for
        
    Returns:
        Dict mapping export name to MatchInfo (or empty if no match found)
    """
    matches: Dict[str, MatchInfo] = {}
    header_files = iter_header_files(headers_root)

    for exp in exports:
        if exp.name in matches:
            continue

        for hdr in header_files:
            mi = find_prototype_in_header(hdr, exp.name)
            if mi:
                matches[exp.name] = mi
                break

    return matches
