import json
import sys
from pathlib import Path

def analyze_anomalies(root_dir):
    print(f"Scanning {root_dir}...")
    root = Path(root_dir)
    if not root.exists():
        print(f"Directory {root_dir} not found.")
        return
    
    files = list(root.rglob("*.json"))
    print(f"Scanned {len(files)} JSON files.\n")
    
    anomalies = []
    
    for p in files:
        name = p.name
        
        # Check for Legacy filenames
        if "_dotnet_methods.json" in name and "_mcp.json" not in name:
            anomalies.append(f"[Redundancy] Legacy file found: {p}")
            continue
            
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check Schema Version
            if data.get("schema_version") != "2.0.0":
                anomalies.append(f"[Invalid Schema] {p} has version {data.get('schema_version')}")
                
            # Check for Empty Invocables (Noise) - though strict hygiene means file shouldn't exist
            invocables = data.get("invocables", [])
            if not invocables:
                 anomalies.append(f"[Noise] Empty invocables list in: {p}")
                 
        except Exception as e:
            anomalies.append(f"[Corrupt] Failed to parse {p}: {e}")
            
    if anomalies:
        print("Anomalies Found:")
        for a in anomalies:
            print(a)
        sys.exit(1)
    else:
        print("No anomalies found.")
        sys.exit(0)

if __name__ == "__main__":
    analyze_anomalies("validation_output")