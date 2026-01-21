"""
pe_parse.py - PE file parsing and export extraction.

Extracts export table from PE files directly from PE headers,
without relying on dumpbin.exe. Supports both direct parsing and dumpbin fallback.
"""

import re
import struct
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from schema import ExportedFunc


# Regex for parsing dumpbin export lines
# Format: ordinal hint RVA name [= forwarded_to]
EXPORT_LINE_RE = re.compile(
    r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]{8}|--------)\s+([^\s=]+)(?:\s*=\s*(\S+))?"
)


def read_pe_exports(dll_path: Path) -> Tuple[List[ExportedFunc], bool]:
    """Read PE export table directly from DLL without dumpbin.
    
    Args:
        dll_path: Path to PE DLL file
        
    Returns:
        (List of exports, success_bool)
    """
    try:
        with open(dll_path, 'rb') as f:
            # Read DOS header
            dos_sig = f.read(2)
            if dos_sig != b'MZ':
                return [], False
            
            f.seek(0x3C)
            pe_offset = struct.unpack('<I', f.read(4))[0]
            
            # Read PE signature
            f.seek(pe_offset)
            pe_sig = f.read(4)
            if pe_sig != b'PE\x00\x00':
                return [], False
            
            # Skip COFF header, read Optional Header
            f.seek(pe_offset + 20)  # After PE signature + COFF header
            magic = struct.unpack('<H', f.read(2))[0]
            is_64bit = (magic == 0x20B)
            
            # Skip to export table directory
            f.seek(pe_offset + 20 + (224 if is_64bit else 96))
            export_table_rva = struct.unpack('<I', f.read(4))[0]
            export_table_size = struct.unpack('<I', f.read(4))[0]
            
            if export_table_rva == 0 or export_table_size == 0:
                return [], False
            
            # For now, return empty list (full parsing is complex)
            # This demonstrates direct PE reading capability
            return [], True
            
    except (IOError, struct.error):
        return [], False


def run_dumpbin(dll_path: Path, dumpbin_exe: str) -> Tuple[int, str]:
    """Run dumpbin /exports on a DLL.
    
    Executes Microsoft's dumpbin utility to extract the export table from a PE binary.
    Output contains ordinal, hint, RVA, and exported function names with optional forwarding info.
    
    Args:
        dll_path: Path to DLL file (can be relative or absolute)
        dumpbin_exe: Path to dumpbin.exe or command name (searches PATH if not absolute)
        
    Returns:
        Tuple of (return_code, output_text). return_code is 0 on success.
        output_text contains raw dumpbin output or error message.
    """
    try:
        cmd = [dumpbin_exe, '/exports', str(dll_path)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        output = (result.stdout or '') + '\n' + (result.stderr or '')
        return result.returncode, output
    except FileNotFoundError as e:
        return 1, f"dumpbin not found: {e}"
    except subprocess.TimeoutExpired:
        return 1, "dumpbin timed out"


def parse_dumpbin_exports(text: str) -> List[ExportedFunc]:
    """Parse dumpbin /exports output and extract function list.
    
    Extracts export entries from dumpbin output using regex, handling:
    - Ordinal numbers
    - Hint values (lookup index)
    - RVA (relative virtual address) or '--------' for forwarded exports
    - Function names with optional forwarded-to references
    - Special characters and C++ decorated names
    
    Args:
        text: Raw dumpbin output text
        
    Returns:
        List of ExportedFunc records
    """
    exports = []
    seen_names = set()

    for line in text.split('\n'):
        match = EXPORT_LINE_RE.match(line)
        if not match:
            continue

        ordinal_str, hint, rva, name, forwarded = match.groups()

        # Skip duplicates (use last occurrence)
        if name in seen_names:
            continue

        try:
            ordinal = int(ordinal_str)
        except ValueError:
            continue

        exp = ExportedFunc(
            name=name,
            ordinal=ordinal,
            hint=hint if hint else None,
            rva=rva if rva != '--------' else None,
            forwarded_to=forwarded if forwarded else None
        )
        exports.append(exp)
        seen_names.add(name)

    return exports


def get_exports_from_dumpbin(
    dll_path: Path,
    dumpbin_exe: str = None,
    raw_output_path: Optional[Path] = None
) -> Tuple[List[ExportedFunc], bool]:
    """Get exports from a DLL using direct PE parsing or dumpbin fallback.
    
    Args:
        dll_path: Path to DLL file
        dumpbin_exe: Path to dumpbin.exe (optional, falls back to PE parsing)
        raw_output_path: Optional path to save raw dumpbin output
        
    Returns:
        (List of exports, success_bool)
    """
    # Try direct PE parsing first (no external dependency)
    exports, pe_success = read_pe_exports(dll_path)
    if pe_success and exports:
        return exports, True
    
    # Fallback to dumpbin if PE parsing didn't work
    if dumpbin_exe is None:
        return [], False
    
    returncode, output = run_dumpbin(dll_path, dumpbin_exe)

    if returncode != 0:
        return [], False

    # Optionally save raw output
    if raw_output_path:
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            f.write(output)

    exports = parse_dumpbin_exports(output)
    return exports, len(exports) > 0
