---
description: Scaffold a new data source connector following the required order of work
argument-hint: <source-name>
---

Add a connector for: **$1**

Follow this order strictly — do not skip to implementation.

1. **Licence gate first.** Check `docs/data-sources/catalog.md` for $1. Apply the
   five-question test in `docs/data-sources/CLAUDE.md`. If the licence does not permit
   storage/redistribution, **stop and report** — a failing source is never wired up,
   however good the data is.
2. **Spec.** Add or confirm the `FR-ING-xxx` requirement in `docs/requirements/FRD.md`,
   and add its row to `docs/requirements/traceability-matrix.md` in the same change.
3. **Contract.** Write `src/connectors/$1/contract.yaml` per
   `docs/architecture/solution-design-document.md` §4, and the `dim_source` row per
   `docs/technical/data-model.md`.
4. **Tests before code.** Write unit tests (retry, parsing, key derivation) and an
   idempotency test that runs the job twice and asserts identical state.
5. **Implement** `connector.py` until tests pass. Raw response is persisted with a
   SHA-256 checksum **before** any parsing.
6. **Wire the event** — emit `raw_data.received`; downstream advances only on
   `raw_data.validated`.
7. **DLQ** — every failure path routes to the dead-letter queue. No silent drops.
8. **Finish:** `README.md` for the package, a runbook entry, and update `STATUS.md`.

Check `docs/backlog/definition-of-done.md` before opening a PR.
