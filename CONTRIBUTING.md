# Contributing Guide

Thanks for considering a contribution! This project is designed to be simple and approachable for newcomers.

## Ways to contribute
- Report bugs and request features via issues
- Improve docs and examples
- Add tests
- Implement enhancements (small, focused PRs are best)

## Development setup

1. Create a virtual environment and install dependencies:
   ```powershell
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Run the server locally:
   ```powershell
   uvicorn main:app --reload
   ```
3. Run tests:
   ```powershell
   python -m pytest -q
   ```

## Coding standards
- Use type hints and docstrings
- Keep functions small and focused
- Add/adjust tests when changing behavior
- Avoid breaking public API unless justified (mention in PR)

## Commit and PR guidelines
- Reference related issues in the PR description
- Provide a clear summary of changes and rationale
- Keep PRs small and incremental
- Ensure CI (lint/tests) passes

## Security
If you discover a security issue, please report it privately via issues with a minimal repro and mark it clearly.
