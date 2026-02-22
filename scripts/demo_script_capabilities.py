"""
demo_script_capabilities.py
---------------------------
Demonstrate MCP Factory's multi-language (non-PE) analysis capabilities.

Runs each new file-type through the same analysis pipeline that
demo_capabilities.py uses for PE/DLL targets, then prints a colour-coded
summary table.

Usage
-----
    python scripts/demo_script_capabilities.py

No arguments required.  Fixture files are read from
tests/fixtures/scripts/ relative to the repository root.
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

from main import main as analyze_main  # noqa: E402  (after sys.path insert)

# ── ANSI colours ─────────────────────────────────────────────────────────────
class C:
    HEADER    = "\033[95m"
    BLUE      = "\033[94m"
    CYAN      = "\033[96m"
    GREEN     = "\033[92m"
    YELLOW    = "\033[93m"
    RED       = "\033[91m"
    ENDC      = "\033[0m"
    BOLD      = "\033[1m"


# ── Fixture definitions ───────────────────────────────────────────────────────
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "scripts"

TARGETS = [
    # ── Script / JIT languages ──────────────────────────────────────────
    {"name": "sample.py",   "type": "Python script"},
    {"name": "sample.ps1",  "type": "PowerShell script"},
    {"name": "sample.vbs",  "type": "VBScript"},
    {"name": "sample.bat",  "type": "Batch script"},
    {"name": "sample.sh",   "type": "Shell script"},
    {"name": "sample.rb",   "type": "Ruby script"},
    {"name": "sample.php",  "type": "PHP script"},
    # ── JavaScript / TypeScript ──────────────────────────────────────────
    {"name": "sample.js",   "type": "JavaScript module"},
    {"name": "sample.ts",   "type": "TypeScript module"},
    # ── SQL ───────────────────────────────────────────────────────────────
    {"name": "sample.sql",  "type": "SQL source file"},
]


# ── Confidence helper (same logic as demo_capabilities.py) ───────────────────
def majority_confidence(invocables: list) -> tuple[str, str]:
    """Return (label, colour) for the dominant confidence tier."""
    if not invocables:
        return "NONE", C.RED

    counts = collections.Counter(
        inv.get("confidence", "low").lower() for inv in invocables
    )
    total = len(invocables)

    guaranteed = counts.get("guaranteed", 0)
    high       = counts.get("high",       0)

    if guaranteed / total > 0.5:
        return "GUARANTEED", C.GREEN
    if (guaranteed + high) / total > 0.5:
        return "HIGH",       C.CYAN
    if (guaranteed + high + counts.get("medium", 0)) / total > 0.5:
        return "MEDIUM",     C.YELLOW
    return "LOW", C.RED


# ── Runner ────────────────────────────────────────────────────────────────────
def run_demo() -> None:
    print(f"\n{C.HEADER}{C.BOLD}MCP FACTORY — MULTI-LANGUAGE SCRIPT DEMO{C.ENDC}")
    print(f"{C.HEADER}{'=' * 43}{C.ENDC}\n")

    output_base = REPO_ROOT / "demo_output" / "scripts"
    output_base.mkdir(parents=True, exist_ok=True)

    # Silence the logger during batch runs
    logging.disable(logging.CRITICAL)

    col_w = {"name": 16, "type": 22, "count": 8, "conf": 14}
    header = (
        f"{'File':<{col_w['name']}} | "
        f"{'Type':<{col_w['type']}} | "
        f"{'Invocables':<{col_w['count']}} | "
        f"{'Confidence'}"
    )
    print(header)
    print("-" * (len(header) + 4))

    any_missing = False

    for target in TARGETS:
        fixture_path = FIXTURE_DIR / target["name"]

        if not fixture_path.exists():
            print(
                f"{target['name']:<{col_w['name']}} | "
                f"{target['type']:<{col_w['type']}} | "
                f"{C.YELLOW}MISSING{C.ENDC}"
            )
            any_missing = True
            continue

        out_dir = output_base / fixture_path.name  # e.g. "sample.py" not just "sample"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Build CLI args – reuse the --target/--dll flag after the alias was added
        sys.argv = [
            "main.py",
            "--target", str(fixture_path),
            "--out",    str(out_dir),
        ]

        capture = io.StringIO()
        exit_code = None
        try:
            with redirect_stdout(capture), redirect_stderr(capture):
                try:
                    exit_code = analyze_main()
                except SystemExit as exc:
                    exit_code = exc.code
        except Exception as exc:
            print(f"{C.RED}EXCEPTION: {exc}{C.ENDC}")
            continue

        # Locate output JSON
        json_files = list(out_dir.glob("*_mcp.json"))
        if not json_files:
            print(
                f"{target['name']:<{col_w['name']}} | "
                f"{target['type']:<{col_w['type']}} | "
                f"{C.RED}FAILED (no JSON){C.ENDC}"
            )
            # Surface last 5 lines of captured output to help diagnosis
            captured = capture.getvalue().strip()
            if captured:
                for line in captured.splitlines()[-5:]:
                    print(f"    {C.RED}{line}{C.ENDC}")
            continue

        with open(json_files[0], encoding="utf-8") as fh:
            data = json.load(fh)

        invocables = data.get("invocables", [])
        count = len(invocables)
        conf_label, conf_colour = majority_confidence(invocables)

        print(
            f"{target['name']:<{col_w['name']}} | "
            f"{target['type']:<{col_w['type']}} | "
            f"{count:<{col_w['count']}} | "
            f"{conf_colour}{conf_label}{C.ENDC}"
        )

    # ── Footer ────────────────────────────────────────────────────────────
    print()
    if any_missing:
        print(
            f"{C.YELLOW}Some fixtures were not found.  "
            f"All files should live in  tests/fixtures/scripts/{C.ENDC}"
        )
    print(
        f"{C.BLUE}Done.  Artifacts written to  "
        f"demo_output/scripts/<name>/{C.ENDC}\n"
    )


# ── Per-file invocable detail (optional verbose mode) ─────────────────────────
def print_detail(name: str) -> None:
    """Print all invocables discovered for a single fixture file."""
    out_dir = REPO_ROOT / "demo_output" / "scripts" / name  # full filename as dir
    json_files = list(out_dir.glob("*_mcp.json"))
    if not json_files:
        print(f"No output found for {name!r} – run the demo first.")
        return

    with open(json_files[0], encoding="utf-8") as fh:
        data = json.load(fh)

    invocables = data.get("invocables", [])
    print(f"\n{C.BOLD}Detail: {name}  ({len(invocables)} invocables){C.ENDC}")
    print("-" * 60)
    for inv in invocables:
        conf  = inv.get("confidence", "?")
        badge = {
            "guaranteed": C.GREEN,
            "high":       C.CYAN,
            "medium":     C.YELLOW,
        }.get(conf, C.RED) + conf.upper() + C.ENDC

        print(f"  {C.BOLD}{inv['name']}{C.ENDC}  [{badge}]")
        if inv.get("signature"):
            print(f"    sig:    {inv['signature']}")
        if inv.get("parameters"):
            print(f"    params: {inv['parameters']}")
        if inv.get("return_type"):
            print(f"    return: {inv['return_type']}")
        if inv.get("doc_comment"):
            doc = inv["doc_comment"]
            if len(doc) > 80:
                doc = doc[:77] + "..."
            print(f"    doc:    {doc}")
        print()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Optional:  pass a fixture filename as the first argument to see detail.
    # Capture the argument BEFORE run_demo() trashes sys.argv.
    detail_target = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        detail_target = sys.argv[1]

    run_demo()

    if detail_target:
        print_detail(detail_target)
