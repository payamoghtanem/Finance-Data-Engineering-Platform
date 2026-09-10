-- FR-MODEL-002 / US-05-002: "collapsing these into a single date field is a
-- defect, not a simplification." Fails (returns rows) if period_start and
-- period_end were ever collapsed into the same value, or if processed_at
-- was populated before retrieved_at -- either would indicate two of the six
-- time fields got aliased to one another instead of independently populated.
select indicator_id, geo_code, period, vintage_date
from {{ ref('fact_economic_observation') }}
where period_start = period_end
   or processed_at < retrieved_at
