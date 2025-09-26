# Contributing Guide

Thank you for your interest in improving **Keyboard Simulator**!

## 🧭 Workflow Overview

1. Fork and clone the repository.
2. Create a feature branch from `main`.
3. Install dependencies in editable mode:
   ```powershell
   pip install -e .[dev]
   ```
4. Run quality checks before submitting:
   ```powershell
   ruff check
   pytest
   ```
5. Submit a pull request with a concise description of your changes.

## ✅ Pull Request Checklist

- [ ] Tests and linters pass locally
- [ ] Docs updated (README / changelog / architecture) if behavior changes
- [ ] New code includes type hints and docstrings where helpful
- [ ] Screenshots for UI changes (optional but appreciated)

## 🧪 Testing Tips

- CLI logic: add unit tests in `tests/`
- GUI logic: keep heavy UI interactions in helper functions to enable testing
- Windows-specific APIs: guard with `pytest.skip` when running on other platforms

## 📝 Coding Style

- Follow Ruff defaults (PEP 8 + bugbear)
- Prefer dataclasses and type hints for shared models
- Minimize platform checks in core modules; delegate to backends

## 📄 Documentation

- Architecture decisions: update `docs/ARCHITECTURE.md`
- User-facing behavior: update `README.md` / `README_PRO.md`
- Add a changelog entry under `CHANGELOG.md` for every release-worthy change

## 🙏 Need Help?

Feel free to open a draft PR or start a discussion. We're happy to pair on tricky interception/driver issues.
