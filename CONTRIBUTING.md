# 🤝 Contributing to AmethystCloud Bot

Thank you for your interest in contributing to AmethystCloud Bot! This document provides guidelines and instructions for contributing.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)

---

## 📜 Code of Conduct

- Be respectful and inclusive
- Use welcoming and inclusive language
- Accept constructive criticism gracefully
- Focus on what is best for the community

---

## 🚀 Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/bot-pterodactyl.git
   cd bot-pterodactyl
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/animesao/bot-pterodactyl.git
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Create `.env` file** from template:
   ```bash
   cp .env.example .env
   ```

---

## 🛠️ Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A Discord bot token (for testing)
- Pterodactyl panel access (optional, for Pterodactyl features)

### Environment Variables

Configure your `.env` file with:
- `token` - Discord bot token (required for testing)
- `ALLOWED_GUILD_ID` - Your test server ID

> ⚠️ **Never commit your `.env` file or expose API keys!**

---

## 📝 How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/animesao/bot-pterodactyl/issues) first
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and OS

### Suggesting Features

1. Check [existing issues](https://github.com/animesao/bot-pterodactyl/issues) for similar suggestions
2. Create a new issue with:
   - Clear description of the feature
   - Use case / why it's needed
   - Possible implementation ideas

### Submitting Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   Use prefixes: `feature/`, `fix/`, `docs/`, `refactor/`

2. Make your changes following [coding standards](#coding-standards)

3. Test your changes:
   ```bash
   python main.py
   ```

4. Commit with clear message:
   ```bash
   git commit -m "feat: add new feature description"
   ```
   
   **Commit prefixes:**
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation
   - `refactor:` - Code refactoring
   - `style:` - Formatting
   - `test:` - Tests
   - `chore:` - Maintenance

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a Pull Request

---

## 🔀 Pull Request Process

1. **Update your fork**:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a clear PR description**:
   - What changes were made
   - Why they were made
   - How to test them
   - Related issues (e.g., "Closes #123")

3. **Ensure your code**:
   - Follows [coding standards](#coding-standards)
   - Doesn't break existing functionality
   - Works with Python 3.10+

4. **Wait for review** and address any feedback

---

## ✨ Coding Standards

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use meaningful variable/function names
- Add docstrings to functions and classes
- Keep functions focused and small

### File Organization

```
cogs/
├── database.py      # Database functions
├── pterodactyl.py   # Pterodactyl commands
├── tickets.py       # Ticket system
├── invites.py       # Invite tracking
└── apply.py         # Applications
```

### Naming Conventions

- **Files**: `snake_case.py`
- **Functions**: `snake_case()`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Discord commands**: `kebab-case` or `snake_case`

### Comments

- Use comments to explain **why**, not **what**
- Keep comments in English or Russian (be consistent)
- Update comments when code changes

### Imports

- Group imports: stdlib → third-party → local
- Use relative imports within cogs: `from .database import ...`

---

## 🧪 Testing

### Manual Testing

1. Run the bot locally:
   ```bash
   python main.py
   ```

2. Test in your Discord server

3. Verify:
   - Commands work as expected
   - No errors in console
   - Database operations work

### Test Checklist

- [ ] Bot starts without errors
- [ ] New/modified commands work
- [ ] Error handling works (invalid inputs, etc.)
- [ ] Database operations succeed
- [ ] No sensitive data in code

---

## ❓ Questions?

If you have questions about contributing:

1. Check this document first
2. Look at [existing issues](https://github.com/animesao/bot-pterodactyl/issues)
3. Open a new issue with the `question` label

---

## 🙏 Thank You!

Every contribution helps make AmethystCloud Bot better. Thank you for your time and effort!
