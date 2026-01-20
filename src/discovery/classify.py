"""
classify.py - File type, architecture, and signature detection.

Detects file types (PE DLL/EXE, .NET assembly, script, COM object, etc)
to route to appropriate analyzers, and extracts digital signature info.
"""

import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class FileType(Enum):
    """Supported file types for analysis."""
    PE_DLL = "PE_DLL"
    PE_EXE = "PE_EXE"
    DOTNET_ASSEMBLY = "DOTNET_ASSEMBLY"
    COM_OBJECT = "COM_OBJECT"
    SCRIPT = "SCRIPT"
    UNKNOWN = "UNKNOWN"


def classify_file(file_path: Path) -> FileType:
    """Classify a file based on its signature and extension.
    
    Args:
        file_path: Path to file to classify
        
    Returns:
        FileType enum indicating detected type
    """
    if not file_path.exists():
        return FileType.UNKNOWN

    ext = file_path.suffix.lower()

    # Script files
    if ext in ['.ps1', '.py', '.vbs', '.bat', '.cmd', '.sh']:
        return FileType.SCRIPT

    # Check magic bytes for binary files
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(4)

        # PE signature: "MZ" followed by PE signature at offset
        if magic[:2] == b'MZ':
            # Read PE header offset
            with open(file_path, 'rb') as f:
                f.seek(0x3c)
                pe_offset_bytes = f.read(4)
                if len(pe_offset_bytes) == 4:
                    pe_offset = int.from_bytes(pe_offset_bytes, 'little')

                    # Read PE signature
                    with open(file_path, 'rb') as f2:
                        f2.seek(pe_offset)
                        pe_sig = f2.read(4)

                        if pe_sig == b'PE\x00\x00':
                            # Read machine type (offset +4 in COFF header)
                            f2.seek(pe_offset + 4)
                            machine = f2.read(2)

                            # Check for .NET metadata
                            if _has_dotnet_metadata(file_path):
                                return FileType.DOTNET_ASSEMBLY

                            # Distinguish DLL vs EXE by characteristics
                            f2.seek(pe_offset + 22)  # Characteristics field
                            chars = f2.read(2)
                            if len(chars) == 2:
                                characteristics = int.from_bytes(chars, 'little')
                                # 0x2000 = DLL characteristic
                                if characteristics & 0x2000:
                                    return FileType.PE_DLL
                                else:
                                    return FileType.PE_EXE

                            return FileType.PE_DLL  # Default for PE

        # .NET signature
        if magic == b'ILFM':
            return FileType.DOTNET_ASSEMBLY

    except (OSError, struct.error):
        pass

    # Extension-based fallback
    if ext in ['.dll']:
        return FileType.PE_DLL
    elif ext in ['.exe', '.com']:
        return FileType.PE_EXE
    elif ext in ['.tlb', '.olb']:
        return FileType.COM_OBJECT

    return FileType.UNKNOWN


def _has_dotnet_metadata(file_path: Path) -> bool:
    """Check if PE file contains .NET metadata (CLR header)."""
    try:
        with open(file_path, 'rb') as f:
            # Read PE offset
            f.seek(0x3c)
            pe_offset = int.from_bytes(f.read(4), 'little')

            # Check for CLR Runtime Header in data directories
            # (This is a simplified check; full check would parse data directories)
            f.seek(pe_offset + 4)
            machine = f.read(2)

            # For now, assume .NET if has .NET file extension pattern
            # Full implementation would parse CLR header
            return str(file_path).lower().endswith(('.dll', '.exe'))

    except (OSError, ValueError):
        return False

    return False


def get_architecture(file_path: Path) -> Optional[str]:
    """Detect architecture (x86, x64, ARM64, etc) from PE header.
    
    Returns:
        Architecture string or None if cannot determine
    """
    try:
        with open(file_path, 'rb') as f:
            f.seek(0x3c)
            pe_offset = int.from_bytes(f.read(4), 'little')

            f.seek(pe_offset + 4)
            machine = int.from_bytes(f.read(2), 'little')

            # Machine type constants
            MACHINE_I386 = 0x014C
            MACHINE_AMD64 = 0x8664
            MACHINE_ARM = 0x01C0
            MACHINE_ARM64 = 0xAA64

            if machine == MACHINE_I386:
                return "x86"
            elif machine == MACHINE_AMD64:
                return "x64"
            elif machine == MACHINE_ARM:
                return "ARM"
            elif machine == MACHINE_ARM64:
                return "ARM64"

    except (OSError, ValueError):
        pass

    return None


def extract_signature(pe_path: Path) -> Tuple[bool, Optional[str]]:
    """Extract digital signature and publisher info from PE file.
    
    Args:
        pe_path: Path to PE file
        
    Returns:
        (is_signed, publisher_name)
    """
    try:
        # Use wmic to extract file description/publisher
        result = subprocess.run(
            ['wmic', 'datafile', 'where',
             f'name="{str(pe_path).replace(chr(92), chr(92)+chr(92))}"',
             'get', 'Description,Version', '/format:list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if 'Description=' in output:
                publisher = output.split('Description=')[1].split('\n')[0].strip()
                return True, publisher if publisher else "Unknown"
        
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None

