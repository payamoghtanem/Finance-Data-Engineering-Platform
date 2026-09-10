-- Gold: month-over-month and year-over-year % change (FR-MODEL-003).
--
-- Defined exactly once, here -- no dashboard or API handler may recompute
-- this logic itself; anything that needs MoM/YoY reads this table.
--
-- KPI charts use the latest known vintage per period (the `qualify` below);
-- a point-in-time "what was known as of date X" query is a different need
-- (FR-API-002, EPIC-12) served directly off fact_economic_observation's
-- full vintage history, not off this table.

with latest_vintage as (
    select
        indicator_id,
        geo_code,
        period,
        period_start,
        value
    from {{ ref('fact_economic_observation') }}
    qualify row_number() over (
        partition by indicator_id, geo_code, period
        order by vintage_date desc
    ) = 1
),

with_lags as (
    select
        indicator_id,
        geo_code,
        period,
        period_start,
        value,
        lag(value, 1) over (partition by indicator_id, geo_code order by period_start) as value_prior_month,
        lag(value, 12) over (partition by indicator_id, geo_code order by period_start) as value_prior_year
    from latest_vintage
)

select
    indicator_id,
    geo_code,
    period,
    period_start,
    value,
    round((value - value_prior_month) / nullif(value_prior_month, 0) * 100, 4) as mom_pct_change,
    round((value - value_prior_year) / nullif(value_prior_year, 0) * 100, 4) as yoy_pct_change
from with_lags
