# CLAUDE.md — `docs/` Tree Context

This folder is the entire design and requirements record for the platform. If the root `CLAUDE.md` sent you here, this is the next level of orientation before you drop into a specific subfolder.

## What lives directly in this folder

- `00-glossary.md` — the single canonical definition for every recurring term (English, with the concept explained once). If a document elsewhere uses a term inconsistently with this file, the glossary wins and the document is wrong.
- `01-executive-summary-and-recommendation.md` — the top-level verdict and recommendation. Read this first if you want the 10-minute version of the whole project's design reasoning before diving into any individual document.

## Subfolders and what each owns

| Folder | Owns | Does NOT own |
|---|---|---|
| `business/` | Why the platform exists, who it's for, what a user can do (BRD, PRD) | How it's built (that's `architecture/` and `technical/`) |
| `architecture/` | High-level structure, patterns, and irreversible/expensive-to-reverse decisions (ARD, Solution Design Document, ADRs) | Byte-level schemas or endpoint contracts (that's `technical/`) |
| `requirements/` | Precise, testable requirements and their traceability (FRD, NFR, SRS, traceability matrix) | The reasoning behind an architecture choice (that's `architecture/`) — requirements state *what*, ARD/SDD state *why this shape* |
| `technical/` | Implementation-level detail: schemas, API contracts, event shapes, retry logic | Product rationale (that's `business/`) |
| `data-sources/` | Which external data sources are trustworthy, their license/trust tier, and how they map to `dim_source` | Pipeline implementation for consuming them (that's `technical/`) |
| `ai-agent/` | What the platform's own AI agent is allowed to do, and how that's enforced | General product features (that's `business/PRD.md`) |
| `methodology/` | How the team builds features (EDD + SDD + TDD combined) | What gets built (that's `requirements/`) |
| `learning-guide/` | Standalone teaching material — read independently of every other document | Project-specific decisions (it teaches the general skill, and references this project only as a worked example) |
| `roadmap/` | Sequencing and phase exit criteria | Feature-level detail (link out to FRD/PRD instead of duplicating) |
| `backlog/` | Epics, user stories, and the ready/done gates — the bridge from design to execution | Requirement definitions (that's `requirements/`) — a story cites an FR, it never replaces it |
| `engineering/` | How code is written, reviewed and tested (standards, test strategy) | What to build (that's `technical/`) |

## Cross-document rules

1. **One fact, one home.** If you need to state something already defined elsewhere (a term, a schema, a source's trust tier), link to it — do not restate it, or the two copies will drift.
2. **Every document opens with "why this document / what it answers / how it differs from its neighbors."** This is what lets a reader (human or agent) pick the right document without opening all of them.
3. **Every technical claim in `requirements/` or `technical/` must be traceable** back to a BRD/PRD goal via `requirements/traceability-matrix.md`. An FR with no traceability row is incomplete.
4. **ADRs in `architecture/decisions/` are append-only.** A changed decision gets a new ADR that supersedes the old one; the old one is never edited to pretend it always said the new thing.
5. **English only, and only glossary-defined terms**, with the original non-English term (if any) noted in parentheses only where it aids search (e.g., referencing an external standard's native name).

## Live state

Design docs here describe the system; they do not track progress. **`/STATUS.md` is the
single source of truth for what is done, in progress, and next.** Update it in the same
change as the work — never leave project state in a chat session, which does not persist.
