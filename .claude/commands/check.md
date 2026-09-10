---
description: Run every quality gate CI would run
---

Run these and report a pass/fail table. Do not fix anything yet — report first.

```bash
./scripts/check_doc_links.sh
./scripts/check_traceability.sh
```

If `src/` exists, also run:

```bash
ruff check src tests
ruff format --check src tests
mypy src
pytest tests/unit
```

Then state clearly whether this branch would pass CI, and list any failure with the
file and line. If everything passes, say so plainly without hedging.
