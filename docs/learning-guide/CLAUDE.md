# CLAUDE.md — `docs/learning-guide/`

## Purpose

`system-design-guide.md` is deliberately **standalone**: a reader (human or agent) should be able to open only this one file and come away understanding how to design a data engineering platform in general — the criteria, the topics to consider, the constraints/risks/impacts, the questions to ask, where to find trustworthy answers, and how to evaluate tools/frameworks (including explicit "why not") — using this project only as a running, concrete example.

## Why this is separate from the rest of `docs/`

Every other document in this repository documents a *decision already made* for *this specific platform*. This document teaches the *general skill* of making those decisions in the first place. Conflating the two would force a reader who just wants to learn system design to wade through project-specific detail, and would force a reader who just wants this project's decisions to wade through generic pedagogy.

## Editing rules

- Keep this document's core teaching content generically applicable — if you add a project-specific detail, clearly mark it as "(this project's choice: ...)" so it doesn't get mistaken for a universal rule.
- When this document references "where to find trustworthy answers," it must point to primary/official sources (vendor docs, open-source project docs, standards bodies) in the same spirit as `../data-sources/catalog.md`'s own source-reliability criteria — don't cite secondary blog commentary as if it were a primary source.
