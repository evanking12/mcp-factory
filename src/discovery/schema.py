"""
schema.py - Data models and output writers for invocable records.

Defines the core data structures for representing exported functions and
provides writers for CSV, JSON, and Markdown output formats.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ExportedFunc:
    """Represents an exported function from a DLL."""
    name: str
    ordinal: Optional[int] = None
    hint: Optional[str] = None
    rva: Optional[str] = None
    forwarded_to: Optional[str] = None
    demangled: Optional[str] = None


@dataclass
class Invocable:
    """Unified record for any callable (export, COM object, CLI command, etc)."""
    name: str
    source_type: str  # "export" | "com" | "cli" | "dotnet" | "rpc"
    ordinal: Optional[int] = None
    hint: Optional[str] = None
    rva: Optional[str] = None
    return_type: Optional[str] = None
    parameters: Optional[str] = None
    signature: Optional[str] = None
    doc_comment: Optional[str] = None
    header_file: Optional[str] = None
    header_line: Optional[int] = None
    demangled: Optional[str] = None
    doc_files: Optional[str] = None  # semicolon-separated
    confidence: str = "medium"  # "low", "medium", "high"
    confidence_reasons: Optional[List[str]] = None
    is_forwarded: bool = False
    publisher: Optional[str] = None
    is_signed: bool = False
    
    # MCP-specific fields
    dll_path: Optional[str] = None
    assembly_path: Optional[str] = None
    type_name: Optional[str] = None
    is_static: Optional[bool] = None
    clsid: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert Invocable to MCP-compatible JSON dict."""
        import re
        
        # Generate unique tool ID
        tool_id = self._generate_tool_id()
        
        # Parse parameters into JSON Schema
        input_schema = self._parse_parameters_to_schema()
        
        # Get execution metadata
        execution = self._get_execution_metadata()
        
        return {
            "name": self.name,
            "tool_id": tool_id,
            "kind": self.source_type,
            "ordinal": self.ordinal,
            "rva": self.rva,
            "confidence": self.confidence,
            "confidence_factors": {
                "has_signature": bool(self.signature),
                "has_documentation": bool(self.doc_comment),
                "has_parameters": bool(self.parameters),
                "has_return_type": bool(self.return_type),
                "is_forwarded": self.is_forwarded,
                "is_ordinal_only": bool(self.ordinal and not self.name)
            },
            "signature": {
                "return_type": self.return_type,
                "parameters": self.parameters,
                "calling_convention": None,
                "full_prototype": self.signature or self._build_prototype()
            },
            "documentation": {
                "summary": self.doc_comment,
                "description": self.doc_comment,
                "source_file": self.header_file,
                "source_line": self.header_line
            },
            "evidence": {
                "discovered_by": self.source_type + "_analyzer",
                "header_file": self.header_file,
                "forwarded_to": None,
                "demangled_name": self.demangled
            },
            "mcp": {
                "version": "1.0",
                "input_schema": input_schema,
                "execution": execution
            },
            "metadata": {
                "is_signed": self.is_signed,
                "publisher": self.publisher
            }
        }
    
    def _generate_tool_id(self) -> str:
        """Generate unique MCP tool identifier."""
        import re
        
        # Clean name for use in ID
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', self.name)
        
        # Add source type prefix
        prefix_map = {
            "export": "dll",
            "dotnet": "net",
            "com": "com",
            "cli": "cli",
            "rpc": "rpc"
        }
        prefix = prefix_map.get(self.source_type, "unk")
        
        # Add ordinal if available
        suffix = f"_{self.ordinal}" if self.ordinal else ""
        
        return f"{prefix}_{clean_name}{suffix}"
    
    def _build_prototype(self) -> str:
        """Build function prototype string."""
        ret = self.return_type or "void"
        params = self.parameters or ""
        return f"{ret} {self.name}({params})"
    
    def _parse_parameters_to_schema(self) -> dict:
        """Convert parameter string to JSON Schema for MCP."""
        if not self.parameters or self.parameters.strip().lower() in ('void', ''):
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        properties = {}
        required = []
        
        # Parse parameter string (e.g., "int x, char* y, DWORD flags")
        import re
        
        # Split by comma, handling nested types
        params = self._split_parameters(self.parameters)
        
        for i, param in enumerate(params):
            param = param.strip()
            if not param:
                continue
            
            # Extract type and name
            param_info = self._parse_single_parameter(param, i)
            if param_info:
                properties[param_info["name"]] = {
                    "type": param_info["json_type"],
                    "description": f"{param_info['c_type']}"
                }
                required.append(param_info["name"])
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _split_parameters(self, params: str) -> List[str]:
        """Split parameter string by commas, respecting nested types."""
        result = []
        current = ""
        depth = 0
        
        for char in params:
            if char in "<([":
                depth += 1
            elif char in ">)]":
                depth -= 1
            elif char == ',' and depth == 0:
                result.append(current)
                current = ""
                continue
            current += char
        
        if current:
            result.append(current)
        
        return result
    
    def _parse_single_parameter(self, param: str, index: int) -> Optional[dict]:
        """Parse a single parameter into name and type."""
        import re
        
        # Pattern: type name or type* name or type& name
        # Examples: "int x", "char* str", "const DWORD& flags"
        param = param.strip()
        
        # Remove const, volatile, etc.
        param = re.sub(r'\b(const|volatile|static|extern)\s+', '', param)
        
        # Split into tokens
        tokens = param.split()
        if len(tokens) < 2:
            # No name, or malformed - use positional
            name = f"arg{index}"
            c_type = param
        else:
            # Last token is typically the name
            name = tokens[-1].strip('*&')
            c_type = ' '.join(tokens[:-1])
        
        # Map C type to JSON Schema type
        json_type = self._c_type_to_json_type(c_type)
        
        return {
            "name": name,
            "c_type": c_type,
            "json_type": json_type
        }
    
    def _c_type_to_json_type(self, c_type: str) -> str:
        """Map C/C++ type to JSON Schema type."""
        c_type_lower = c_type.lower().strip()
        
        # 1. Pointers
        # void* or LPVOID -> integer (address) or string? 
        # Most FFI tooling (ctypes etc) can handle integers as pointers. 
        # But LLMs are better at "0x1234" strings often.
        # Let's check for specific string pointers first.
        
        # String pointers (const char*, LPWSTR, etc)
        if any(x in c_type_lower for x in ['char*', 'wchar*', 'str*', 'lpcstr', 'lpwstr', 'lpcwstr', 'bstr']):
            return "string"

        # Other pointers -> integer (addresses usually 64-bit ints) or string?
        # Current logic said string. Let's keep strict pointers as string for safety if they are opaque handles.
        if '*' in c_type or 'ptr' in c_type_lower or 'handle' in c_type_lower:
            return "string"
        
        # 2. Integers
        # Broad matching for integer types
        int_types = [
            'int', 'long', 'short', 'byte', 'dword', 'word', 'uint', 
            'size_t', 'hresult', 'bool', 'boolean', 'unsigned', 'ulong',
            'hwnd', 'int32', 'int64', 'uptr'
        ]
        
        # Split tokens to avoid matching "pointer" in "intptr" falsely if not careful, 
        # but logic above handles * and ptr.
        if any(t in c_type_lower for t in int_types):
            return "integer"
        
        # 3. Floating point
        if any(t in c_type_lower for t in ['float', 'double', 'decimal']):
            return "number"
        
        # 4. Characters
        if c_type_lower in ['char', 'wchar_t']:
             return "string" # Treat single char as string usually easier for LLMs

        # 5. String types (explicit)
        if any(t in c_type_lower for t in ['string', 'str', 'wchar']):
            return "string"
        
        # Default to string for unknown structures/unions to be safe
        return "string"
    
    def _get_execution_metadata(self) -> dict:
        """Generate execution metadata for MCP server."""
        if self.source_type == "export":
            return {
                "method": "dll_import",
                "dll_path": self.dll_path,
                "function_name": self.name,
                "calling_convention": "stdcall",  # Default, could be enhanced
                "charset": "unicode" if 'W' in self.name else "ansi"
            }
        
        elif self.source_type == "dotnet":
            return {
                "method": "dotnet_reflection",
                "assembly_path": self.assembly_path,
                "type": self.type_name,
                "method": self.name,
                "is_static": self.is_static or False
            }
        
        elif self.source_type == "com":
            return {
                "method": "com_automation",
                "clsid": self.clsid,
                "interface": "IDispatch",
                "method": self.name
            }
        
        elif self.source_type == "rpc":
            # RPC endpoint invocation
            return {
                "method": "rpc_call",
                "endpoint": self.parameters,  # Named pipe or network endpoint
                "interface_uuid": self.signature.split(': ')[-1] if 'UUID:' in (self.signature or '') else None,
                "dll_path": self.dll_path
            }
        
        else:
            return {
                "method": "unknown",
                "notes": f"Execution method not defined for source_type: {self.source_type}"
            }



@dataclass
class MatchInfo:
    """Information extracted from header file about a function."""
    function: str
    return_type: str
    parameters: str
    doc_comment: str
    header_file: str
    line: int
    prototype: str


def exports_to_invocables(
    exports: List[ExportedFunc],
    dll_path: Path,
    matches: Dict[str, MatchInfo] = None,
    is_signed: bool = False,
    publisher: str = None
) -> List[Invocable]:
    """Convert ExportedFunc list to Invocable list for native DLL exports.
    
    Args:
        exports: List of ExportedFunc objects from dumpbin
        dll_path: Path to the DLL file
        matches: Optional header file matches
        is_signed: Whether the DLL is digitally signed (extracted from Security Directory[4])
        publisher: Publisher name from certificate
        
    Returns:
        List of Invocable objects
    """
    matches = matches or {}
    invocables = []
    
    # Extract signature if not provided
    if is_signed is False and publisher is None:
        from signature import get_signature_info
        is_signed, publisher = get_signature_info(dll_path)
    
    # Check if this is a well-known system DLL (high confidence by default)
    dll_name = dll_path.name.lower() if hasattr(dll_path, 'name') else str(dll_path).lower()
    is_system_dll = any(dll_name.endswith(name) for name in [
        'kernel32.dll', 'kernelbase.dll', 'user32.dll', 'gdi32.dll',
        'advapi32.dll', 'ntdll.dll', 'shell32.dll', 'ole32.dll',
        'oleaut32.dll', 'combase.dll', 'rpcrt4.dll', 'ws2_32.dll',
        'winhttp.dll', 'wininet.dll', 'bcrypt.dll', 'crypt32.dll',
        'msvcrt.dll', 'ucrtbase.dll'
    ])
    
    for export in exports:
        match = matches.get(export.name)
        
        # IMPROVED CONFIDENCE SCORING (4-TIER SYSTEM)
        confidence = "low"
        confidence_reasons = ["exported from DLL"]
        
        # GUARANTEED: Header match with complete signature
        if match:
            confidence = "guaranteed"
            confidence_reasons.append("complete signature from header file")
        elif is_system_dll:
            # Well-known system DLLs have high confidence even without headers
            confidence = "high"
            confidence_reasons.append("well-known system API")
        elif export.demangled:
            # C++ exports with demangled names
            confidence = "medium"
            confidence_reasons.append("demangled name available")
        
        # MEDIUM CONFIDENCE BOOST: Digital signature
        if is_signed and publisher:
            if confidence == "low":
                confidence = "medium"
            confidence_reasons.append("digitally signed")
            if "Microsoft" in publisher:
                confidence_reasons.append("Microsoft signed")
        
        # ADDITIONAL HEURISTICS
        # Well-formed function names (PascalCase, snake_case) suggest legitimate API
        if confidence == "low":
            name = export.name
            
            # Check for library prefix patterns (e.g., sqlite3_, ZSTD_, curl_, SSL_)
            # Consistent prefixes indicate professional library design
            if '_' in name:
                prefix = name.split('_')[0]
                # If prefix is 3+ chars and uppercase or lowercase consistent, it's likely a library prefix
                if len(prefix) >= 3 and (prefix.isupper() or prefix.islower()):
                    confidence = "medium"
                    confidence_reasons.append(f"library prefix pattern ({prefix}_*)")
            
            # Check for common API patterns (Windows + cross-platform)
            elif any(name.startswith(prefix) for prefix in [
                # Windows patterns
                'Create', 'Get', 'Set', 'Open', 'Close', 'Read', 'Write',
                'Initialize', 'Finalize', 'Register', 'Unregister',
                'Allocate', 'Free', 'Query', 'Release',
                # Cross-platform C library patterns
                'init', 'destroy', 'alloc', 'dealloc', 'malloc', 'calloc',
                'compress', 'decompress', 'encode', 'decode', 'encrypt', 'decrypt',
                'load', 'save', 'bind', 'connect', 'send', 'recv', 'shutdown'
            ]):
                confidence = "medium"
                confidence_reasons.append("common API pattern")
        
        # Create Invocable
        invocable = Invocable(
            name=export.name,
            source_type="export",
            ordinal=export.ordinal,
            hint=export.hint,
            rva=export.rva,
            return_type=match.return_type if match else None,
            parameters=match.parameters if match else "",
            signature=match.prototype if match else None,
            doc_comment=match.doc_comment if match else None,
            header_file=match.header_file if match else None,
            header_line=match.line if match else None,
            demangled=export.demangled,
            confidence=confidence,
            confidence_reasons=confidence_reasons,
            is_forwarded=bool(export.forwarded_to),
            publisher=publisher,
            is_signed=is_signed,
            dll_path=str(dll_path)
        )
        
        invocables.append(invocable)
    
    return invocables


def write_csv(
    path: Path,
    exports: List[ExportedFunc],
    matches: Dict[str, MatchInfo],
    doc_hits: Dict[str, List[str]],
    is_signed: bool = False,
    publisher: str = None
) -> None:
    """Write exports to CSV file with matched headers and documentation."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Function', 'Ordinal', 'Hint', 'RVA', 'ForwardedTo',
            'ReturnType', 'Parameters', 'Signature', 'DocComment',
            'HeaderFile', 'Line', 'Demangled', 'DocFiles', 'IsSigned', 'Publisher'
        ])

        for exp in exports:
            mi = matches.get(exp.name)
            docs = doc_hits.get(exp.name, [])

            writer.writerow([
                exp.name,
                exp.ordinal or '',
                exp.hint or '',
                exp.rva or '',
                exp.forwarded_to or '',
                mi.return_type if mi else '',
                mi.parameters if mi else '',
                mi.prototype if mi else '',
                mi.doc_comment if mi else '',
                mi.header_file if mi else '',
                mi.line if mi else '',
                exp.demangled or '',
                ';'.join(docs) if docs else '',
                'Yes' if is_signed else 'No',
                publisher or ''
            ])


def write_json(
    path: Path,
    exports: List[ExportedFunc],
    matches: Dict[str, MatchInfo],
    doc_hits: Dict[str, List[str]]
) -> None:
    """Write exports to JSON file (for MCP schema generation)."""
    import json

    path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for exp in exports:
        mi = matches.get(exp.name)
        docs = doc_hits.get(exp.name, [])

        record = {
            'name': exp.name,
            'ordinal': exp.ordinal,
            'hint': exp.hint,
            'rva': exp.rva,
            'forwarded_to': exp.forwarded_to,
            'demangled': exp.demangled,
        }

        if mi:
            record.update({
                'return_type': mi.return_type,
                'parameters': mi.parameters,
                'signature': mi.prototype,
                'doc_comment': mi.doc_comment,
                'header_file': str(mi.header_file),
                'header_line': mi.line,
            })

        if docs:
            record['doc_files'] = docs

        records.append(record)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)


def write_markdown(
    path: Path,
    dll_path: Path,
    exports: List[ExportedFunc],
    matches: Dict[str, MatchInfo],
    doc_hits: Dict[str, List[str]]
) -> None:
    """Write exports to Markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# API Report: {dll_path.name}\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total Exports: {len(exports)}\n\n")

        for exp in exports:
            mi = matches.get(exp.name)
            docs = doc_hits.get(exp.name, [])

            f.write(f"## {exp.name}\n\n")

            if exp.ordinal:
                f.write(f"**Ordinal:** {exp.ordinal}\n\n")

            if mi:
                f.write(f"**Signature:** `{mi.prototype}`\n\n")
                f.write(f"**Header:** `{mi.header_file}:{mi.line}`\n\n")

                if mi.doc_comment:
                    f.write(f"**Documentation:**\n\n{mi.doc_comment}\n\n")

                if docs:
                    f.write(f"**Referenced in:**\n\n")
                    for doc in docs:
                        f.write(f"- `{doc}`\n")
                    f.write("\n")

            if exp.demangled and exp.demangled != exp.name:
                f.write(f"**Demangled:** `{exp.demangled}`\n\n")

            f.write("---\n\n")


def write_tier_summary(path: Path, entries: List[str]) -> None:
    """Write summary of all tiers generated."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write("# Tier Summary\n\n")
        f.write("Tiers successfully generated:\n\n")
        for entry in entries:
            f.write(f"- {entry}\n")
        f.write("\n")
        f.write("See individual tier files for detailed analysis.\n")


def write_invocables_json(
    path: Path,
    invocables: List[Invocable],
    dll_path: Optional[Path] = None,
    tier: int = 2,
    schema_version: str = "2.0.0"
) -> None:
    """Write Invocable objects to MCP-compatible JSON.
    
    Args:
        path: Output JSON file path
        invocables: List of Invocable objects
        dll_path: Source DLL/assembly path
        tier: Analysis tier level
        schema_version: JSON schema version
    """
    import json
    import os
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build metadata
    metadata = {
        "schema_version": schema_version,
        "tier": tier,
        "analysis_timestamp": datetime.now().isoformat(),
        "pipeline_version": "1.0.0"
    }
    
    if dll_path:
        metadata.update({
            "target_path": str(dll_path),
            "target_name": dll_path.name,
            "target_type": dll_path.suffix.lstrip('.'),
            "file_size_bytes": os.path.getsize(dll_path) if dll_path.exists() else 0
        })
    
    # Convert invocables to dicts
    invocable_dicts = [inv.to_dict() for inv in invocables]
    
    # Build final structure
    output = {
        "schema_version": schema_version,
        "metadata": metadata,
        "invocables": invocable_dicts,
        "summary": {
            "total_invocables": len(invocables),
            "by_source_type": _count_by_source_type(invocables),
            "by_confidence": _count_by_confidence(invocables)
        }
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def _count_by_source_type(invocables: List[Invocable]) -> dict:
    """Count invocables by source type."""
    counts = {}
    for inv in invocables:
        counts[inv.source_type] = counts.get(inv.source_type, 0) + 1
    return counts


def _count_by_confidence(invocables: List[Invocable]) -> dict:
    """Count invocables by confidence level."""
    counts = {}
    for inv in invocables:
        counts[inv.confidence] = counts.get(inv.confidence, 0) + 1
    return counts
