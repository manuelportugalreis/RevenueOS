SELECT currency, sum(amount) AS amount, count(*) AS opportunity_count
FROM opportunities
WHERE organization_id=:org AND dataset_id=:dataset AND stage NOT IN ('won','lost')
GROUP BY currency ORDER BY currency
