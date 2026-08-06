# ADR 0001 — Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-08-06

## Context

RentFlow spans a frontend, a backend, a database and cloud infrastructure. Decisions made early — the auth model, the multi-tenancy approach, how money is stored — are expensive to reverse and easy to forget the reasoning behind. Commit messages and PR threads scatter that reasoning across places nobody rereads.

## Decision

Record significant architectural decisions as numbered Markdown files in `docs/adr/`, one per decision, using the template below. A decision is significant if reversing it would touch multiple layers, change the database schema, or alter a security boundary.

An ADR is never edited after acceptance except to change its status. To change a decision, write a new ADR that supersedes it.

## Consequences

- New contributors can read why the system is shaped this way without asking.
- Slight overhead per significant decision — acceptable, and a filter against churn on choices that were never actually contested.
- The ADR list becomes the honest changelog of the architecture.

---

## Template

```markdown
# ADR NNNN — <title>

- **Status:** Proposed | Accepted | Superseded by ADR-NNNN
- **Date:** YYYY-MM-DD

## Context
What forces are at play? What constraints apply?

## Decision
What was decided, stated in the active voice.

## Consequences
What becomes easier, what becomes harder, what is now hard to reverse.

## Alternatives considered
What else was on the table, and why it lost.
```
