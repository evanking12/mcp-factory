#!/usr/bin/env python3
"""
main.py - CLI entry point and pipeline orchestration.

Parses arguments, runs the analysis pipeline, and writes outputs.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

from classify import classify_file, FileType, extract_signature, get_architecture
from docs_scan import scan_docs_for_exports
from exports import demangle_with_undname, deduplicate_exports, resolve_forwarders
from headers_scan import scan_headers
from pe_parse import get_exports_from_dumpbin
from schema import ExportedFunc, Invocable, MatchInfo, write_csv, write_json, write_markdown, write_tier_summary


# Plugin-based analyzer registry
ANALYZER_REGISTRY = {
    'pe_dll': {'name': 'PE DLL Analyzer', 'enabled': True},
    'pe_exe': {'name': 'PE EXE Analyzer', 'enabled': True},
    'dotnet': {'name': '.NET Assembly Analyzer', 'enabled': True},
    'com': {'name': 'COM Registry Analyzer', 'enabled': False},
    'cli': {'name': 'CLI Tool Analyzer', 'enabled': False},
}


def score_confidence(export: Invocable, matches: dict, is_signed: bool, forwarded_resolved: bool) -> tuple:
    """Score confidence in export invocability with reasons."""
    score = 0
    reasons = []
    
    if export.source_type == 'export':
        score += 2
        reasons.append('exported from DLL')
    
    if export.name in matches:
        score += 3
        reasons.append('matched to header prototype')
    
    if is_signed:
        score += 2
        reasons.append('digitally signed')
    
    if forwarded_resolved:
        score += 1
        reasons.append('forwarded reference resolved')
    
    if export.doc_comment:
        score += 1
        reasons.append('has documentation')
    
    if score >= 6:
        confidence = 'high'
    elif score >= 4:
        confidence = 'medium'
    else:
        confidence = 'low'
    
    return confidence, reasons


def generate_confidence_summary(
    exports: List[ExportedFunc],
    matches: dict,
    is_signed: bool,
    forwarding_chain: dict,
    base_name: str,
    out_dir: Path
) -> str:
    """Generate human-readable confidence summary and write to file."""
    
    # Score all exports
    confidence_data = {'high': [], 'medium': [], 'low': []}
    reason_counts = {}
    
    for exp in exports:
        # Convert ExportedFunc to Invocable-like object for scoring
        forwarded_resolved = exp.name in forwarding_chain and forwarding_chain[exp.name] != exp.name
        score, reasons = score_confidence(
            type('Export', (), {
                'name': exp.name,
                'source_type': 'export',
                'doc_comment': getattr(exp, 'doc_comment', None)
            })(),
            matches,
            is_signed,
            forwarded_resolved
        )
        
        confidence_data[score].append({
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
    
    # Generate summary text
    lines = [
        f"CONFIDENCE ANALYSIS SUMMARY",
        f"{'=' * 60}",
        f"",
        f"DLL: {base_name}",
        f"Total Exports: {total}",
        f"Analysis Date: {__import__('datetime').datetime.now().isoformat()}",
        f"",
        f"CONFIDENCE BREAKDOWN",
        f"{'-' * 60}",
        f"HIGH    Confidence: {len(confidence_data['high']):3d} exports ({high_pct:5.1f}%)",
        f"MEDIUM  Confidence: {len(confidence_data['medium']):3d} exports ({med_pct:5.1f}%)",
        f"LOW     Confidence: {len(confidence_data['low']):3d} exports ({low_pct:5.1f}%)",
        f"",
    ]
    
    # Add reason breakdown
    if reason_counts:
        lines.extend([
            f"CONFIDENCE FACTORS (by frequency)",
            f"{'-' * 60}",
        ])
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"  • {reason:<40s} {count:3d} ({pct:5.1f}%)")
        lines.append("")
    
    # Add improvement opportunities
    lines.extend([
        f"WAYS TO IMPROVE CONFIDENCE",
        f"{'-' * 60}",
    ])
    
    improvements = []
    if len(matches) < total:
        improvements.append(f"  • Provide header files (.h/.hpp): Would match function prototypes")
        improvements.append(f"    and increase HIGH confidence exports")
    if not is_signed:
        improvements.append(f"  • Obtain signed binaries: Digital signatures boost confidence")
    if 'forwarded reference resolved' not in reason_counts:
        improvements.append(f"  • Document forwarder chains: Track indirect function references")
    
    if improvements:
        for imp in improvements:
            lines.append(imp)
    else:
        lines.append("  • All major confidence factors are present!")
    
    lines.extend([
        "",
        f"EXPORT DETAILS BY CONFIDENCE LEVEL",
        f"{'-' * 60}",
    ])
    
    # Add sample exports from each tier
    for level in ['high', 'medium', 'low']:
        data = confidence_data[level]
        lines.append(f"\n{level.upper()} CONFIDENCE ({len(data)} exports):")
        
        if data:
            # Show first 5 and last 2 if more than 7
            shown = data[:5] if len(data) <= 7 else data[:5] + [{'name': '...', 'reasons': []}] + data[-2:]
            for item in shown:
                if item['name'] == '...':
                    lines.append(f"  ... ({len(data) - 7} more)")
                else:
                    reasons_str = ', '.join(item['reasons']) if item['reasons'] else 'no info'
                    lines.append(f"  • {item['name']}")
                    lines.append(f"      → {reasons_str}")
    
    lines.append("")
    
    # Write to file
    summary_text = '\n'.join(lines)
    summary_file = out_dir / f"{base_name}_confidence_summary.txt"
    summary_file.write_text(summary_text, encoding='utf-8')
    
    return summary_text


def get_default_output_dir() -> Path:
    """Get default output directory for analysis results."""
    return Path.cwd() / "mcp_dumpbin_out"


def main():
    """Main entry point."""
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    parser = argparse.ArgumentParser(
        description="Advanced DLL Export Analyzer - Generate MCP schemas from Windows binaries"
    )

    # Required arguments (one of)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--dll", type=Path, help="Path to DLL file to analyze"
    )
    input_group.add_argument(
        "--exports-raw",
        type=Path,
        help="Path to existing dumpbin /exports output (skip dumpbin run)",
    )

    # Optional arguments
    parser.add_argument(
        "--headers",
        type=Path,
        help="Root directory to search for header files (.h, .hpp, etc.)",
    )
    parser.add_argument(
        "--docs", type=Path, help="Root directory to search for documentation files"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=f"Output directory (default: {get_default_output_dir()})",
    )
    parser.add_argument(
        "--tag", type=str, default="", help="Tag to append to output filenames"
    )
    parser.add_argument(
        "--dumpbin",
        type=str,
        default="dumpbin",
        help="Path to dumpbin.exe or name on PATH",
    )
    parser.add_argument(
        "--undname",
        type=str,
        default="undname",
        help="Path to undname.exe or name on PATH",
    )
    parser.add_argument(
        "--no-demangle",
        action="store_true",
        help="Skip C++ name demangling step",
    )
    parser.add_argument(
        "--max-doc-hits",
        type=int,
        default=2,
        help="Maximum documentation file hits per export",
    )

    args = parser.parse_args()

    # Resolve output directory
    out_dir = args.out or get_default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build base filename from DLL or use generic name
    if args.dll:
        base_name = args.dll.stem
        dll_path = args.dll
    else:
        base_name = "analysis"
        dll_path = None

    if args.tag:
        base_name = f"{base_name}_{args.tag}"

    # Phase 1: Get raw exports
    exports: List[ExportedFunc] = []

    if args.exports_raw:
        # Read from existing raw file
        try:
            raw_text = args.exports_raw.read_text(encoding="utf-8")
            from pe_parse import parse_dumpbin_exports
            exports = parse_dumpbin_exports(raw_text)
        except Exception as e:
            logger.error(f"Error reading exports-raw file: {e}")
            return 1
    elif args.dll:
        # Run dumpbin
        raw_path = out_dir / f"{base_name}_exports_raw.txt"
        exports, success = get_exports_from_dumpbin(args.dll, args.dumpbin, raw_path)

        if not success:
            logger.error(f"Could not extract exports from {args.dll}")
            if raw_path.exists():
                try:
                    raw_content = raw_path.read_text()
                    if not raw_content.strip():
                        print("  (dumpbin produced empty output)", file=sys.stderr)
                    else:
                        print("  (First 50 lines of dumpbin output:)", file=sys.stderr)
                        for i, line in enumerate(raw_content.split("\n")[:50]):
                            print(f"    {line}", file=sys.stderr)
                except Exception:
                    pass
            return 1

    if not exports:
        logger.error("No exports found")
        return 1

    # Phase 2: Deduplicate and demangle, resolve forwarders
    exports = deduplicate_exports(exports)

    if not args.no_demangle:
        demangle_with_undname(exports, args.undname)
    
    # Extract digital signature
    is_signed, publisher = False, None
    if dll_path:
        is_signed, publisher = extract_signature(dll_path)
    
    # Resolve forwarder chains
    forwarding_chain = resolve_forwarders(exports)

    # Phase 3: Match to headers and documentation
    matches: dict = {}
    doc_hits: dict = {}

    if args.headers:
        matches = scan_headers(args.headers, exports)

    if args.docs:
        doc_hits = scan_docs_for_exports(args.docs, exports, args.max_doc_hits)

    # Phase 4: Write tiered outputs
    tier_entries = []

    # Tier 1: Exports + headers + docs
    if args.headers and args.docs and matches:
        tier1_csv = out_dir / f"{base_name}_tier1_api.csv"
        tier1_md = out_dir / f"{base_name}_tier1_api.md"
        write_csv(tier1_csv, exports, matches, doc_hits, is_signed, publisher)
        write_markdown(tier1_md, dll_path or args.dll or Path(base_name), exports, matches, doc_hits)
        tier_entries.append("Tier 1: Exports + headers + docs")

    # Tier 2: Exports + headers
    if args.headers and matches:
        tier2_csv = out_dir / f"{base_name}_tier2_api.csv"
        tier2_md = out_dir / f"{base_name}_tier2_api.md"
        write_csv(tier2_csv, exports, matches, {}, is_signed, publisher)
        write_markdown(tier2_md, dll_path or args.dll or Path(base_name), exports, matches, {})
        tier_entries.append("Tier 2: Exports + headers")

    # Tier 3: Exports + demangle
    if any(e.demangled for e in exports):
        tier3_csv = out_dir / f"{base_name}_tier3_api.csv"
        tier3_md = out_dir / f"{base_name}_tier3_api.md"
        write_csv(tier3_csv, exports, {}, {}, is_signed, publisher)
        write_markdown(tier3_md, dll_path or args.dll or Path(base_name), exports, {}, {})
        tier_entries.append("Tier 3: Exports + demangled names")

    # Tier 4: Exports only (always generated)
    tier4_csv = out_dir / f"{base_name}_tier4_api.csv"
    tier4_md = out_dir / f"{base_name}_tier4_api.md"
    write_csv(tier4_csv, exports, {}, {}, is_signed, publisher)
    write_markdown(tier4_md, dll_path or args.dll or Path(base_name), exports, {}, {})
    tier_entries.append("Tier 4: Exports only")

    # Tier 5: Metadata
    tier5_md = out_dir / f"{base_name}_tier5_metadata.md"
    with open(tier5_md, 'w', encoding='utf-8') as f:
        f.write(f"# DLL Metadata: {base_name}\n\n")
        f.write(f"Total exports: {len(exports)}\n")
        if dll_path and dll_path.exists():
            f.write(f"File size: {dll_path.stat().st_size} bytes\n")
        demangled_count = sum(1 for e in exports if e.demangled)
        f.write(f"Demangled: {demangled_count}\n")
        matched_count = sum(1 for e in exports if e.name in matches)
        f.write(f"Header matched: {matched_count}\n")
        f.write(f"\nDate generated: {__import__('datetime').datetime.now().isoformat()}\n")
    tier_entries.append("Tier 5: Metadata only")

    # Tier summary
    summary_md = out_dir / f"{base_name}_tiers.md"
    write_tier_summary(summary_md, tier_entries)

    # Phase 5: Generate confidence summary
    confidence_summary = generate_confidence_summary(
        exports, matches, is_signed, forwarding_chain, base_name, out_dir
    )

    logger.info(f"Analysis complete. Results in: {out_dir}")
    logger.info(f"Exports found: {len(exports)}")
    logger.info(f"Matched to headers: {sum(1 for e in exports if e.name in matches)}")
    logger.info(f"Demangled: {sum(1 for e in exports if e.demangled)}")
    
    # Print confidence summary to console
    print("\n" + "=" * 60)
    print(confidence_summary)
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
