# AI Usage Guidelines

This document complements `AGENTS.md` with practical notes for Codex/Copilot and other assistants.

## How to Engage
- Start by reading the surrounding code and following the existing patterns.
- For multi-step tasks, outline a short plan and keep it updated.
- Before running commands, provide a brief preamble of what you will do next.

## Implementation Checklist
- [ ] No emojis or hype words in UI/docs
- [ ] Imports at top; modular, descriptive functions
- [ ] Meaningful error handling; centralized logging
- [ ] Pattern validation with allowed placeholders: {title}, {author}, {year}, {publisher}, {isbn}
- [ ] UI warnings instead of hard failures; responsive background work
- [ ] Tests added/updated for new features; meaningful assertions
- [ ] Docs updated; short summary of changes
- [ ] Cross-platform behavior verified (Windows/macOS/Linux)
- [ ] Avoid overly long CLI command lines and quoting pitfalls
- [ ] Preview vs apply separation; backups/dry-run where relevant

## Do and Don’t
Do:
- Be concise and professional in messages.
- Keep changes minimal and reversible.
- Validate cascading effects and keep consistency across the codebase.

Don’t:
- Suppress errors without handling.
- Introduce blocking UI waits for long tasks.
- Scatter logic changes across unrelated areas.

