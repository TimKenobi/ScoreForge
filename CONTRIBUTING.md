# Contributing to ScoreForge

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and considerate in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a feature branch
5. Make your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/ScoreForge.git
cd ScoreForge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Optional Dependencies

```bash
# For OMR functionality
pip install oemer onnxruntime

# For Verovio rendering
brew install swig  # macOS
pip install verovio

# For PDF export
pip install abjad
brew install lilypond  # macOS
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-midi-playback`
- `fix/transpose-crash`
- `docs/update-readme`
- `refactor/simplify-parser`

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tool changes

Examples:
```
feat(parser): add support for tuplets
fix(gui): prevent crash on empty score
docs: update installation instructions
```

## Code Style

### Python Style Guide

We follow PEP 8 with these tools:
- **Black** for formatting
- **isort** for import sorting
- **Ruff** for linting

```bash
# Format code
black sheet_music_scanner tests

# Sort imports
isort sheet_music_scanner tests

# Lint
ruff check sheet_music_scanner
```

### Documentation

- Use docstrings for all public modules, classes, and functions
- Follow Google-style docstrings
- Keep comments concise and meaningful

```python
def transpose(score: Score, semitones: int) -> Score:
    """Transpose a score by the specified number of semitones.
    
    Args:
        score: The Score object to transpose.
        semitones: Number of semitones to transpose (positive = up, negative = down).
    
    Returns:
        A new Score object with all pitches transposed.
    
    Raises:
        ValueError: If semitones is not an integer.
    
    Example:
        >>> transposed = transpose(my_score, 5)  # Up a perfect fourth
    """
    ...
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sheet_music_scanner --cov-report=html

# Run specific test file
pytest tests/test_command_parser.py

# Run specific test
pytest tests/test_command_parser.py::test_parse_note_basic

# Run tests matching pattern
pytest -k "parser"
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive names: `test_transpose_up_one_octave`
- Include both positive and negative test cases
- Mock external dependencies

```python
import pytest
from sheet_music_scanner.core.command_parser import CommandParser

class TestCommandParser:
    def test_parse_simple_note(self):
        parser = CommandParser()
        result = parser.parse("C4 q")
        assert len(result) == 1
        assert result[0].pitch == "C4"
        assert result[0].duration == "q"
    
    def test_parse_invalid_note_raises_error(self):
        parser = CommandParser()
        with pytest.raises(ValueError):
            parser.parse("X9 q")
```

### Test Coverage

We aim for >80% code coverage. Check coverage with:

```bash
pytest --cov=sheet_music_scanner --cov-report=term-missing
```

## Pull Request Process

### Before Submitting

1. ✅ Update documentation if needed
2. ✅ Add/update tests
3. ✅ Run full test suite
4. ✅ Run formatters and linters
5. ✅ Update CHANGELOG.md if applicable

### Submitting

1. Push your branch to your fork
2. Open a Pull Request against `main`
3. Fill out the PR template
4. Wait for review

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested the changes

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

- At least one maintainer approval required
- CI checks must pass
- Address review comments promptly
- Squash commits if requested

## Reporting Bugs

### Before Reporting

1. Check existing issues for duplicates
2. Try the latest version
3. Gather reproduction steps

### Bug Report Template

```markdown
## Description
Clear description of the bug

## Steps to Reproduce
1. Open the app
2. Click on...
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: macOS 14.0 / Windows 11 / Ubuntu 22.04
- Python: 3.11
- App Version: 1.0.0

## Additional Context
Screenshots, error messages, etc.
```

## Feature Requests

### Before Requesting

1. Check the roadmap in README
2. Search existing issues
3. Consider if it fits the project scope

### Feature Request Template

```markdown
## Feature Description
Clear description of the feature

## Use Case
Why is this feature needed?

## Proposed Solution
How might it be implemented?

## Alternatives Considered
Other approaches you've thought of

## Additional Context
Mockups, examples from other software, etc.
```

## Architecture Guidelines

### Module Organization

- `core/`: Music processing logic (no GUI dependencies)
- `gui/`: User interface (PySide6)
- `omr/`: Optical Music Recognition adapters
- `export/`: File format exporters
- `utils/`: Shared utilities

### Design Principles

1. **Separation of Concerns**: Keep GUI and logic separate
2. **Single Responsibility**: Each class/function does one thing
3. **Dependency Injection**: Pass dependencies, don't hardcode
4. **Testability**: Design for easy testing

### Adding New Features

1. Discuss in an issue first
2. Start with core logic (no GUI)
3. Add tests
4. Add GUI components
5. Update documentation

## Questions?

- Open a GitHub Discussion for questions
- Join our community chat (if available)
- Email: maintainers@example.com

---

Thank you for contributing! 🎵
