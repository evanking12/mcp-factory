"""
String Extractor - Binary string mining fallback

Extracts potential API names, function names, and documentation strings
from compiled binaries when static analysis methods fail.

Used as fallback when:
- Export tables are missing/corrupted
- Headers cannot be matched
- Help text is unavailable

Looks for patterns:
- Common function name conventions (PascalCase, snake_case)
- Windows API prefixes (Create*, Get*, Set*, etc.)
- Unicode vs ASCII strings
- Printable sequences > 3 characters
"""

import re
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class StringMatch:
    text: str
    offset: int  # Byte offset in file
    encoding: str  # 'ascii' or 'utf-16le'
    confidence: str  # 'HIGH', 'MEDIUM', 'LOW'
    reason: str  # Why this string is likely relevant
    evidence: List[str] = field(default_factory=list)


class StringExtractor:
    """Extract meaningful strings from binary files"""
    
    # Common Windows API function prefixes
    API_PREFIXES = {
        'Create', 'Get', 'Set', 'Is', 'Find', 'Open', 'Close',
        'Read', 'Write', 'Delete', 'Copy', 'Move', 'Query',
        'Register', 'Unregister', 'Enumerate', 'Allocate', 'Free'
    }
    
    # Function name patterns
    FUNCTION_PATTERNS = [
        r'[A-Z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*',  # PascalCase
        r'[a-z_]+[A-Z][a-zA-Z0-9]*',  # camelCase with underscore prefix
    ]
    
    def __init__(self, filepath: str, min_length: int = 4):
        self.filepath = Path(filepath)
        self.min_length = min_length
        self.strings: List[StringMatch] = []
    
    def extract(self) -> List[StringMatch]:
        """Extract all meaningful strings from binary"""
        if not self.filepath.exists():
            return []
        
        with open(self.filepath, 'rb') as f:
            data = f.read()
        
        # Extract ASCII strings
        self._extract_ascii(data)
        
        # Extract UTF-16LE strings (common in Windows binaries)
        self._extract_utf16(data)
        
        # Filter and rank
        self._filter_and_rank()
        
        return self.strings
    
    def _extract_ascii(self, data: bytes):
        """Extract ASCII printable strings"""
        pattern = b'[ -~]{' + str(self.min_length).encode() + b',}'
        
        for match in re.finditer(pattern, data):
            text = match.group().decode('ascii', errors='ignore')
            offset = match.start()
            
            if self._is_likely_function_name(text) or self._has_api_prefix(text):
                self.strings.append(StringMatch(
                    text=text,
                    offset=offset,
                    encoding='ascii',
                    confidence=self._rank_confidence(text),
                    reason=self._get_reason(text)
                ))
    
    def _extract_utf16(self, data: bytes):
        """Extract UTF-16LE strings (Windows default)"""
        try:
            # Look for null-terminated UTF-16LE strings
            for match in re.finditer(b'(?:[^\x00]\x00){' + str(self.min_length).encode() + b',}\x00\x00', data):
                try:
                    text = match.group().rstrip(b'\x00').decode('utf-16le')
                    if len(text) >= self.min_length and self._is_likely_function_name(text):
                        offset = match.start()
                        self.strings.append(StringMatch(
                            text=text,
                            offset=offset,
                            encoding='utf-16le',
                            confidence=self._rank_confidence(text),
                            reason=self._get_reason(text)
                        ))
                except (UnicodeDecodeError, AttributeError):
                    continue
        except Exception:
            pass
    
    def _is_likely_function_name(self, text: str) -> bool:
        """Check if string matches function name patterns"""
        if not text or len(text) < self.min_length:
            return False
        
        # Skip common false positives
        if any(x in text for x in ['http', 'www.', '.exe', '.dll', '.txt']):
            return False
        
        # Check patterns
        for pattern in self.FUNCTION_PATTERNS:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _has_api_prefix(self, text: str) -> bool:
        """Check if text starts with known Windows API prefix"""
        for prefix in self.API_PREFIXES:
            if text.startswith(prefix):
                return True
        return False
    
    def _rank_confidence(self, text: str) -> str:
        """Rank how confident we are this is a real function name"""
        if self._has_api_prefix(text):
            return 'HIGH'  # Windows API prefix is strong signal
        
        if re.match(r'^[A-Z][a-z]+[A-Z]', text):  # PascalCase
            return 'MEDIUM'
        
        return 'LOW'  # Weak signal - could be random data
    
    def _get_reason(self, text: str) -> str:
        """Explain why this string is included"""
        if self._has_api_prefix(text):
            prefix = next((p for p in self.API_PREFIXES if text.startswith(p)), 'API')
            return f"Windows API function ({prefix}* pattern)"
        
        if re.match(r'^[A-Z][a-z]+[A-Z]', text):
            return "PascalCase identifier (likely function name)"
        
        return "Function-like name pattern"


def extract_strings(filepath: str, min_length: int = 4) -> List[StringMatch]:
    """Convenience function to extract strings"""
    extractor = StringExtractor(filepath, min_length)
    return extractor.extract()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python string_extractor.py <binary_file>")
        sys.exit(1)
    
    results = extract_strings(sys.argv[1])
    
    print(f"Found {len(results)} strings")
    for i, match in enumerate(results[:10], 1):
        print(f"  {i}. {match.text:30} [{match.confidence}] @ offset {match.offset}")
    
    if len(results) > 10:
        print(f"  ... and {len(results) - 10} more")
