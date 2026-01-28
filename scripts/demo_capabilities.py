"""
Demo Capabilities Script
------------------------
Concise demonstration of MCP Factory's analysis capabilities.
Analyzes Native, .NET, and COM binaries with color-coded confidence metrics.
"""

import sys
import json
import logging
import io  # Added
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import os
import collections

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "discovery"))

# Import main directly
from main import main as analyze_main

# --- Colors ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Targets to analyze
TARGETS = [
    {
        "name": "kernel32.dll",
        "path": r"C:\Windows\System32\kernel32.dll", 
        "type": "System API"
    },
    {
        "name": "user32.dll",
        "path": r"C:\Windows\System32\user32.dll", 
        "type": "UI System API"
    },
    {
        "name": "rpcrt4.dll",
        "path": r"C:\Windows\System32\rpcrt4.dll", 
        "type": "RPC Runtime"
    },
    {
        "name": "System.dll",
        "path": r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.dll",
        "type": ".NET Assembly"
    },
    {
        "name": "mscorlib.dll",
        "path": r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\mscorlib.dll",
        "type": ".NET Core Lib"
    },
    {
        "name": "oleaut32.dll", 
        "path": r"C:\Windows\System32\oleaut32.dll", 
        "type": "COM Server"
    },
    {
        "name": "stdole2.tlb", 
        "path": r"C:\Windows\System32\stdole2.tlb", 
        "type": "Type Library"
    },
    {
        "name": "ws2_32.dll",
        "path": r"C:\Windows\System32\ws2_32.dll",
        "type": "Network API"
    },
    {
        "name": "shell32.dll",
        "path": r"C:\Windows\System32\shell32.dll",
        "type": "Hybrid COM/Native"
    }
]

def get_majority_confidence(invocables):
    """Determine majority confidence level and associated color."""
    if not invocables:
        return "NONE", Colors.RED

    counts = collections.Counter(inv.get("confidence", "low").lower() for inv in invocables)
    total = len(invocables)
    
    # Order of precedence for "majority" label
    # If > 50% are guaranteed, it's Guaranteed.
    # If > 50% are High+, it's High. 
    # Etc.
    
    guaranteed = counts.get("guaranteed", 0)
    high = counts.get("high", 0)
    medium = counts.get("medium", 0)
    low = counts.get("low", 0)
    
    if guaranteed / total > 0.5:
        return "GUARANTEED", Colors.GREEN
    elif (guaranteed + high) / total > 0.5:
        return "HIGH", Colors.CYAN
    elif (guaranteed + high + medium) / total > 0.5:
        return "MEDIUM", Colors.YELLOW
    else:
        return "LOW", Colors.RED

def run_demo():
    print(f"{Colors.HEADER}{Colors.BOLD}MCP FACTORY CAPABILITIES DEMO{Colors.ENDC}")
    print(f"{Colors.HEADER}============================={Colors.ENDC}\n")
    
    output_base = Path("demo_output")
    output_base.mkdir(exist_ok=True)
    
    logging.disable(logging.CRITICAL)
    
    print(f"{'Target':<20} | {'Type':<20} | {'Count':<8} | {'Confidence':<12}")
    print("-" * 70)
    
    for target in TARGETS:
        path = Path(target["path"])
        if not path.exists():
            continue
            
        output_dir = output_base / target["name"]
        output_dir.mkdir(exist_ok=True)
        
        # Prepare args
        sys.argv = [
            "main.py",
            "--dll", str(path),
            "--out", str(output_dir)
        ]
        
        try:
            # Silence output unless error occurs
            # We capture stdout/stderr to print only on failure
            capture_io = io.StringIO()
            with redirect_stdout(capture_io), redirect_stderr(capture_io):
                try:
                    exit_code = analyze_main()
                except SystemExit as e:
                    exit_code = e.code
                except Exception as e:
                    print(f"Exception: {e}")
                    raise

            # Read results
            json_files = list(output_dir.glob("*_mcp.json"))
            if json_files:
                with open(json_files[0], 'r') as f:
                    data = json.load(f)
                    
                invocables = data.get("invocables", [])
                count = len(invocables)
                
                conf_label, conf_color = get_majority_confidence(invocables)
                
                print(f"{target['name']:<20} | {target['type']:<20} | {count:<8} | {conf_color}{conf_label:<12}{Colors.ENDC}")

            else:
                # Print captured output to help debug "FAILED" state
                print(f"{target['name']:<20} | {Colors.RED}FAILED{Colors.ENDC}")
                # Indent error output for readability
                error_log = capture_io.getvalue().strip()
                if error_log:
                    print(f"{Colors.RED}  Error Log:{Colors.ENDC}")
                    for line in error_log.splitlines()[-5:]: # Show last 5 lines
                        print(f"    {line}")
                
        except Exception as e:
            print(f"{Colors.RED}ERROR: {e}{Colors.ENDC}")
            
    print(f"\n{Colors.BLUE}Demo Complete. Artifacts saved to ./demo_output/{Colors.ENDC}")

if __name__ == "__main__":
    run_demo()
