# Contributing to Katteb CLI & SDK

Thank you for considering contributing to Katteb! This document outlines our development workflow, coding standards, and testing procedures.

---

## Development Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/savethepolarbears/katteb.git
   cd katteb
   ```

2. **Create and Activate a Virtual Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies (in Editable Mode with Dev Extras):**
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

---

## Local Validation Suite

Before committing or opening a pull request, ensure all checks pass locally:

### 1. Test Suite & Coverage
We enforce a minimum test coverage threshold of **80%**:
```bash
pytest --cov=katteb --cov-report=term-missing --cov-fail-under=80
```

### 2. Linting & Formatting
We use [Ruff](https://astral.sh/ruff) for fast, unified linting and formatting:
```bash
# Check code style and rules
ruff check .

# Check formatting
ruff format --check .

# Auto-format changes
ruff format .
```

### 3. Static Type Checking
All code must be fully type-annotated and pass [Mypy](https://mypy-lang.org/):
```bash
mypy src/
```

### 4. Security SAST Scan
Verify code against Bandit static security analyzer:
```bash
bandit -r src/ -ll
```

---

## Pull Request Guidelines

1. **Branch Naming:**
   - Use descriptive feature branches off `main`: `feat/short-description`, `fix/issue-description`, `chore/task-name`.
   - Never commit directly to `main`.
2. **Conventional Commits:**
   Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
   - `feat:` for new capabilities, endpoints, or CLI commands
   - `fix:` for bug fixes and error handling
   - `docs:` for documentation updates
   - `test:` for new or improved unit/integration tests
   - `refactor:` for code restructuring without behavioral changes
   - `chore:` for dependencies, tooling, and workflow maintenance
3. **No Secrets or Workstation Paths:**
   - Never commit API keys, personal access tokens, or private paths (`/Users/...`).
   - Use configurable environment variables (e.g. `KATTEB_API_KEY`, `BBM_WP_ROOT`).
4. **CI/CD Compliance:**
   - Ensure the GitHub Actions CI and Security workflows pass cleanly on your pull request.
