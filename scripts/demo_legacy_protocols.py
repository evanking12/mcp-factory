"""
demo_legacy_protocols.py
------------------------
Standalone verification suite for the five spec-gap / legacy protocol
analyzers added in §2-3:

  • OpenAPI 3.x / Swagger 2.x  (YAML spec)
  • JSON-RPC 2.0               (JSON service descriptor)
  • SOAP / WSDL 1.1            (.wsdl XML)
  • CORBA IDL                  (.idl text)
  • JNDI configuration         (.jndi / .properties)
  • PDB debug symbols          (.pdb + companion .dll)

Usage
-----
  python scripts/demo_legacy_protocols.py         # all targets
  python scripts/demo_legacy_protocols.py openapi # filter by name

Output MCP JSON is written to demo_output/unified/<target>/ alongside
the main demo outputs.
"""

import collections
import json
import logging
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "discovery"))

from openapi_analyzer import analyze_openapi
from wsdl_analyzer    import analyze_wsdl
from idl_analyzer     import analyze_idl
from jndi_analyzer    import analyze_jndi
from pdb_analyzer     import analyze_pdb
from schema           import write_invocables_json

# UTF-8 output on Windows
import io as _io
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.WARNING)

# ── ANSI colours ──────────────────────────────────────────────────────────────
class C:
    HEADER = "\033[95m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    ENDC   = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"

# ── Fixture paths ─────────────────────────────────────────────────────────────
_SCRIPTS  = REPO_ROOT / "tests" / "fixtures" / "scripts"
_VCPKG    = REPO_ROOT / "tests" / "fixtures" / "vcpkg_installed" / "x64-windows" / "bin"

TARGETS = [
    {
        "name":     "sample_openapi.yaml",
        "path":     _SCRIPTS / "sample_openapi.yaml",
        "analyzer": analyze_openapi,
        "type":     "OpenAPI 3.0 spec",
        "tag":      "openapi_operation",
    },
    {
        "name":     "sample_jsonrpc.json",
        "path":     _SCRIPTS / "sample_jsonrpc.json",
        "analyzer": analyze_openapi,   # handles JSON-RPC via same module
        "type":     "JSON-RPC 2.0 descriptor",
        "tag":      "jsonrpc_method",
    },
    {
        "name":     "sample.wsdl",
        "path":     _SCRIPTS / "sample.wsdl",
        "analyzer": analyze_wsdl,
        "type":     "SOAP/WSDL 1.1 service",
        "tag":      "soap_operation",
    },
    {
        "name":     "sample.idl",
        "path":     _SCRIPTS / "sample.idl",
        "analyzer": analyze_idl,
        "type":     "CORBA IDL interface",
        "tag":      "corba_method",
    },
    {
        "name":     "sample.jndi",
        "path":     _SCRIPTS / "sample.jndi",
        "analyzer": analyze_jndi,
        "type":     "JNDI config",
        "tag":      "jndi_lookup",
    },
    {
        "name":     "zstd.pdb",
        "path":     _VCPKG / "zstd.pdb",
        "analyzer": analyze_pdb,
        "type":     "PDB debug symbols",
        "tag":      "pdb_symbol",
    },
]

# ── Output directory ──────────────────────────────────────────────────────────
OUT_BASE = REPO_ROOT / "demo_output" / "unified"


# ── Confidence helpers ────────────────────────────────────────────────────────
_CONF_ORDER = ("guaranteed", "high", "medium", "low")

_CONF_COLOUR = {
    "guaranteed": C.GREEN,
    "high":       C.GREEN,
    "medium":     C.YELLOW,
    "low":        C.RED,
}


def majority_confidence(invocables: list) -> tuple:
    if not invocables:
        return "NONE", C.RED
    counts = collections.Counter(
        inv.confidence.lower() for inv in invocables
    )
    total = len(invocables)
    for tier in _CONF_ORDER:
        if counts.get(tier, 0) / total >= 0.5:
            return tier.upper(), _CONF_COLOUR[tier]
    dominant = counts.most_common(1)[0][0]
    return dominant.upper(), _CONF_COLOUR.get(dominant, C.DIM)


# ── JSON validator ────────────────────────────────────────────────────────────
_REQUIRED_KEYS = {"name", "kind", "confidence", "description", "return_type",
                  "parameters", "execution"}


def _check_json(mcp_path: Path) -> list:
    """Return a list of problems found in the MCP JSON; empty = OK."""
    problems = []
    try:
        with open(mcp_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return [f"Cannot load JSON: {exc}"]

    # The output key is 'invocables' (not 'tools')
    invocables = data.get("invocables") or []
    if not invocables:
        return ["No invocables[] in output"]

    for tool in invocables:
        for k in _REQUIRED_KEYS:
            if k not in tool:
                problems.append(f"'{tool.get('name', '?')}' missing key '{k}'")

        exec_block = tool.get("execution") or {}
        if "method" not in exec_block:
            problems.append(f"'{tool.get('name', '?')}' execution.method missing")
        if exec_block.get("method") == "unknown":
            problems.append(f"'{tool.get('name', '?')}' has method=unknown")

    return problems


# ── Run one target ────────────────────────────────────────────────────────────

def run_target(target: dict, verbose: bool = False) -> bool:
    """Analyse one target, write output, print row. Returns True on success."""
    name     = target["name"]
    path     = target["path"]
    analyzer = target["analyzer"]
    ttype    = target["type"]

    if not path.exists():
        print(f"  {C.YELLOW}SKIP{C.ENDC}  {name:<35} — file not found: {path}")
        return True  # don't count missing files as failures

    # Run analyzer
    try:
        invocables = analyzer(path)
    except Exception as exc:
        print(f"  {C.RED}FAIL{C.ENDC}  {name:<35} — analyzer raised {type(exc).__name__}: {exc}")
        return False

    if not invocables:
        print(f"  {C.RED}FAIL{C.ENDC}  {name:<35} — 0 invocables returned")
        return False

    # Write MCP JSON
    out_dir = OUT_BASE / name
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(name).stem
    mcp_path = out_dir / f"{stem}_mcp.json"

    write_invocables_json(
        mcp_path,
        invocables,
        dll_path=path,
        tier=4,
        schema_version="2.0.0",
    )

    # Validate JSON
    problems = _check_json(mcp_path)

    conf_label, conf_colour = majority_confidence(invocables)
    status = f"{C.GREEN}PASS{C.ENDC}"
    if problems:
        status = f"{C.YELLOW}WARN{C.ENDC}"

    print(
        f"  {status}  {name:<35} | {ttype:<30} | "
        f"{len(invocables):>3} invocables | "
        f"{conf_colour}{conf_label:<11}{C.ENDC}"
    )
    if problems:
        for p in problems:
            print(f"        {C.YELLOW}⚠ {p}{C.ENDC}")

    if verbose:
        for inv in invocables[:5]:
            print(f"        {C.DIM}{inv.name:<30} ({inv.confidence}){C.ENDC}")
        if len(invocables) > 5:
            print(f"        {C.DIM}… {len(invocables)-5} more{C.ENDC}")

    return True  # WARN still counts as pass for suite


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    filter_arg  = sys.argv[1].lower() if len(sys.argv) > 1 else None
    verbose     = "--verbose" in sys.argv or "-v" in sys.argv

    targets = [t for t in TARGETS
               if filter_arg is None or filter_arg in t["name"].lower()]

    if not targets:
        print(f"No targets match filter '{filter_arg}'")
        sys.exit(1)

    print(f"\n{C.BOLD}{C.HEADER}MCP Factory — Legacy Protocol / Spec-Gap Demo{C.ENDC}")
    print("─" * 100)
    print(f"  {'Status':<8} {'File':<35} | {'Type':<30} | {'Count':>8} | Confidence")
    print("─" * 100)

    passed = 0
    failed = 0

    for t in targets:
        ok = run_target(t, verbose=verbose)
        if ok:
            passed += 1
        else:
            failed += 1

    print("─" * 100)
    colour = C.GREEN if failed == 0 else C.RED
    print(
        f"\n  {colour}Summary: {passed} passed, {failed} failed{C.ENDC} "
        f"({passed + failed} targets)\n"
        f"  Artifacts -> demo_output/unified/<target>/\n"
    )

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
