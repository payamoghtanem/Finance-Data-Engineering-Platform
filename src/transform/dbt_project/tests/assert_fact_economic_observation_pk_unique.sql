-- FR-QUAL-003 / data-model.md §3: (indicator_id, geo_code, period, vintage_date)
-- is the declared primary key. A dbt test passes when this returns zero rows.
select indicator_id, geo_code, period, vintage_date, count(*) as n
from {{ ref('fact_economic_observation') }}
group by indicator_id, geo_code, period, vintage_date
having count(*) > 1
