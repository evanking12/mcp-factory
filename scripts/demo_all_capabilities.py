"""
demo_all_capabilities.py
------------------------
Unified showcase of every binary and source-file type MCP Factory supports.

Replaces the standalone demo_capabilities.py and demo_script_capabilities.py
with a single, section-organised run.

Usage
-----
    python scripts/demo_all_capabilities.py           # full table
    python scripts/demo_all_capabilities.py sample.ts # + invocable detail

Sections
--------
  1  Native PE DLLs          – kernel32, user32, ws2_32, rpcrt4
  2  .NET Assemblies          – System.dll, mscorlib.dll
  3  COM Servers / Type Libs  – oleaut32.dll, shell32.dll, stdole2.tlb
  4  PE EXEs                  – cmd.exe  [limited – EXE scanner deferred]
  5  Bundled DLL Fixtures     – zstd.dll, sqlite3.dll  (vcpkg / tests/fixtures)
  6  Script / JIT Languages   – .py .ps1 .vbs .bat .sh .rb .php
  7  JavaScript / TypeScript  – .js .ts
  8  SQL Source Files         – .sql
  9  Legacy Protocols / Specs – OpenAPI, JSON-RPC, WSDL, CORBA IDL, JNDI, PDB
 10  Directory Scan (§2.a)    – scripts/ dir, proves installed-instance support
"""

import collections
import io
import json
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "discovery"))

from main import main as analyze_main  # noqa: E402

# Ensure UTF-8 output on Windows regardless of active code page
import io as _io
import sys as _sys
if hasattr(_sys.stdout, 'reconfigure'):
    try:
        _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ── ANSI colours ─────────────────────────────────────────────────────────────
class C:
    HEADER  = "\033[95m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    ENDC    = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"


# ── Column widths ────────────────────────────────────────────────────────────
W_NAME  = 22
W_TYPE  = 24
W_COUNT =  9
# confidence label takes the rest


# ── Target catalogue ─────────────────────────────────────────────────────────
_FIXTURES   = REPO_ROOT / "tests" / "fixtures"
_SCRIPTS    = _FIXTURES / "scripts"
_VCPKG_BIN  = _FIXTURES / "vcpkg_installed" / "x64-windows" / "bin"
_SYS32      = Path(r"C:\Windows\System32")
_DOTNET     = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319")

SECTIONS = [
    {
        "title": "Native PE DLLs",
        "note": None,
        "targets": [
            {"name": "kernel32.dll",  "path": _SYS32  / "kernel32.dll",  "type": "System API"},
            {"name": "user32.dll",    "path": _SYS32  / "user32.dll",    "type": "UI System API"},
            {"name": "ws2_32.dll",    "path": _SYS32  / "ws2_32.dll",    "type": "Network API"},
            {"name": "rpcrt4.dll",    "path": _SYS32  / "rpcrt4.dll",    "type": "RPC Runtime"},
        ],
    },
    {
        "title": ".NET Assemblies",
        "note": None,
        "targets": [
            {"name": "System.dll",    "path": _DOTNET / "System.dll",    "type": ".NET Assembly"},
            {"name": "mscorlib.dll",  "path": _DOTNET / "mscorlib.dll",  "type": ".NET Core Lib"},
        ],
    },
    {
        "title": "COM Servers & Type Libraries",
        "note": None,
        "targets": [
            {"name": "oleaut32.dll",  "path": _SYS32  / "oleaut32.dll",  "type": "COM Server"},
            {"name": "shell32.dll",   "path": _SYS32  / "shell32.dll",   "type": "COM + Native"},
            {"name": "stdole2.tlb",   "path": _SYS32  / "stdole2.tlb",   "type": "Type Library"},
        ],
    },
    {
        "title": "PE EXEs",
        "note": "EXE GUI/dialog scanner deferred — CLI/export invocables only",
        "targets": [
            {"name": "cmd.exe",       "path": _SYS32  / "cmd.exe",       "type": "PE EXE (CLI)"},
        ],
    },
    {
        "title": "Bundled DLL Fixtures  (vcpkg)",
        "note": None,
        "targets": [
            {"name": "zstd.dll",      "path": _VCPKG_BIN / "zstd.dll",   "type": "C Library"},
            {"name": "sqlite3.dll",   "path": _VCPKG_BIN / "sqlite3.dll","type": "C Library"},
        ],
    },
    {
        "title": "Script / JIT Languages",
        "note": None,
        "targets": [
            {"name": "sample.py",  "path": _SCRIPTS / "sample.py",  "type": "Python script"},
            {"name": "sample.ps1", "path": _SCRIPTS / "sample.ps1", "type": "PowerShell script"},
            {"name": "sample.vbs", "path": _SCRIPTS / "sample.vbs", "type": "VBScript"},
            {"name": "sample.bat", "path": _SCRIPTS / "sample.bat", "type": "Batch script"},
            {"name": "sample.sh",  "path": _SCRIPTS / "sample.sh",  "type": "Shell script"},
            {"name": "sample.rb",  "path": _SCRIPTS / "sample.rb",  "type": "Ruby script"},
            {"name": "sample.php", "path": _SCRIPTS / "sample.php", "type": "PHP script"},
        ],
    },
    {
        "title": "JavaScript / TypeScript",
        "note": None,
        "targets": [
            {"name": "sample.js",  "path": _SCRIPTS / "sample.js",  "type": "JavaScript module"},
            {"name": "sample.ts",  "path": _SCRIPTS / "sample.ts",  "type": "TypeScript module"},
        ],
    },
    {
        "title": "SQL Source Files",
        "note": None,
        "targets": [
            {"name": "sample.sql", "path": _SCRIPTS / "sample.sql", "type": "SQL source file"},
        ],
    },
    {
        "title": "Legacy Protocols & Spec Formats",
        "note": "OpenAPI / JSON-RPC / SOAP-WSDL / CORBA IDL / JNDI / PDB symbols",
        "targets": [
            {"name": "sample_openapi.yaml", "path": _SCRIPTS / "sample_openapi.yaml", "type": "OpenAPI 3.0 spec"},
            {"name": "sample_jsonrpc.json", "path": _SCRIPTS / "sample_jsonrpc.json", "type": "JSON-RPC 2.0 descriptor"},
            {"name": "sample.wsdl",         "path": _SCRIPTS / "sample.wsdl",         "type": "SOAP/WSDL 1.1 service"},
            {"name": "sample.idl",          "path": _SCRIPTS / "sample.idl",          "type": "CORBA IDL interface"},
            {"name": "sample.jndi",         "path": _SCRIPTS / "sample.jndi",         "type": "JNDI config"},
            {"name": "zstd.pdb",            "path": _VCPKG_BIN / "zstd.pdb",          "type": "PDB debug symbols"},
        ],
    },
    {
        "title": "Directory Scan  (\u00a72.a installed-instance target)",
        "note": "Passes a directory to --target; proves §2.a directory-walk compliance",
        "targets": [
            {"name": "scripts/  (dir)", "path": _SCRIPTS, "type": "Installed Directory"},
        ],
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def majority_confidence(invocables: list) -> tuple:
    """Return (label, colour) for the dominant confidence tier."""
    if not invocables:
        return "NONE", C.RED

    counts = collections.Counter(
        inv.get("confidence", "low").lower() for inv in invocables
    )
    total      = len(invocables)
    guaranteed = counts.get("guaranteed", 0)
    high       = counts.get("high",       0)
    medium     = counts.get("medium",     0)

    if guaranteed / total > 0.5:
        return "GUARANTEED", C.GREEN
    if (guaranteed + high) / total > 0.5:
        return "HIGH",       C.CYAN
    if (guaranteed + high + medium) / total > 0.5:
        return "MEDIUM",     C.YELLOW
    return "LOW", C.RED


def _run_target(target: dict, out_base: Path) -> dict:
    """Run the analyzer for one target.  Returns a result dict."""
    path = Path(target["path"])

    if not path.exists():
        return {"status": "missing"}

    # Output directory: use full filename to avoid collisions when stems match
    out_dir = out_base / path.name
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.argv = ["main.py", "--target", str(path), "--out", str(out_dir)]

    capture = io.StringIO()
    try:
        with redirect_stdout(capture), redirect_stderr(capture):
            try:
                analyze_main()
            except SystemExit:
                pass
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}

    json_files = list(out_dir.glob("*_mcp.json"))
    if not json_files:
        return {
            "status": "failed",
            "detail": capture.getvalue().strip().splitlines()[-5:],
        }

    with open(json_files[0], encoding="utf-8") as fh:
        data = json.load(fh)

    invocables = data.get("invocables", [])
    label, colour = majority_confidence(invocables)
    return {
        "status":     "ok",
        "count":      len(invocables),
        "confidence": label,
        "colour":     colour,
    }


def _row(name: str, kind: str, result: dict) -> str:
    name_col = f"{name:<{W_NAME}}"
    type_col = f"{kind:<{W_TYPE}}"

    if result["status"] == "missing":
        return f"{name_col} | {type_col} | {C.DIM}SKIP (not found){C.ENDC}"
    if result["status"] == "failed":
        lines = "  ".join(result.get("detail", []))
        return (
            f"{name_col} | {type_col} | {C.RED}FAILED{C.ENDC}\n"
            f"    {C.RED}{lines}{C.ENDC}"
        )
    if result["status"] == "error":
        return f"{name_col} | {type_col} | {C.RED}ERROR: {result['detail']}{C.ENDC}"

    col = result["colour"]
    label = result["confidence"]
    count = result["count"]
    return f"{name_col} | {type_col} | {count:<{W_COUNT}} | {col}{label}{C.ENDC}"


def _section_header(title: str, note: str | None) -> None:
    bar = "-" * (W_NAME + W_TYPE + W_COUNT + 14)
    print(f"\n{C.BOLD}{C.HEADER}  {title}{C.ENDC}")
    if note:
        print(f"  {C.YELLOW}  NOTE: {note}{C.ENDC}")
    print(f"  {C.DIM}{bar}{C.ENDC}")
    col_header = (
        f"  {'File':<{W_NAME}} | {'Type':<{W_TYPE}} | "
        f"{'Invocables':<{W_COUNT}} | Confidence"
    )
    print(f"{C.DIM}{col_header}{C.ENDC}")
    print(f"  {C.DIM}{bar}{C.ENDC}")


# ── Main runner ───────────────────────────────────────────────────────────────
def run_demo() -> dict:
    """Run all sections.  Returns totals dict for the summary footer."""
    print(f"\n{C.BOLD}{C.HEADER}  MCP FACTORY — FULL CAPABILITIES DEMO{C.ENDC}")
    print(f"  {C.DIM}All supported binary and source-file types{C.ENDC}")

    logging.disable(logging.CRITICAL)

    out_base = REPO_ROOT / "demo_output" / "unified"
    out_base.mkdir(parents=True, exist_ok=True)

    totals = {"ok": 0, "missing": 0, "failed": 0, "sections": 0}

    for section in SECTIONS:
        totals["sections"] += 1
        _section_header(section["title"], section.get("note"))

        for target in section["targets"]:
            result = _run_target(target, out_base)
            print(f"  {_row(target['name'], target['type'], result)}")

            if result["status"] == "ok":
                totals["ok"] += 1
            elif result["status"] == "missing":
                totals["missing"] += 1
            else:
                totals["failed"] += 1

    return totals


def _footer(totals: dict) -> None:
    total = totals["ok"] + totals["missing"] + totals["failed"]
    skip  = totals["missing"]
    ok    = totals["ok"]
    fail  = totals["failed"]

    print(f"\n  {'-'*50}")
    print(
        f"  {C.BOLD}Summary:{C.ENDC}  "
        f"{C.GREEN}{ok} succeeded{C.ENDC}  "
        f"{C.DIM}{skip} skipped{C.ENDC}  "
        f"{'  ' + C.RED + str(fail) + ' failed' + C.ENDC if fail else ''}"
        f"  ({total} total across {totals['sections']} sections)"
    )
    print(f"  Artifacts → {C.BLUE}demo_output/unified/<name>/{C.ENDC}\n")


# ── Detail view ───────────────────────────────────────────────────────────────
def print_detail(name: str) -> None:
    """Print all invocables for a single target (use full filename, e.g. sample.ts)."""
    out_dir    = REPO_ROOT / "demo_output" / "unified" / name
    json_files = list(out_dir.glob("*_mcp.json")) if out_dir.exists() else []

    if not json_files:
        print(f"\n  No output found for {name!r} — run the demo first.\n")
        return

    with open(json_files[0], encoding="utf-8") as fh:
        data = json.load(fh)

    invocables = data.get("invocables", [])
    print(f"\n{C.BOLD}  Detail: {name}  ({len(invocables)} invocables){C.ENDC}")
    print(f"  {'-'*60}")

    CONF_COLOUR = {
        "guaranteed": C.GREEN, "high": C.CYAN,
        "medium": C.YELLOW,    "low":  C.RED,
    }
    for inv in invocables:
        conf   = inv.get("confidence", "?")
        colour = CONF_COLOUR.get(conf, C.ENDC)
        badge  = colour + conf.upper() + C.ENDC

        print(f"  {C.BOLD}{inv['name']}{C.ENDC}  [{badge}]")
        if inv.get("signature"):
            sig = inv["signature"]
            if len(sig) > 90:
                sig = sig[:87] + "..."
            print(f"    sig:    {sig}")
        if inv.get("parameters"):
            params = str(inv["parameters"])
            if len(params) > 90:
                params = params[:87] + "..."
            print(f"    params: {params}")
        if inv.get("return_type"):
            print(f"    return: {inv['return_type']}")
        if inv.get("doc_comment"):
            doc = inv["doc_comment"]
            if len(doc) > 90:
                doc = doc[:87] + "..."
            print(f"    doc:    {doc}")
        print()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Capture optional detail target before run_demo() writes sys.argv
    detail_target = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        detail_target = sys.argv[1]

    totals = run_demo()
    _footer(totals)

    if detail_target:
        print_detail(detail_target)
