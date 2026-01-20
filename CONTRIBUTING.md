# Contributing to MCP Factory

## Development Setup

### Prerequisites
- **Python 3.6+** for binary analysis scripts
- **.NET 8 SDK** (planned for future MCP generation components)
- **Visual Studio Build Tools** with C++ Desktop Development workload
- **git** for version control
- **vcpkg** for dependency management (auto-installed by scripts)

### Initial Setup

```powershell
# 1. Clone the repository
git clone https://github.com/evanking12/mcp-factory.git
cd mcp-factory

# 2. Run fixture tests to verify setup
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_fixtures.ps1 -BootstrapVcpkg

# 3. Verify smoke tests pass
.\scripts\smoke_test.ps1
```

## Workflow

### Branch Strategy

```bash
# Create feature branch from main
git checkout -b feature/your-feature-name

# Make changes and test locally
.\scripts\run_fixtures.ps1

# Commit with clear messages (see below)
git add .
git commit -m "feat(discovery): add COM type library parser"

# Push and create PR
git push origin feature/your-feature-name
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Adding or updating tests
- `refactor:` Code restructuring without behavior change
- `perf:` Performance improvements
- `chore:` Maintenance tasks

**Scope (optional):** `feat(discovery):`, `fix(mcp):`, `docs(readme):`

**Examples:**
```
feat(discovery): add PDB parsing for type information
fix(fixtures): correct sqlite3 header matching regex
docs(sections-2-3): update coverage details
test(smoke): add COM object detection validation
```

## Code Standards

### Python (src/discovery/)
- Follow PEP 8 style guidelines
- Add docstrings for functions
- Include type hints where applicable
- Test with fixture DLLs before committing

### PowerShell (scripts/)
- Use approved verbs (Get-, Set-, Invoke-, etc.)
- Add comment-based help blocks
- Test on both PowerShell 5.1 and 7
- Validate on clean machine when possible

### Documentation
- Update README.md for user-facing changes
- Add entries to `docs/copilot-log.md` for AI-assisted work
- Keep `docs/sections-2-3.md` in sync with implementation

## Testing

### Automated Tests

```powershell
# Run full fixture suite
.\scripts\run_fixtures.ps1

# Verify outputs
.\scripts\smoke_test.ps1

# Check specific exports
Select-String -Path "artifacts\zstd_tier2_api_zstd_fixture.csv" -Pattern "ZSTD_" | Measure-Object
```

### Manual Testing
- Test with vcpkg fixtures (zstd, sqlite3)
- Verify on different VS installations when possible
- Check PowerShell 5.1 compatibility

## Pull Request Guidelines

### Before Submitting
1. Run fixture tests and verify they pass
2. Update relevant documentation
3. Add tests for new features
4. Rebase on latest main if needed

### PR Description Template
```markdown
## What
Brief description of the change

## Why
Problem this solves or feature it adds

## Testing
- [ ] Fixture tests pass
- [ ] Smoke tests pass
- [ ] Tested on clean environment (if applicable)

## Screenshots/Output
(If relevant - show before/after CSV, terminal output, etc.)
```

### Review Process
1. At least one team member approval required
2. All CI checks must pass (when configured)
3. Lead maintainer (Evan) final review for sections 2-3
4. Squash merge to main after approval

## Project Structure

```
mcp-factory/
├── src/discovery/          # Section 2-3: Binary analysis (Evan)
├── src/mcp/                # Section 4: MCP generation (Layalie, Caden)
├── src/verification/       # Section 5: Verification UI (Thinh)
├── scripts/                # Automation (PowerShell)
├── tests/fixtures/         # Test dependencies
├── docs/                   # Architecture, ADRs, logs
└── artifacts/              # Generated outputs (gitignored)
```

## Questions or Issues?

- **GitHub Issues:** For bugs, feature requests, or questions
- **Discussions:** For design discussions or architecture questions
- **Contact:** Tag @evanking12 for urgent items

## Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [vcpkg Documentation](https://vcpkg.io/)
- [DUMPBIN Reference](https://learn.microsoft.com/en-us/cpp/build/reference/dumpbin-reference)
- [Project Docs](./docs/)

---

**Note:** This is an active capstone project with weekly iterations. Expect frequent updates to structure and guidelines.
