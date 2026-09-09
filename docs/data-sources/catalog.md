# Data Source Catalog

**What this document answers:** which free/official/licensed sources are trustworthy for this platform, for which domain, and with what caveats?
**How it differs from its neighbors:** `../architecture/ARD.md` and `../requirements/FRD.md` assume sources are already vetted; this document is where that vetting happens and is recorded, feeding `dim_source` in `../technical/data-model.md`.

## 1. The five-question test every source must pass

Before any source is wired into a connector (`FR-ING-006`), it is evaluated against:

1. **Who is the actual publisher?** An official body, central bank, exchange, licensed commercial provider — or an aggregator of unclear origin?
2. **Does the license actually permit storage and redistribution** (and commercial use, if relevant)? "Publicly viewable" is not the same as "licensed to store and redistribute."
3. **What is the data's latency** — real-time, delayed, daily, monthly?
4. **Does it provide historical data, revisions, and metadata** — not just a current snapshot?
5. **Is there a clear SLA, rate limit, and change-notification process?**

A source that fails question 2 must never back a connector that this platform calls a "data product," however good the data looks — see the scraping warning in §5.

## 2. Trust tiers (used in `dim_source.trust_tier`)

| Tier | Meaning | Example |
|---|---|---|
| `official` | Government agency, central bank, primary regulator/exchange, or a standards body | FRED, Eurostat, SEC EDGAR |
| `licensed_commercial` | Commercial provider with clear terms permitting the platform's use | A paid market-data vendor (not used in the free MVP) |
| `reputable_media_analytics` | High-credibility journalism or analytics platform, used for *context*, not as a primary data backbone | Reuters, Financial Times, Morningstar |
| `community_unofficial` | Unofficial wrapper, scraped, or community-maintained — prototyping/learning only | Unofficial Yahoo Finance libraries |

## 3. Global MVP-priority sources (start here)

| Domain | Source | Trust tier | Key notes |
|---|---|---|---|
| Macroeconomics (US) | **FRED / ALFRED** (Federal Reserve Bank of St. Louis) | `official` | Free API key required; huge time-series library; ALFRED preserves historical vintages — essential for point-in-time queries (FR-API-002) |
| Macroeconomics (global) | **World Bank Indicators API** | `official` | No API key required; ~16,000 time series across 45+ databases; not suited to intraday/market data |
| Macroeconomics (EU) | **Eurostat (SDMX 2.1/3.0 API)** | `official` | Free; official EU statistics; SDMX dimension/codelist modeling required (FR-ING-003) |
| Corporate filings (US) | **SEC EDGAR / data.sec.gov** | `official` | Free, public; automated access must comply with SEC's fair-access policy (declared User-Agent, rate discipline) |
| Crypto | **CoinGecko (Demo API)** | `reputable_media_analytics` (free tier; treat historical depth as limited, not `official`) | Free tier has endpoint and rate limits; demo history capped at 365 days — do not assume permanence of this tier's terms |
| Equity market data | *(no free tier recommended as a production backbone)* | — | See the mandatory warning in §5 — a licensed/official provider is required for anything beyond prototyping |

## 4. Country-level reference catalog (context and expansion sources)

Condensed from a structured multi-country research pass. These are primarily useful for **context, cross-checking, and eventual expansion** beyond the MVP-priority sources above — each still requires the five-question test in §1 before backing a connector, and most in the "media/analytics" and "commercial terminal" rows are `reputable_media_analytics` or `licensed_commercial`, not `official`, unless noted.

### Germany

| Category | Representative sources | Tier |
|---|---|---|
| Official statistics/regulation | Destatis (Federal Statistical Office), Deutsche Bundesbank, BaFin (financial supervision + MiCAR crypto rules), ECB | `official` |
| Exchange | Deutsche Börse / Börse Frankfurt (DAX family indices) | `official` |
| Energy | Bundesnetzagentur / SMARD (electricity & gas market data) | `official` |
| Corporate filings | Unternehmensregister (official balance sheets, free access from 2022) | `official` |
| Fundamentals/analytics | Eulerpool, finanzen.net, onvista, Morningstar Deutschland, AlleAktien | `reputable_media_analytics` |

### United Kingdom

| Category | Representative sources | Tier |
|---|---|---|
| Official statistics/regulation | Office for National Statistics (ONS), Bank of England (incl. yield curves, Financial Stability Report), UK Debt Management Office, HM Treasury, FCA (incl. Cryptoassets regime), HMRC | `official` |
| Exchange | London Stock Exchange, FTSE Russell/LSEG Indices | `official` |
| Media | Financial Times, Reuters, BBC Business, The Economist | `reputable_media_analytics` |
| Fundamentals/analytics | Morningstar UK, Stockopedia, Trustnet, LSEG/Refinitiv | `reputable_media_analytics` / `licensed_commercial` |

### China

| Category | Representative sources | Tier |
|---|---|---|
| Official statistics/regulation | National Bureau of Statistics (NBS), People's Bank of China (PBOC, incl. e-CNY), Ministry of Finance, CSRC, SAFE | `official` |
| Exchanges | Shanghai Stock Exchange, Shenzhen Stock Exchange, ChinaBond/CCDC | `official` |
| Commercial terminals | Wind Information, CEIC Data, CSMAR — institutional-grade, subscription | `licensed_commercial` |
| Media | Caixin Global, Yicai, SCMP Economy | `reputable_media_analytics` |
| Open-source toolkits | Tushare, AkShare (community Python libraries drawing on public sources) | `community_unofficial` — verify each underlying source individually |

### Japan

| Category | Representative sources | Tier |
|---|---|---|
| Official statistics/regulation | Bank of Japan (BOJ), Ministry of Finance (JGBs), e-Stat (official statistics portal, API available), Financial Services Agency (FSA) | `official` |
| Exchange/disclosure | Japan Exchange Group (JPX), EDINET (mandatory securities disclosure, XBRL, API available — Japan's SEC EDGAR equivalent) | `official` |
| Media | Nikkei / Nikkei Asia, NHK Economy | `reputable_media_analytics` |

### United States (expansion beyond MVP-priority list)

| Category | Representative sources | Tier |
|---|---|---|
| Official | Federal Reserve Board, BEA, BLS, US Census Bureau, US Treasury / TreasuryDirect / FiscalData, EIA (energy), CFTC | `official` |
| Ratings | S&P Global Ratings, Moody's, Fitch | `licensed_commercial` (ratings themselves; some research free) |
| Fundamentals/analytics | Macrotrends, StockAnalysis.com, Finviz, Morningstar | `reputable_media_analytics` |
| Crypto (beyond CoinGecko) | CoinMarketCap, Messari, Glassnode, DefiLlama | `reputable_media_analytics` |

### India

| Category | Representative sources | Tier |
|---|---|---|
| Official statistics/regulation | Reserve Bank of India (RBI, incl. DBIE database), SEBI, MoSPI (national statistics), NITI Aayog | `official` |
| Exchanges | National Stock Exchange (NSE), Bombay Stock Exchange (BSE) | `official` |
| Ratings | CRISIL, ICRA, CARE Ratings, India Ratings | `licensed_commercial` |
| Media/analytics | Moneycontrol, The Economic Times, Screener.in, Trendlyne | `reputable_media_analytics` |

### Russia

| Category | Representative sources | Tier |
|---|---|---|
| Official | Bank of Russia (CBR, incl. DFA/crypto regulation), Ministry of Finance (OFZ), Rosstat | `official` |
| Exchange | Moscow Exchange (MOEX) | `official` |
| Caveat | Sanctions/geopolitical conditions materially affect data availability and interpretation; cross-verify against IMF/World Bank/OECD external reporting | — |

### Canada

| Category | Representative sources | Tier |
|---|---|---|
| Official | Statistics Canada (StatCan), Bank of Canada (incl. Valet API), Canada Energy Regulator, OSFI (bank regulation) | `official` |
| Filings/exchange | SEDAR+ (official company filings — Canada's SEC EDGAR equivalent), TMX Group / Toronto Stock Exchange | `official` |
| Research | Big Six bank research desks (RBC, TD, Scotiabank, BMO, CIBC, National Bank), Morningstar Canada | `reputable_media_analytics` / `licensed_commercial` |

*(This country catalog is a starting reference set, not exhaustive — the full underlying research pass covers 80–120+ sources per country. Add a source here, with its trust tier and license status resolved, before it backs any connector.)*

## 5. Mandatory warning: equity market data specifically

**"Verifiable from a public website" is not the same as "official or licensed."**

- Do not use website scraping as the ingestion backbone for anything this platform calls a production "data product" (this is a direct instance of `../architecture/ARD.md` §2.7/§2.8 discipline, not a separate rule).
- Unofficial API wrapper libraries (e.g., informal Yahoo Finance clients) are acceptable for personal learning and prototyping only — they carry no contractual guarantee of stability and are `community_unofficial` tier, never higher.
- Real-time equity market data is almost always subject to exchange licensing and redistribution agreements; treat "free real-time equity data, redistributable" as **not a safe assumption** anywhere in this platform's design.
- For the MVP, prioritize daily/delayed data, macro indicators, official filings, and crypto — see §3 — over real-time equities.
- Every dataset treated as a real data product must populate `license_url`, `terms_version`, `redistribution_allowed`, `attribution_text`, and `source_retrieved_at` in `dim_source` (`../technical/data-model.md`).

## 6. Relationship to other documents

- `dim_source` in `../technical/data-model.md` is the queryable, pipeline-facing version of this catalog.
- `FR-ING-006` in `../requirements/FRD.md` requires a resolved catalog entry before any connector goes to production.
- `../ai-agent/agentic-ai-design.md`'s retrieval scope includes this catalog specifically so the agent can answer "is this source trustworthy" using the same criteria as the pipeline itself, never an improvised judgment.
