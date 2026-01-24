"""
CLI Analyzer - Extract invocables from Windows EXE/CLI tools

Parses --help output and structured CLI metadata to discover:
- Flags/options (--verbose, -v, /all)
- Positional arguments
- Subcommands
- Evidence: where each fact came from (help text line, documentation)
"""

import subprocess
import re
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ArgumentType(Enum):
    FLAG = "flag"  # --verbose, -v, /all
    OPTION = "option"  # --input=value, -o value
    POSITIONAL = "positional"  # file, directory
    SUBCOMMAND = "subcommand"  # git commit, git push


@dataclass
class Argument:
    name: str
    type: ArgumentType
    short_form: Optional[str] = None
    long_form: Optional[str] = None
    description: str = ""
    takes_value: bool = False
    value_type: str = "string"  # string, integer, path, choice
    choices: List[str] = None
    required: bool = False
    evidence: List[Dict] = None  # Where this came from (line #, source)

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type.value,
            "short_form": self.short_form,
            "long_form": self.long_form,
            "description": self.description,
            "takes_value": self.takes_value,
            "value_type": self.value_type,
            "choices": self.choices or [],
            "required": self.required,
            "evidence": self.evidence or []
        }


@dataclass
class CLIInvocable:
    exe_path: str
    exe_name: str
    description: str = ""
    version: Optional[str] = None
    arguments: List[Argument] = None
    subcommands: List[str] = None
    evidence_sources: List[str] = None  # ["--help output", "file inspection", etc]
    
    def __post_init__(self):
        if self.arguments is None:
            self.arguments = []
        if self.subcommands is None:
            self.subcommands = []
        if self.evidence_sources is None:
            self.evidence_sources = []

    def to_dict(self):
        return {
            "exe_path": self.exe_path,
            "exe_name": self.exe_name,
            "description": self.description,
            "version": self.version,
            "arguments": [arg.to_dict() for arg in self.arguments],
            "subcommands": self.subcommands,
            "evidence_sources": self.evidence_sources
        }


class CLIAnalyzer:
    """Analyzes Windows CLI executables to extract invocable arguments and commands"""
    
    def __init__(self, exe_path: str, timeout: int = 5):
        self.exe_path = Path(exe_path)
        self.exe_name = self.exe_path.stem
        self.timeout = timeout
        self.help_text = None
        self.invocable = CLIInvocable(
            exe_path=str(self.exe_path),
            exe_name=self.exe_name
        )
    
    def run_help(self, flag: str = "--help") -> Optional[str]:
        """Run the EXE with help flag, handling stderr/stdout"""
        try:
            result = subprocess.run(
                [str(self.exe_path), flag],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            # Help text can be on stdout or stderr
            output = result.stdout or result.stderr
            return output if output and len(output.strip()) > 20 else None
        except subprocess.TimeoutExpired:
            logger.warning(f"Help timeout for {self.exe_name} with {flag}")
            return None
        except FileNotFoundError:
            logger.error(f"EXE not found: {self.exe_path}")
            return None
        except Exception as e:
            logger.warning(f"Error running help for {self.exe_name}: {e}")
            return None
    
    def analyze(self) -> CLIInvocable:
        """Main analysis: try multiple help flags, parse output, extract arguments"""
        
        # Try Windows-style help flags first, then Unix-style
        help_flags = ["/?", "/help", "-?", "--help", "-h", "--usage", "-usage"]
        
        for flag in help_flags:
            help_text = self.run_help(flag)
            if help_text and len(help_text.strip()) > 20:  # Got meaningful output
                self.help_text = help_text
                self.invocable.evidence_sources.append(f"Help output from '{flag}'")
                logger.info(f"Got help for {self.exe_name} using '{flag}'")
                break
        
        if not self.help_text:
            logger.warning(f"No help text found for {self.exe_name}, falling back to string extraction")
            self._extract_from_strings()
        else:
            # Parse the help text
            self._parse_help_text()
        
        return self.invocable
    
    def _extract_from_strings(self):
        """Fallback: Extract flag patterns from binary strings"""
        try:
            # Try to use strings.exe from Sysinternals (if available)
            result = subprocess.run(
                ["strings.exe", str(self.exe_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                strings_output = result.stdout
                self.invocable.evidence_sources.append("Binary string extraction (strings.exe)")
                logger.info(f"Extracted strings from {self.exe_name}")
                
                # Look for flag-like patterns in strings
                lines = strings_output.split('\n')
                for i, line in enumerate(lines):
                    self._extract_flags(line, i)
        except FileNotFoundError:
            logger.warning("strings.exe not found - Sysinternals not installed")
            # Could add fallback to pefile string extraction here
        except Exception as e:
            logger.warning(f"String extraction failed for {self.exe_name}: {e}")
    
    def _parse_help_text(self):
        """Extract arguments and subcommands from help text"""
        lines = self.help_text.split('\n')
        
        for i, line in enumerate(lines):
            # Look for flag patterns: --flag, -f, /flag
            self._extract_flags(line, i)
            # Look for subcommands (more sophisticated heuristics)
            self._extract_subcommands(line, i)
    
    def _extract_flags(self, line: str, line_num: int):
        """Extract flag patterns from help line"""
        
        # Pattern: --long-form, short-form, or /windows-style
        # Matches: --verbose, -v, /all, -i FILE, --output=PATH
        
        # Windows style: /flag
        windows_flags = re.findall(r'/(\w+)', line)
        for flag in windows_flags:
            if flag not in ['flag', 'help', '?']:  # Skip false positives
                arg = Argument(
                    name=flag,
                    type=ArgumentType.FLAG,
                    long_form=f"/{flag}",
                    description=self._extract_description(line),
                    evidence=[{
                        "source": "help_text",
                        "line": line_num,
                        "match": f"/{flag}"
                    }]
                )
                if arg not in self.invocable.arguments:
                    self.invocable.arguments.append(arg)
        
        # Unix style: --long-form, -short
        unix_flags = re.findall(r'(--[\w-]+|-[a-zA-Z])\s*(?:=|\s+)?([A-Z_]*)', line)
        for long_form, value_type in unix_flags:
            name = long_form.lstrip('-').replace('-', '_')
            takes_value = bool(value_type.strip())
            
            arg = Argument(
                name=name,
                type=ArgumentType.OPTION if takes_value else ArgumentType.FLAG,
                long_form=long_form,
                takes_value=takes_value,
                value_type=value_type.lower() if value_type else "bool",
                description=self._extract_description(line),
                evidence=[{
                    "source": "help_text",
                    "line": line_num,
                    "match": long_form
                }]
            )
            
            # Check if already exists
            if not any(a.long_form == long_form for a in self.invocable.arguments):
                self.invocable.arguments.append(arg)
    
    def _extract_subcommands(self, line: str, line_num: int):
        """Extract subcommands (simple heuristic: short words at line start)"""
        # Pattern: "git commit", "docker run", etc.
        # Heuristic: if line starts with 1-2 word command-like tokens
        
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            return
        
        tokens = stripped.split()
        if len(tokens) >= 1:
            cmd = tokens[0]
            # Simple heuristic: all lowercase, no special chars, 3-20 chars
            if (cmd.islower() and 
                cmd.isalpha() and 
                3 <= len(cmd) <= 20 and
                cmd not in ['usage', 'options', 'commands', 'examples', 'arguments']):
                
                if cmd not in self.invocable.subcommands:
                    self.invocable.subcommands.append(cmd)
    
    def _extract_description(self, line: str) -> str:
        """Extract description after flags/commands"""
        # Remove flag markers and return the description text
        text = re.sub(r'^\s*(/|--|-)\S*\s*', '', line).strip()
        return text[:100] if text else ""


def analyze_multiple_exes(exe_paths: List[str]) -> Dict[str, CLIInvocable]:
    """Analyze multiple executables and return structured results"""
    results = {}
    
    for exe_path in exe_paths:
        if not Path(exe_path).exists():
            logger.warning(f"EXE not found, skipping: {exe_path}")
            continue
        
        logger.info(f"Analyzing {exe_path}...")
        analyzer = CLIAnalyzer(exe_path)
        invocable = analyzer.analyze()
        results[invocable.exe_name] = invocable
    
    return results


if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="CLI Analyzer - Extract arguments from Windows executables")
    parser.add_argument("exe_path", help="Path to executable to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--timeout", type=int, default=5, help="Timeout for help commands (seconds)")
    
    args = parser.parse_args()
    
    # Analyze single executable
    analyzer = CLIAnalyzer(args.exe_path, timeout=args.timeout)
    invocable = analyzer.analyze()
    
    if args.json:
        import json
        print(json.dumps(invocable.to_dict(), indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"EXE: {invocable.exe_name}")
        print(f"Path: {invocable.exe_path}")
        print(f"{'='*60}")
        print(f"Arguments found: {len(invocable.arguments)}")
        print(f"Subcommands found: {len(invocable.subcommands)}")
        print(f"Evidence sources: {invocable.evidence_sources}")
        
        if invocable.description:
            print(f"Description: {invocable.description}")
        
        if invocable.arguments:
            print("\nArguments:")
            for arg in invocable.arguments:
                forms = []
                if arg.short_form:
                    forms.append(arg.short_form)
                if arg.long_form:
                    forms.append(arg.long_form)
                form_str = ", ".join(forms) if forms else arg.name
                print(f"  {form_str:20} {arg.description}")
        
        if invocable.subcommands:
            print(f"\nSubcommands: {', '.join(invocable.subcommands)}")
        
        print()
