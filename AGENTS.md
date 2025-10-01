# AGENTS Guidelines (Codex, Copilot, and Others)

This repository uses AI assistants for day-to-day development. The rules below instruct any agent (Codex CLI, Copilot Chat, etc.) how to act when editing this codebase. They are binding for the entire repository.

## Mission and Scope
- Be surgical and precise: implement exactly what was requested, nothing broader.
- Preserve existing behavior, language (PT-BR labels), and structure.
- Prefer incremental improvements over refactors unless explicitly requested.

## Editing Conduct
- Never use emojis. Keep tone sober, professional, and neutral.
- Avoid hype words in UI/docs like: “final”, “profissional”, “ultra”, “definitivo”, “melhorado”, “refinado”, “superior”, etc.
- Use modular code: specialized, descriptive functions; group related logic; avoid scattering adaptations across the codebase.
- Always declare imports at the top of each file.
- Keep lines reasonably short; do not introduce unnecessary trailing spaces; ensure consistent indentation.
- Add a short docstring to each new function describing purpose and parameters.
- Maintain cross-platform support (Windows 11, macOS, Linux/Debian 13). Add OS checks when needed (e.g., PyQt6 font/spacing differences on macOS).
- Respect existing naming, file structure, and entry points.

## Error Handling, Logging, and Rollback
- Do not add try/except blocks only to silence errors. Provide meaningful handling and user feedback.
- Centralize logging through the project’s logging utilities when available; do not print stack traces directly to the UI.
- Ensure there is a safe way to revert actions:
  - Prefer dry-run modes first.
  - Write backups before destructive DB/file operations.
  - Separate preview from apply steps.

## UI/UX (Streamlit, PyQt, Web)
- Add inline guidance and non-blocking validation (warnings) near inputs.
- Group related controls into a single row when it improves clarity (e.g., padrão/underscore/preview/apply).
- Keep web UIs responsive: long tasks must run in background; provide clear progress/feedback.
- Text must be sober and objective; avoid jokes or “cringe”.
- Prefer simple, dependency-free helpers (e.g., clipboard via small HTML snippet).

## Naming and Patterns
- Allowed rename placeholders: {title}, {author}, {year}, {publisher}, {isbn}.
- Validate patterns and warn the user; do not block the interface unless necessary.
- Keep sanitization consistent (ASCII fallback, spaces, underscore option).

## CLI and Background Work
- Avoid very long terminal invocations and quoting pitfalls; prefer config files or short flags.
- Run heavy operations in background processes; surface start/completion feedback to the user.
- Maintain entry points behavior and help messages; do not break existing CLIs.

## Tests and Validation
- Write a test for each new feature (unit or integration) following existing patterns.
- Do not add tests that always return the same result; ensure semantic coverage and expected UI behaviors.
- Validate user interactions and interface states where applicable.
- When changing code, consider cascading effects and update affected tests.

## Documentation and Change Tracking
- Update relevant docs with any behavior change.
- Keep a concise list of what was done and what remains (plans, TODOs, CHANGELOG entries as appropriate).
- Use professional writing; avoid emojis and hype terms.

## Performance and Reliability
- Favor efficient queries, limited previews, and bounded log reads.
- Ensure background tasks do not block UI threads.
- Aim for robust, cross-platform behavior (macOS, Windows, Linux).

## Requirements and Environment
- Keep requirements.txt up to date.
- Projects must be runnable on Windows 11, macOS, and Debian 13 when feasible.
- Prefer using a project-specific virtual environment (e.g., via venv/pyenv/direnv) and provide scripts to activate/deactivate when available.

## Git and Collaboration
- Follow existing branch protections; use PRs when required.
- Keep commit messages short and focused on the change.
- Do not introduce destructive actions without explicit user approval.

