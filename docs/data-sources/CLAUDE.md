# CLAUDE.md — `docs/data-sources/`

## Purpose

`catalog.md` is the vetted inventory of external data sources this platform is allowed to pull from — organized first by "global MVP-priority sources" (FRED/ALFRED, World Bank, Eurostat/SDMX, SEC EDGAR, CoinGecko) and then by an eight-country reference catalog (Germany, UK, China, Japan, USA, India, Russia, Canada) condensed from a verified-sources research pass.

## The rule this folder enforces

**A source is not "reliable" just because it's free or scrapeable.** Every entry in `catalog.md` is evaluated on five criteria before it's trusted:

1. Who is the actual publisher — official body, exchange, central bank, licensed commercial provider, or an aggregator of unclear origin?
2. Does the license/terms of use actually permit storage, redistribution, and (if relevant) commercial use?
3. What is the data's latency — real-time, 15-minutes-delayed, daily, monthly?
4. Does it provide historical data, revisions, versions, and metadata (not just a current snapshot)?
5. Is there a clear SLA, rate limit, and change-notification process?

A source that fails #2 (license) must never be wired into an ingestion connector, however good the data looks — see `../requirements/FRD.md` for the connector requirements this gates, and `ADR` entries in `../architecture/decisions/` for any source-selection decision significant enough to warrant one.

## How this maps to the data model

Every source in `catalog.md` should be representable as a row in `dim_source` (see `../technical/data-model.md`), with `license_url`, `terms_version`, `redistribution_allowed`, `attribution_text`, and a `trust_tier`. If a source can't honestly populate those fields, it isn't ready to be added to the catalog as "usable," even if it's listed for reference.

## Scraping warning (do not relax this)

Web scraping of a public site is explicitly **not** an acceptable primary ingestion method for production use in this project (see `../architecture/ARD.md` principle 7 and `catalog.md`'s own scraping warning section). Unofficial libraries wrapping consumer sites (e.g., unofficial Yahoo Finance wrappers) are fine for learning/prototyping only, never as the ingestion backbone for anything the platform calls a "data product."
