"""
com_scan.py - COM object discovery and type library analysis.

Stub for future implementation of:
- Registry scanning (CLSID, AppID, ProgID)
- Type library (TLB) parsing
- IDispatch enumeration at runtime

Current implementation is minimal, placeholder for future work.
"""

from pathlib import Path
from typing import List

from schema import ExportedFunc


def scan_com_registry(target_name: str) -> List[dict]:
    """Scan registry for COM objects (stub).
    
    Args:
        target_name: Name of target DLL/executable
        
    Returns:
        List of COM objects found
    """
    # Placeholder for registry scanning
    # Would search HKEY_LOCAL_MACHINE\Software\Classes for CLSID entries
    # matching the target DLL
    return []


def parse_type_library(tlb_path: Path) -> List[dict]:
    """Parse type library file (stub).
    
    Args:
        tlb_path: Path to .tlb file
        
    Returns:
        List of interface/method definitions
    """
    # Placeholder for TLB parsing
    # Would extract interface definitions, method signatures, etc.
    return []


def enumerate_idispatch(clsid: str) -> List[dict]:
    """Enumerate IDispatch methods at runtime (stub).
    
    Args:
        clsid: CLSID of COM object to enumerate
        
    Returns:
        List of dispatchable methods
    """
    # Placeholder for runtime enumeration
    # Would instantiate COM object and query IDispatch
    return []
