# MarketBot Development Guidelines

## Architecture Principles

1. One responsibility per module.
2. No hard-coded paths.
3. No hard-coded credentials.
4. Collectors should never manage authentication.
5. Database access should go through the repository layer.
6. Every feature should include logging and error handling.
7. Every sprint ends with testing and a Git commit.

## Coding Standards

- Python 3.12+
- Type hints where practical.
- Descriptive function names.
- Small, testable functions.
- Prefer composition over duplication.

## Git Workflow

- Work in sprint-sized commits.
- Keep the `main` branch deployable.
- Use descriptive commit messages.