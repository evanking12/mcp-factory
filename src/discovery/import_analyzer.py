"""
import_analyzer.py - Import Address Table (IAT) analysis for PE/COFF binaries.

Analyzes what DLLs and functions a binary imports to determine capabilities:
- Network operations (WinHTTP, WinINet, Winsock)
- COM/RPC usage
- Cryptography
- File system operations
- Registry access
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)


# Capability detection based on imported DLLs
CAPABILITY_DLLS = {
    'networking': {
        'ws2_32.dll', 'wsock32.dll',  # Winsock
        'winhttp.dll',                 # WinHTTP
        'wininet.dll',                 # WinINet
        'iphlpapi.dll',                # IP Helper
        'netapi32.dll',                # Network API
    },
    'com': {
        'ole32.dll',                   # COM core
        'oleaut32.dll',                # COM automation
        'combase.dll',                 # Modern COM
    },
    'rpc': {
        'rpcrt4.dll',                  # RPC runtime
        'rpcns4.dll',                  # RPC name service
    },
    'crypto': {
        'bcrypt.dll',                  # BCrypt
        'crypt32.dll',                 # Crypto API
        'ncrypt.dll',                  # CNG
        'cryptsp.dll',                 # Crypto service provider
    },
    'registry': {
        'advapi32.dll',                # Advanced API (includes registry)
    },
    'filesystem': {
        'kernel32.dll',                # File I/O
        'kernelbase.dll',              # Base kernel
    },
    'security': {
        'secur32.dll',                 # Security support
        'sspicli.dll',                 # SSPI client
    },
    'database': {
        'odbc32.dll',                  # ODBC
        'oledb32.dll',                 # OLE DB
    }
}

# Key network functions to detect
NETWORK_FUNCTIONS = {
    # WinHTTP
    'WinHttpOpen', 'WinHttpConnect', 'WinHttpOpenRequest',
    'WinHttpSendRequest', 'WinHttpReceiveResponse', 'WinHttpReadData',
    'WinHttpSetOption', 'WinHttpQueryOption',
    
    # WinINet
    'InternetOpenA', 'InternetOpenW', 'InternetConnectA', 'InternetConnectW',
    'HttpOpenRequestA', 'HttpOpenRequestW', 'HttpSendRequestA', 'HttpSendRequestW',
    'InternetReadFile', 'InternetCloseHandle',
    
    # Winsock
    'WSAStartup', 'WSACleanup', 'socket', 'connect', 'bind', 'listen',
    'send', 'recv', 'sendto', 'recvfrom', 'closesocket',
    'getaddrinfo', 'gethostbyname', 'inet_addr',
}

# RPC functions
RPC_FUNCTIONS = {
    'RpcServerRegisterIf', 'RpcServerRegisterIfEx', 'RpcServerListen',
    'RpcServerUseProtseq', 'RpcServerUseProtseqEp',
    'RpcBindingFromStringBinding', 'RpcStringBindingCompose',
    'RpcEpRegister', 'RpcEpResolveBinding',
    'NdrClientCall2', 'NdrServerCall2',
}

# COM functions
COM_FUNCTIONS = {
    'CoInitialize', 'CoInitializeEx', 'CoCreateInstance',
    'CoCreateInstanceEx', 'CoGetClassObject', 'CoRegisterClassObject',
    'IDispatch', 'IUnknown',
}


def parse_imports_dumpbin(dll_path: Path, dumpbin_path: str = "dumpbin") -> Dict[str, List[str]]:
    """Parse imports using dumpbin /IMPORTS.
    
    Args:
        dll_path: Path to PE file
        dumpbin_path: Path to dumpbin.exe
        
    Returns:
        Dict mapping DLL names to list of imported functions
    """
    try:
        result = subprocess.run(
            [dumpbin_path, "/IMPORTS", str(dll_path)],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode != 0:
            logger.warning(f"dumpbin failed with code {result.returncode}")
            return {}
        
        return _parse_dumpbin_imports(result.stdout)
        
    except FileNotFoundError:
        logger.warning(f"dumpbin not found at: {dumpbin_path}")
        return {}
    except subprocess.TimeoutExpired:
        logger.warning(f"dumpbin timeout for {dll_path}")
        return {}
    except Exception as e:
        logger.warning(f"Error parsing imports: {e}")
        return {}


def _parse_dumpbin_imports(output: str) -> Dict[str, List[str]]:
    """Parse dumpbin /IMPORTS output.
    
    Expected format:
        Section contains the following imports:
        
        KERNEL32.dll
                   402070 Import Address Table
                   402208 Import Name Table
                        0 time date stamp
                        0 Index of first forwarder reference
        
              14F CreateFileW
              1A3 GetLastError
    """
    imports = {}
    current_dll = None
    
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # DLL name line (e.g., "KERNEL32.dll")
        if line.endswith('.dll') and not line.startswith('Dump of file'):
            current_dll = line.lower()
            if current_dll not in imports:
                imports[current_dll] = []
        
        # Function import (starts with hex number or whitespace + hex)
        elif current_dll and line:
            # Format: "14F CreateFileW" or just "CreateFileW"
            parts = line.split(maxsplit=1)
            if len(parts) >= 1:
                # Last part is function name
                func_name = parts[-1].strip()
                # Skip obvious non-function lines
                if func_name and not func_name.startswith('0x') and \
                   not func_name.isdigit() and \
                   'Import Address Table' not in func_name:
                    imports[current_dll].append(func_name)
    
    return imports


def detect_capabilities(imports: Dict[str, List[str]]) -> Dict[str, Dict]:
    """Detect binary capabilities from imports.
    
    Args:
        imports: Dict mapping DLL names to imported functions
        
    Returns:
        Dict with capability categories and detected features
    """
    capabilities = {}
    imported_dlls = set(dll.lower() for dll in imports.keys())
    all_functions = set()
    for funcs in imports.values():
        all_functions.update(funcs)
    
    # Check each capability category
    for category, dlls in CAPABILITY_DLLS.items():
        detected_dlls = imported_dlls & {d.lower() for d in dlls}
        
        if detected_dlls:
            capabilities[category] = {
                'detected': True,
                'dlls': list(detected_dlls),
                'functions': []
            }
    
    # Detect specific network functions
    if 'networking' in capabilities:
        network_funcs = all_functions & NETWORK_FUNCTIONS
        capabilities['networking']['functions'] = list(network_funcs)
        capabilities['networking']['protocols'] = _detect_network_protocols(network_funcs)
    
    # Detect RPC functions
    if 'rpc' in capabilities or 'rpcrt4.dll' in imported_dlls:
        rpc_funcs = all_functions & RPC_FUNCTIONS
        if rpc_funcs:
            if 'rpc' not in capabilities:
                capabilities['rpc'] = {'detected': True, 'dlls': ['rpcrt4.dll']}
            capabilities['rpc']['functions'] = list(rpc_funcs)
            capabilities['rpc']['is_server'] = any('Server' in f for f in rpc_funcs)
            capabilities['rpc']['is_client'] = any('Binding' in f or 'Client' in f for f in rpc_funcs)
    
    # Detect COM functions
    if 'com' in capabilities:
        com_funcs = all_functions & COM_FUNCTIONS
        capabilities['com']['functions'] = list(com_funcs)
    
    return capabilities


def _detect_network_protocols(network_funcs: Set[str]) -> List[str]:
    """Detect which network protocols are used."""
    protocols = []
    
    if any('WinHttp' in f for f in network_funcs):
        protocols.append('HTTP/HTTPS (WinHTTP)')
    
    if any('Internet' in f or 'Http' in f for f in network_funcs):
        protocols.append('HTTP/HTTPS (WinINet)')
    
    if any(f in network_funcs for f in ['socket', 'WSAStartup', 'connect', 'bind']):
        protocols.append('TCP/UDP (Winsock)')
    
    return protocols


def analyze_imports(dll_path: Path, dumpbin_path: str = "dumpbin") -> Dict:
    """Full import analysis with capability detection.
    
    Args:
        dll_path: Path to PE file
        dumpbin_path: Path to dumpbin.exe
        
    Returns:
        Dict with imports and detected capabilities
    """
    logger.info(f"Analyzing imports for {dll_path.name}")
    
    imports = parse_imports_dumpbin(dll_path, dumpbin_path)
    
    if not imports:
        logger.warning(f"No imports found for {dll_path.name}")
        return {
            'imports': {},
            'capabilities': {},
            'summary': {
                'total_dlls': 0,
                'total_functions': 0,
                'has_networking': False,
                'has_rpc': False,
                'has_com': False
            }
        }
    
    capabilities = detect_capabilities(imports)
    
    # Generate summary
    total_funcs = sum(len(funcs) for funcs in imports.values())
    
    summary = {
        'total_dlls': len(imports),
        'total_functions': total_funcs,
        'has_networking': 'networking' in capabilities,
        'has_rpc': 'rpc' in capabilities,
        'has_com': 'com' in capabilities,
        'has_crypto': 'crypto' in capabilities,
        'has_registry': 'registry' in capabilities,
    }
    
    logger.info(f"Import analysis complete: {total_funcs} functions from {len(imports)} DLLs")
    
    return {
        'imports': imports,
        'capabilities': capabilities,
        'summary': summary
    }


def format_capabilities_summary(capabilities: Dict[str, Dict]) -> str:
    """Format capabilities as human-readable summary."""
    if not capabilities:
        return "No special capabilities detected"
    
    lines = []
    
    for category, info in sorted(capabilities.items()):
        if not info.get('detected'):
            continue
        
        lines.append(f"\n{category.upper()}:")
        lines.append(f"  DLLs: {', '.join(info['dlls'])}")
        
        if 'functions' in info and info['functions']:
            func_count = len(info['functions'])
            lines.append(f"  Functions: {func_count} detected")
            if func_count <= 10:
                for func in info['functions']:
                    lines.append(f"    - {func}")
            else:
                for func in info['functions'][:5]:
                    lines.append(f"    - {func}")
                lines.append(f"    ... and {func_count - 5} more")
        
        if category == 'networking' and 'protocols' in info:
            lines.append(f"  Protocols: {', '.join(info['protocols'])}")
        
        if category == 'rpc':
            if info.get('is_server'):
                lines.append(f"  Mode: RPC Server")
            if info.get('is_client'):
                lines.append(f"  Mode: RPC Client")
    
    return '\n'.join(lines)
