SELECT source, count(*) AS lead_count
FROM leads
WHERE organization_id=:org AND dataset_id=:dataset AND created_at >= :start AND created_at < :end
  AND source NOT IN ('test','internal') AND deleted_at IS NULL
GROUP BY source ORDER BY source
