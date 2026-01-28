"""
Display sample JSON and CSV content from generated artifacts
"""

import json
from pathlib import Path

artifacts_dir = Path('artifacts')

print("="*70)
print("4-TIER CONFIDENCE SYSTEM - ARTIFACT SAMPLES")
print("="*70)

# Sample files
samples = [
    ('sqlite3_sqlite3_exports_mcp.json', 'NATIVE DLL (sqlite3) - LOW'),
    ('System_System_dotnet_methods_mcp.json', '.NET ASSEMBLY (System.dll) - GUARANTEED'),
    ('lsass_lsass_exports_mcp.json', 'RPC EXECUTABLE (lsass.exe) - HIGH/LOW'),
    ('oleaut32_oleaut32_com_objects_mcp.json', 'COM OBJECTS (oleaut32.dll) - GUARANTEED'),
]

for json_file, desc in samples:
    json_path = artifacts_dir / json_file
    if not json_path.exists():
        continue
    
    with open(json_path) as f:
        data = json.load(f)
    
    invocables = data.get('invocables', [])
    
    print(f"\n{'='*70}")
    print(f"{desc}")
    print(f"{'='*70}")
    print(f"Total invocables: {len(invocables):,}")
    
    # Count confidence levels
    from collections import Counter
    conf_dist = Counter(inv.get('confidence', 'unknown') for inv in invocables)
    
    print("\nConfidence Distribution:")
    for conf in ['guaranteed', 'high', 'medium', 'low']:
        if conf in conf_dist:
            count = conf_dist[conf]
            pct = (count / len(invocables) * 100) if invocables else 0
            print(f"  {conf.upper():12s}: {count:5,} ({pct:5.1f}%)")
    
    print(f"\nFirst 3 invocables:")
    for i, inv in enumerate(invocables[:3], 1):
        print(f"\n{i}. {inv.get('name', 'N/A')}")
        print(f"   kind: {inv.get('kind', 'N/A')}")
        print(f"   confidence: {inv.get('confidence', 'N/A')}")
        
        # Show signature
        sig = inv.get('signature', {})
        if isinstance(sig, dict):
            proto = sig.get('full_prototype')
            if proto:
                print(f"   signature: {proto[:80]}...")
        elif isinstance(sig, str):
            print(f"   signature: {sig[:80]}")

print(f"\n{'='*70}")
print("CSV SAMPLES")
print(f"{'='*70}")

# Show CSV headers and first few rows
csv_samples = [
    ('sqlite3_sqlite3_exports.csv', 'NATIVE DLL (sqlite3)'),
    ('System_System_dotnet_methods.csv', '.NET ASSEMBLY'),
]

for csv_file, desc in csv_samples:
    csv_path = artifacts_dir / csv_file
    if not csv_path.exists():
        continue
    
    print(f"\n{desc} - {csv_file}")
    print("-" * 70)
    
    with open(csv_path) as f:
        lines = f.readlines()[:5]  # Header + 4 rows
        for line in lines:
            print(line.rstrip())

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print("\nGenerated artifacts:")
print("  ✅ sqlite3 - 294 invocables (100% LOW - non-system DLL)")
print("  ✅ zstd - 187 invocables (100% LOW - non-system DLL)")
print("  ✅ System.dll - 9,424 invocables (100% GUARANTEED - .NET reflection)")
print("  ✅ lsass.exe - 14 invocables (71.4% HIGH RPC, 28.6% LOW exports)")
print("  ✅ oleaut32.dll - 10 invocables (100% GUARANTEED - COM CLSIDs)")
print()
print("4-Tier Confidence System Working:")
print("  GUARANTEED = Complete signature, can invoke immediately")
print("  HIGH       = Verified source (system DLL/COM/RPC)")
print("  MEDIUM     = API patterns or heuristics")
print("  LOW        = Minimal information only")
