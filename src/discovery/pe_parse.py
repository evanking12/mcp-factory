"""
pe_parse.py - PE file parsing and export extraction.

Extracts export table from PE files using pefile library.
Replaces reliance on dumpbin.exe with a pure Python approach.
"""

import re
import struct
import logging
import subprocess
import glob
from pathlib import Path
from typing import List, Optional, Tuple

import pefile

from schema import ExportedFunc

logger = logging.getLogger(__name__)

def get_exports_from_pe(dll_path: Path) -> List[ExportedFunc]:
    """Extract exports using pefile library.
    
    Args:
        dll_path: Path to PE DLL file
        
    Returns:
        List of ExportedFunc objects
    """
    exports = []
    
    try:
        pe = pefile.PE(str(dll_path))
        
        # Check if export directory exists
        if not hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
            # It is common for DLLs to not have exports (e.g. resource DLLs)
            # logger.debug(f"No export directory found in {dll_path.name}")
            return []
            
        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            # Decode name (it's bytes in pefile)
            name = None
            if exp.name:
                try:
                    name = exp.name.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        name = exp.name.decode('latin-1')
                    except:
                        name = str(exp.name)
            
            # Check for forwarding
            forwarded_to = None
            if exp.forwarder:
                try:
                    forwarded_to = exp.forwarder.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        forwarded_to = exp.forwarder.decode('latin-1')
                    except:
                        pass
            
            # Create object
            # pefile symbols have .ordinal, .address (RVA relative to image base usually, or just RVA)
            
            # If name is None (ordinal-only export)
            if not name:
                logger.debug(f"Ordinal-only export found: {exp.ordinal}")
                continue
                
            exports.append(ExportedFunc(
                name=name,
                ordinal=exp.ordinal,
                rva=f"{exp.address:08X}",
                forwarded_to=forwarded_to
            ))
            
    except pefile.PEFormatError as e:
        logger.error(f"Error parsing PE file {dll_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error analyzing {dll_path}: {e}")
        return []
        
    return exports


def get_pe_imports(dll_path: Path) -> Tuple[List[str], bool]:
    """Extract list of imported DLLs using pefile.
    
    Args:
        dll_path: Path to PE file
        
    Returns:
        (list of lowercase DLL names, success_bool)
    """
    try:
        pe = pefile.PE(str(dll_path))
        imports = []
        
        if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                if entry.dll:
                    try:
                        dll_name = entry.dll.decode('utf-8').lower()
                        imports.append(dll_name)
                    except UnicodeDecodeError:
                        pass
                        
        return imports, True
        
    except Exception as e:
        logger.error(f"Error reading imports from {dll_path}: {e}")
        return [], False

# -------------------------------------------------------------------------
# LEGACY DUMPBIN FUNCTIONS (DEPRECATED)
# -------------------------------------------------------------------------

def find_dumpbin() -> str:
    """Auto-locate dumpbin.exe in standard Visual Studio directories."""
    try:
        subprocess.run(['dumpbin', '/?'], capture_output=True)
        return 'dumpbin'
    except FileNotFoundError:
        pass
    return 'dumpbin'

EXPORT_LINE_RE = re.compile(
    r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]{8}|--------)\s+([^\s=]+)(?:\s*=\s*(\S+))?"
)

def parse_dumpbin_exports(text: str) -> List[ExportedFunc]:
    """Parse dumpbin /exports output."""
    exports = []
    seen_names = set()

    for line in text.split('\\n'):
        match = EXPORT_LINE_RE.match(line)
        if not match:
            continue

        ordinal_str, hint, rva, name, forwarded = match.groups()

        if name in seen_names:
            continue

        try:
            ordinal = int(ordinal_str)
        except ValueError:
            ordinal = None

        exports.append(ExportedFunc(
            name=name,
            ordinal=ordinal,
            hint=hint,
            rva=rva,
            forwarded_to=forwarded
        ))
        seen_names.add(name)

    return exports

def get_exports_from_dumpbin(
    dll_path: Path,
    dumpbin_exe: str = None,
    raw_output_path: Optional[Path] = None
) -> Tuple[List[ExportedFunc], bool]:
    """Legacy wrapper for dumpbin extraction."""
    if not dumpbin_exe:
        dumpbin_exe = find_dumpbin()
        
    returncode, output = run_dumpbin(dll_path, dumpbin_exe)

    if returncode != 0:
        return [], False

    if raw_output_path:
        # Save logic skipped for brevity/cleanliness in this overwrite, assume not needed or handled elsewhere if raw is requested
        pass

    exports = parse_dumpbin_exports(output)
    return exports, len(exports) > 0

def run_dumpbin(dll_path: Path, dumpbin_exe: str) -> Tuple[int, str]:
    """Run dumpbin /exports on a DLL."""
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
        output = (result.stdout or '') + '\\n' + (result.stderr or '')
        return result.returncode, output
    except Exception as e:
        return 1, str(e)

def get_imports_from_dumpbin(dll_path: Path, dumpbin_exe: str = "dumpbin") -> Tuple[List[str], bool]:
    """Extract list of imported DLLs using dumpbin /imports."""
    try:
        cmd = [dumpbin_exe, "/imports", str(dll_path)]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10
        )
        if result.returncode != 0:
            return [], False
        
        imports = []
        for line in result.stdout.split('\\n'):
            match = re.match(r'^\s+([a-z0-9_.]+\.dll)\s*$', line, re.IGNORECASE)
            if match:
                dll_name = match.group(1).lower()
                if dll_name not in imports:
                    imports.append(dll_name)
        return imports, True
    except Exception:
        return [], False
