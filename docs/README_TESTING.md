# Testing OpenAI Conversation Plus

This document describes how to test the OpenAI Conversation Plus integration without running the full Home Assistant Core.

## Quick Start

### Automated Testing

Run all tests using the test runner script:

```bash
python run_tests.py
```

Or use make:

```bash
make test
```

### Manual Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements_test.txt
   pip install -e .
   ```

2. **Run pytest:**
   ```bash
   pytest -v
   ```

3. **Run with coverage:**
   ```bash
   pytest --cov=custom_components.openai_conversation_plus
   ```

## Testing Components

### Unit Tests

Located in the `tests/` directory:

- `test_init.py` - Tests for integration setup and configuration
- `test_config_flow.py` - Tests for configuration flow
- `test_ai_task.py` - Tests for AI Task functionality

### Static Code Analysis

Run pre-commit hooks:

```bash
pre-commit run --all-files
```

Individual tools:

- **Ruff:** `ruff check .`
- **Black:** `black --check .`
- **MyPy:** `mypy custom_components/openai_conversation_plus`
- **isort:** `isort --check-only .`

### Manifest Validation

Validate the integration manifest:

```bash
hassfest validate
```

## Development Workflow

1. **Set up development environment:**
   ```bash
   make setup-dev
   ```

2. **Make changes to the code**

3. **Format code:**
   ```bash
   make format
   ```

4. **Run validation:**
   ```bash
   make validate-all
   ```

5. **Run tests:**
   ```bash
   make test
   ```

## CI/CD

GitHub Actions automatically runs tests on:
- Push to main or dev branches
- Pull requests

The workflow includes:
- Testing on Python 3.11 and 3.12
- Code coverage reporting
- Hassfest validation
- HACS validation

## Testing Without Home Assistant

The test suite uses `pytest-homeassistant-custom-component` which provides:
- Mock Home Assistant core
- Test fixtures
- Async test support
- Entity helpers

This allows testing the integration logic without a running Home Assistant instance.

## Background Testing

The `run_tests.py` script can be run as a background agent:

```bash
python run_tests.py &
```

This will:
1. Create a virtual environment
2. Install dependencies
3. Run pre-commit hooks
4. Run hassfest validation
5. Execute all tests
6. Generate coverage reports

## Troubleshooting

### Import Errors

If you encounter import errors, ensure:
- You're in the correct directory
- Dependencies are installed: `pip install -r requirements_test.txt`
- The package is installed in development mode: `pip install -e .`

### AI Task Tests Skipped

Some tests are skipped if the AI Task component is not available. This is normal for testing outside of Home Assistant Core.

### Pre-commit Failures

If pre-commit fails:
1. Run `make format` to auto-fix issues
2. Review and fix any remaining issues manually
3. Re-run pre-commit: `pre-commit run --all-files`

## Next Steps

After testing locally:
1. Commit changes: `git add -A && git commit -m "message"`
2. Push to repository: `git push`
3. CI/CD will run automatically
4. Monitor test results in GitHub Actions
