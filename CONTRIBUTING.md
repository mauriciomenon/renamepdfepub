# Contributing Guidelines

These conventions apply to all contributors (humans and AI assistants) to ensure consistency, safety, and quality across the project.

## Principles
- Be precise: implement only what is requested; avoid broad refactors.
- Keep tone professional and sober. Never use emojis. Avoid hype terms (e.g., final, ultra, definitivo, melhorado, refinado, superior).
- Respect existing structure, naming, and entry points.
- Maintain cross-platform compatibility (Windows 11, macOS, Debian 13) whenever possible.

## Development Environment
- Use a project-specific virtual environment (venv/pyenv/direnv). Suggested name: `venv-renamepdfepub` or similar.
- Keep `requirements.txt` updated when dependencies change.
- Provide activation/deactivation scripts if using pyenv/direnv.

## Code Style
- Place all imports at the top of files.
- Prefer modular, descriptive functions; group related logic.
- Add a short docstring to each new function (purpose and parameters).
- Keep lines reasonably short; avoid unnecessary whitespace; ensure consistent indentation.
- Do not add try/except solely to silence errors; implement meaningful handling and user feedback.
- Use centralized logging utilities (do not print raw stack traces to UIs).

## UI/UX
- Provide inline guidance and non-blocking validation (warnings) near inputs.
- Group related controls into a single row when it improves clarity (e.g., padrão/underscore/preview/apply).
- Keep interfaces responsive: long operations in background with clear progress/feedback.
- Use neutral, professional language. Avoid jokes or informal tone.

## Rename Patterns
- Allowed placeholders: `{title}`, `{author}`, `{year}`, `{publisher}`, `{isbn}`.
- Validate patterns and warn users; do not hard-fail UI on simple mistakes.
- Keep filename sanitization consistent (ASCII fallback, underscore option).

## CLI and Background Tasks
- Avoid very long command invocations; prefer short flags or config files.
- Ensure entry points support `--help` (and `--version` if applicable) and remain backward compatible.
- Use background processes for heavy tasks; present start/completion feedback.

## Testing and Validation
- Add tests for each new feature. Avoid trivial tests that always pass; ensure semantic coverage.
- Validate expected UI interactions and states where reasonable.
- Consider cascading effects of changes and update impacted tests.

## Documentation and Change Tracking
- Update docs when behavior changes.
- Maintain a succinct list of completed work and remaining tasks (CHANGELOG, TODOs, or plan tool).

## Safety and Rollback
- Prefer dry-runs before modifications.
- Backup data before destructive DB/file operations.
- Keep preview vs apply as separate steps to allow easy rollback.

## Cross-Platform Notes
- Use OS checks for behavior differences (e.g., PyQt6 fonts/spacing on macOS).
- Ensure file operations (open folder/file) work on Windows/macOS/Linux.

## Git Workflow
- Follow branch protections and open PRs as required.
- Use clear, focused commit messages.
- Avoid destructive operations unless explicitly approved.

