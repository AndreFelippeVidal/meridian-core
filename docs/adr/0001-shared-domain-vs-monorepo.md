# ADR 0001 — Shared domain library (`meridian-core`) vs monorepo

- **Status:** Accepted
- **Date:** 2026-06-29

## Context

The Meridian portfolio consists of multiple independent project repos (one per project) so each
project is browsable on its own by recruiters without navigating a monorepo. The shared fictional
domain — synthetic generators for customers, products, orders, etc. — must stay consistent across
all projects. Without a central package, each repo would vendor its own copy and they would drift.

## Decision

Extract the shared domain into a standalone, installable Python package (`meridian-core`) hosted in
its own GitHub repo. Portfolio projects depend on it via a git-tag pin in `pyproject.toml`:

```toml
"meridian-core @ git+https://github.com/AndreFelippeVidal/meridian-core@vX.Y.Z"
```

## Rationale

- **Consistency** — one source of truth; column names and ID formats never diverge across projects.
- **Recruiter legibility** — each project repo remains self-contained and browsable.
- **Semver discipline** — adding domain entities (e.g., products, orders for Project 1) requires
  a deliberate version bump and tag, making the dependency explicit and auditable.
- **No monorepo tooling** — avoids the overhead of Nx, Turborepo, or path-dependency hacks while
  still sharing code.

## Consequences

- Downstream projects must update their pin when `meridian-core` changes (intentional friction).
- CI on project repos needs network access to clone the git dep (standard on GitHub Actions).
- The first real test of this workflow is the v0.2.0 cycle, when Project 1 adds `products`,
  `orders`, `order_items`, and `payments` entities.
