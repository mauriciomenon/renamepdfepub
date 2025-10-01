# Copilot Instructions (Project-Specific)

Authoritative references:
- Root instructions: `.copilot-instructions.md`
- Agent rules: `AGENTS.md`
- Contributing guide: `CONTRIBUTING.md`
- AI usage checklist: `docs/AI_GUIDELINES.md`

Key rules to enforce during suggestions and chat:
- No emojis; sober/professional tone; avoid hype terms (final/ultra/definitivo/melhorado/refinado/superior).
- Use modular, descriptive functions; imports at top; add concise docstrings for new functions; consistent indentation and whitespace.
- Provide meaningful error handling and centralized logging — do not silence exceptions.
- Write tests for each new feature; avoid trivial tests; validate expected UI behaviors when feasible.
- Keep UIs responsive: long tasks run in background with clear feedback; separate preview vs apply.
- Rename placeholders allowed: {title}, {author}, {year}, {publisher}, {isbn}. Validate and warn.
- Consider cascading effects across the codebase; update docs and related code accordingly.
- Cross‑platform (Windows 11, macOS, Debian 13); handle PyQt6 sizing differences on macOS when relevant.
- Keep `requirements.txt` current; prefer project-specific virtualenv (venv/pyenv/direnv).

