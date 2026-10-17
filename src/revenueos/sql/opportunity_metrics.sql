SELECT count(*) FILTER (WHERE stage='won') AS won,
       count(*) FILTER (WHERE stage='lost') AS lost,
       count(*) AS closed_denominator
FROM opportunities
WHERE organization_id=:org AND dataset_id=:dataset
  AND closed_at >= :start AND closed_at < :end
