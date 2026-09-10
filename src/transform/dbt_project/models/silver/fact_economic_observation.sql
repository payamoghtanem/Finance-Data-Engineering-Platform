-- Silver: canonical economic-indicator observations (FR-MODEL-001, FR-MODEL-002).
--
-- Reads Bronze's untouched raw JSON in place (never re-fetches from the
-- source, per ARD §2.2) and conforms it to one shape any source can populate.
-- `seed_dataset_indicator_map` is what makes this source-agnostic: adding a
-- second source (e.g. Eurostat, EPIC-14) means adding a mapping row and a
-- parsing branch below, not a new fact table — see the model's schema.yml
-- for the current single-source honesty note.
--
-- Time fields (FR-MODEL-002, US-05-002) — six distinct fields, none derived
-- from another at query time:
--   * period / period_start / period_end : the calendar period this
--     observation covers, computed once here from the source's own date.
--   * vintage_date  : FRED's `realtime_start` — the date this specific
--     revision of the value became the known value (ALFRED/FRED vintage
--     semantics), part of the primary key so a later revision is a new row,
--     not an overwrite.
--   * retrieved_at  : copied from Bronze's own `retrieved_at` (when the
--     connector fetched the payload) — never recomputed here.
--   * processed_at  : when *this* dbt run built the row (`run_started_at`),
--     distinct from `retrieved_at` and `ingested_at` by construction.
--   * published_at  : FRED's per-observation JSON does not expose a
--     publication timestamp distinct from realtime_start — left NULL rather
--     than faked as a copy of vintage_date. See schema.yml.

with bronze_fred as (
    select
        dataset_id,
        source_id,
        retrieved_at,
        payload
    from {{ source('bronze', 'bronze_raw_records') }}
    where dataset_id in (select dataset_id from {{ ref('seed_dataset_indicator_map') }})
),

exploded as (
    select
        b.dataset_id,
        b.source_id,
        b.retrieved_at,
        obs.value ->> 'date' as observed_date_text,
        obs.value ->> 'value' as raw_value_text,
        obs.value ->> 'realtime_start' as vintage_date_text
    from bronze_fred b,
        json_each(json_extract(decode(b.payload), '$.observations')) as obs
),

mapped as (
    select
        e.*,
        m.indicator_id,
        m.geo_code
    from exploded e
    inner join {{ ref('seed_dataset_indicator_map') }} m
        on e.dataset_id = m.dataset_id
),

typed as (
    select
        indicator_id,
        geo_code,
        strftime(cast(observed_date_text as date), '%Y-%m') as period,
        date_trunc('month', cast(observed_date_text as date))::date as period_start,
        (date_trunc('month', cast(observed_date_text as date)) + interval '1 month' - interval '1 day')::date
            as period_end,
        cast(vintage_date_text as date) as vintage_date,
        try_cast(raw_value_text as decimal(28, 8)) as value,
        retrieved_at
    from mapped
    -- FRED's own convention for a missing observation is the literal "."
    where raw_value_text is not null and raw_value_text != '.'
)

select
    t.indicator_id,
    t.geo_code,
    t.period,
    t.period_start,
    t.period_end,
    t.vintage_date,
    t.value,
    i.unit,
    i.seasonal_adjustment,
    cast(null as timestamp) as published_at,
    t.retrieved_at,
    cast('{{ run_started_at.strftime("%Y-%m-%d %H:%M:%S%z") }}' as timestamptz) as processed_at
from typed t
inner join {{ ref('seed_dim_indicator') }} i using (indicator_id)
where t.value is not null
qualify row_number() over (
    partition by t.indicator_id, t.geo_code, t.period, t.vintage_date
    order by t.retrieved_at desc
) = 1
