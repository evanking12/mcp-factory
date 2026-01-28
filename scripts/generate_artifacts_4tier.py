"""
Generate artifacts with 4-tier confidence system (GUARANTEED, HIGH, MEDIUM, LOW)
Supports safe mode execution to prevent terminal issues.
"""

import sys
import argparse
import io
from pathlib import Path
import json
import csv
import os
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "discovery"))

from main import main as analyze_main


def find_headers_for_dll(dll_path: Path) -> Path | None:
    """Auto-discover header files for a DLL.
    
    Search strategy:
    1. vcpkg libraries: Check ../include relative to DLL
    2. System DLLs: Check Windows SDK paths
    3. Custom libraries: Check common header locations
    """
    dll_path = Path(dll_path)
    
    # Strategy 1: vcpkg structure (bin/foo.dll -> include/)
    if 'vcpkg' in str(dll_path).lower():
        # Check if we're in vcpkg_installed/<triplet>/bin
        potential_include = dll_path.parent.parent / 'include'
        if potential_include.exists() and potential_include.is_dir():
            # Verify it has header files
            if any(potential_include.glob('*.h')) or any(potential_include.glob('*.hpp')):
                return potential_include
    
    # Strategy 2: System DLLs - check Windows SDK
    if dll_path.parent.name.lower() in ['system32', 'syswow64']:
        # Common Windows SDK locations
        sdk_paths = [
            Path(r'C:\Program Files (x86)\Windows Kits\10\Include'),
            Path(r'C:\Program Files (x86)\Microsoft SDKs\Windows'),
        ]
        
        # Try to find latest SDK version
        for sdk_base in sdk_paths:
            if sdk_base.exists():
                # Find newest version directory
                versions = [v for v in sdk_base.iterdir() if v.is_dir()]
                if versions:
                    latest = sorted(versions, reverse=True)[0]
                    # Optimization: Only return 'um' (User Mode) directory
                    # Scanning the whole SDK takes forever due to WinRT/CPP headers
                    um_path = latest / 'um'
                    if um_path.exists():
                        return um_path
                    return latest
    
    # Strategy 3: Check environment variable hints
    include_path = os.environ.get('INCLUDE', '')
    if include_path:
        # INCLUDE is semicolon-separated on Windows
        for path in include_path.split(';'):
            path = Path(path.strip())
            if path.exists() and path.is_dir():
                return path
    
    return None

# Test binaries for artifact generation
ARTIFACTS_TESTS = [
    # sqlite3 (native DLL - non-system)
    {
        'path': r'C:\Users\evanw\Downloads\capstone_project\mcp-factory\tests\fixtures\vcpkg_installed\x64-windows\bin\sqlite3.dll',
        'name': 'sqlite3',
        'category': 'native_dll'
    },
    # zstd (native DLL - non-system)
    {
        'path': r'C:\Users\evanw\Downloads\capstone_project\mcp-factory\tests\fixtures\vcpkg_installed\x64-windows\bin\zstd.dll',
        'name': 'zstd',
        'category': 'native_dll'
    },
    # System.dll (.NET assembly)
    {
        'path': r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.dll',
        'name': 'System',
        'category': 'dotnet'
    },
    # lsass.exe (RPC executable)
    {
        'path': r'C:\Windows\System32\lsass.exe',
        'name': 'lsass',
        'category': 'rpc_exe'
    },
    # oleaut32.dll (COM)
    {
        'path': r'C:\Windows\System32\oleaut32.dll',
        'name': 'oleaut32',
        'category': 'com'
    },
    # svchost.exe (executable - if it works)
    {
        'path': r'C:\Windows\System32\notepad.exe',
        'name': 'notepad',
        'category': 'exe'
    }
]


def generate_artifacts(args=None):
    """Generate artifacts with new 4-tier confidence system"""
    artifacts_dir = Path(__file__).parent.parent / 'artifacts'
    artifacts_dir.mkdir(exist_ok=True)
    
    safe_mode = args.safe if args else False
    log_dir = Path("logs")
    if safe_mode:
        log_dir.mkdir(exist_ok=True)
        print(f"Running in safe mode - outputs redirected to {log_dir.absolute()}")
    
    print("="*70)
    print("ARTIFACT GENERATION - 4-TIER CONFIDENCE SYSTEM")
    print("="*70)
    print("\nConfidence Levels:")
    print("  GUARANTEED: Complete signature, can invoke immediately")
    print("  HIGH:       Verified source, signature lookup needed")
    print("  MEDIUM:     API patterns or heuristics")
    print("  LOW:        Minimal information")
    print()
    
    results = []
    
    for test in ARTIFACTS_TESTS:
        binary_path = Path(test['path'])
        
        print(f"Processing {test['name']} ({test['category']})... ", end='', flush=True)

        if not binary_path.exists():
            print(f"SKIPPED (not found: {binary_path})")
            continue
            
        # Create output directory
        output_dir = artifacts_dir / test['name']
        output_dir.mkdir(exist_ok=True)
        
        # Auto-discover header files
        headers_path = find_headers_for_dll(binary_path)
        
        # Build argv for analysis
        original_argv = sys.argv
        sys.argv = [
            'main.py',
            '--dll', str(binary_path),
            '--out', str(output_dir)
        ]
        
        # Add headers if found
        if headers_path:
            sys.argv.extend(['--headers', str(headers_path)])
            if not safe_mode:
                print(f"[HEADERS] Auto-discovered: {headers_path}")
        
        try:
            if safe_mode:
                log_file = log_dir / f"{test['name']}_generation.log"
                with open(log_file, 'w', encoding='utf-8') as f:
                    with redirect_stdout(f), redirect_stderr(f):
                        result = analyze_main()
                print("DONE (logs saved)")
            else:
                print("\n")
                result = analyze_main()
                print("DONE")
                
            if result != 0 and result is not None:
                print(f"  [ERROR] Analysis failed with code {result}")
                continue
                
        except Exception as e:
            print(f"FAILED: {e}")
            if safe_mode:
                 # Print exception to console too if in safe mode
                print(f"  Error details: {e}")
            continue
        finally:
             sys.argv = original_argv
        
        # Find generated MCP JSON
        json_files = list(output_dir.glob('*_mcp.json'))
        if not json_files:
            if not safe_mode: print(f"  [ERROR] No MCP JSON generated")
            continue
        
        json_path = json_files[0]
        
        # Load JSON
        with open(json_path) as f:
            data = json.load(f)
        
        invocables = data.get('invocables', [])
        
        # Analyze confidence distribution
        from collections import Counter
        conf_dist = Counter(inv.get('confidence', 'unknown') for inv in invocables)
        
        # Generate CSV version
        csv_path = output_dir / json_path.name.replace('_mcp.json', '.csv')
        generate_csv(data, csv_path)
        
        # Copy to artifacts root with prefix
        prefix = f"{test['name']}_"
        
        # Copy JSON
        final_json = artifacts_dir / f"{prefix}{json_path.name}"
        with open(final_json, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Copy CSV  
        final_csv = artifacts_dir / f"{prefix}{csv_path.name}"
        with open(csv_path) as src, open(final_csv, 'w') as dst:
            dst.write(src.read())
        
        results.append({
            'name': test['name'],
            'category': test['category'],
            'invocables': len(invocables),
            'confidence': dict(conf_dist),
            'json': str(final_json.name),
            'csv': str(final_csv.name)
        })
    
    # Summary
    print(f"\n{'='*70}")
    print("ARTIFACT GENERATION SUMMARY")
    print(f"{'='*70}\n")
    
    print("Generated artifacts by category:\n")
    
    by_category = {}
    for r in results:
        cat = r['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(r)
    
    for cat, items in sorted(by_category.items()):
        print(f"{cat.upper().replace('_', ' ')}:")
        for item in items:
            print(f"  {item['name']:15s} - {item['invocables']:6,} invocables")
            print(f"    JSON: {item['json']}")
            print(f"    CSV:  {item['csv']}")
            
            # Show confidence breakdown
            for conf in ['guaranteed', 'high', 'medium', 'low']:
                if conf in item['confidence']:
                    count = item['confidence'][conf]
                    pct = (count / item['invocables'] * 100) if item['invocables'] else 0
                    print(f"      {conf:12s}: {count:5,} ({pct:5.1f}%)")
            print()
    
    print(f"All artifacts saved to: {artifacts_dir}")


def generate_csv(mcp_json: dict, csv_path: Path):
    """Generate CSV from MCP JSON"""
    invocables = mcp_json.get('invocables', [])
    
    if not invocables:
        return
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        # Determine columns from first invocable
        sample = invocables[0]
        columns = ['name', 'kind', 'confidence', 'ordinal', 'rva', 'signature']
        
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        
        for inv in invocables:
            # Flatten signature if it's a dict
            row = inv.copy()
            if isinstance(row.get('signature'), dict):
                row['signature'] = row['signature'].get('full_prototype', '')
            
            writer.writerow(row)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate artifacts with confidence scoring")
    parser.add_argument("--safe", action="store_true", help="Run safely by capturing output to logs")
    args = parser.parse_args()
    
    generate_artifacts(args)
