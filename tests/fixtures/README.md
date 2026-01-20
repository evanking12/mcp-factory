# Test Fixtures

This directory contains vcpkg manifest for installing test DLL fixtures.

## Dependencies

- **zstd** - Compression library (libzstd.dll or zstd.dll)
- **sqlite3** - Database engine (sqlite3.dll)

## Usage

These fixtures are automatically installed when running `scripts/run_fixtures.ps1`.

Manual installation:
```powershell
vcpkg install --triplet x64-windows --manifest-root tests/fixtures
```

## Purpose

Provides real-world DLLs with:
- Comprehensive exports (100+ functions each)
- Well-documented headers
- C API (for simpler testing)
- Cross-platform availability
- Active maintenance

These DLLs serve as test cases for the export analysis pipeline.
