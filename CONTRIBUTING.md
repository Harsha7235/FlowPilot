# CONTRIBUTING

> **Contribution Guidelines for the FlowPilot Engineering Platform**

Version: 1.0

Status: Active

---

# 1. Welcome

Thank you for your interest in contributing to FlowPilot.

FlowPilot is an open, research-driven engineering platform focused on applying Artificial Intelligence to Software Defined Radio (SDR) engineering.

Every contribution should improve the platform while maintaining engineering quality, architectural consistency, and long-term maintainability.

---

# 2. Project Goals

FlowPilot aims to provide:

- Autonomous SDR Engineering
- AI-assisted GNU Radio Development
- Knowledge-driven Engineering
- Explainable AI
- Continuous Learning
- Production-quality Software

Every contribution should align with these goals.

---

# 3. Before You Contribute

Please read the following documents before contributing:

1. README.md
2. INTRODUCTION.md
3. SYSTEM_OVERVIEW.md
4. ARCHITECTURE.md
5. PROJECT_STRUCTURE.md
6. DEVELOPMENT_ROADMAP.md
7. AGENTS.md
8. WORKFLOWS.md

These documents define the official architecture and development process.

---

# 4. Development Principles

Every contribution should follow these principles:

- Simplicity
- Modularity
- Reusability
- Readability
- Maintainability
- Testability
- Explainability
- Security
- Performance

---

# 5. Repository Workflow

Development should follow the Git branching model.

```
main

↓

develop

↓

feature/<feature-name>
```

Example

```
feature/core

feature/planner

feature/generator

feature/runtime
```

---

# 6. Commit Messages

Follow Conventional Commits.

Examples

```
feat: add workflow engine

fix: resolve runtime validation bug

docs: update architecture

refactor: simplify planner logic

test: add validator unit tests
```

---

# 7. Coding Standards

## Python

- Follow PEP 8
- Use type hints
- Keep functions focused
- Prefer composition over inheritance
- Document public APIs

---

## TypeScript

- Use strict typing
- Prefer functional components
- Avoid unnecessary complexity
- Use consistent naming

---

# 8. Naming Conventions

Directories

```
snake_case
```

Python files

```
snake_case.py
```

Classes

```
PascalCase
```

Functions

```
snake_case()
```

Constants

```
UPPER_CASE
```

Variables

```
snake_case
```

---

# 9. Documentation

Every new feature should include:

- Code comments where necessary
- Docstrings
- Updated Markdown documentation
- Usage examples (if applicable)

Documentation should stay synchronized with implementation.

---

# 10. Testing

Every contribution should include appropriate tests.

Types of testing

- Unit Tests
- Integration Tests
- End-to-End Tests (when applicable)

Code should not be merged if tests fail.

---

# 11. Code Review

Every pull request should be reviewed for:

- Correctness
- Readability
- Maintainability
- Security
- Performance
- Documentation
- Test Coverage

---

# 12. Pull Request Checklist

Before opening a pull request:

- Code builds successfully
- Tests pass
- Documentation updated
- No unnecessary dependencies
- No hardcoded secrets
- No debug code left behind

---

# 13. Dependency Management

Before adding a new dependency:

- Verify it is actively maintained
- Confirm license compatibility
- Evaluate performance impact
- Avoid duplicate functionality

---

# 14. Security Guidelines

Never commit:

- API keys
- Passwords
- Tokens
- Secrets
- Certificates

Use environment variables and secret management tools.

---

# 15. Branch Protection

The `main` branch should be protected.

Recommended rules:

- Pull requests required
- Status checks required
- No direct pushes
- Reviewed changes only

---

# 16. Issue Reporting

When reporting an issue, include:

- Description
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details
- Logs (if relevant)

---

# 17. Feature Requests

Feature requests should describe:

- Problem
- Proposed solution
- Benefits
- Alternatives considered

---

# 18. Architecture Changes

Architecture changes should be discussed before implementation.

Do not introduce breaking architectural changes without updating:

- ARCHITECTURE.md
- PROJECT_STRUCTURE.md
- DEVELOPMENT_ROADMAP.md

---

# 19. AI Contribution Guidelines

When AI tools are used:

- Review generated code manually
- Validate engineering correctness
- Verify documentation
- Ensure consistency with project architecture

AI-generated code should be treated like any other contribution.

---

# 20. Licensing

By contributing to FlowPilot, contributors agree that their contributions are made under the project's chosen open-source license.

---

# 21. Community Standards

Contributors should:

- Be respectful
- Provide constructive feedback
- Collaborate professionally
- Focus on technical discussions
- Help maintain a welcoming environment

---

# 22. Summary

FlowPilot is a long-term engineering platform built on strong architectural principles, modular design, and high engineering standards.

These guidelines help ensure that every contribution supports the project's vision while maintaining quality and consistency.

Thank you for contributing to FlowPilot.

---
