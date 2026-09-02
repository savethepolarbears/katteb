# Contributing to Katteb CLI & SDK

We welcome contributions to the Katteb API CLI and Python SDK.

## Development Workflow

1. **Clone the repository:**
   ```bash
   git clone https://github.com/savethepolarbears/katteb.git
   cd katteb
   ```

2. **Set up virtual environment & install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

4. **Lint and Format:**
   ```bash
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

## Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` for new features or endpoints
- `fix:` for bug fixes
- `docs:` for documentation updates
- `test:` for adding or updating tests
- `refactor:` for code refactoring without behavior changes
- `chore:` for build, dependency, or tooling updates
