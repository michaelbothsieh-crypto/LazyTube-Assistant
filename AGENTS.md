# AGENTS.md

This file defines repository-wide guidance for LazyTube-Assistant.

## Engineering Principles

- Follow SOLID when changing production code: keep responsibilities focused, dependencies explicit, and extension points small.
- Preserve SSOT (single source of truth): avoid duplicating business rules, prompt formats, command routing, or notification behavior across modules.
- Preserve SRP (single responsibility principle): each module, class, and function should own one clear reason to change.
- Prefer existing project utilities and patterns before adding new abstractions.
- Keep changes small, testable, and reversible.
- Run the relevant tests before claiming completion.
