WITH cohort AS (
    SELECT * FROM leads
    WHERE organization_id=:org AND dataset_id=:dataset
      AND created_at >= :start AND created_at < :end
), eligible AS (
    SELECT * FROM cohort WHERE source NOT IN ('test','internal') AND deleted_at IS NULL
), facts AS (
    SELECT l.*, r.first_human_response_at,
           o.lead_id IS NOT NULL AS has_outcome,
           o.observation_complete, o.observed_through, o.qualified_at,
           l.created_at + interval '30 days' <= :as_of AS matured,
           (o.observation_complete AND o.observed_through >= l.created_at + interval '30 days')
              IS TRUE AS complete
    FROM eligible l
    JOIN lead_response_facts_v1 r
      ON (r.organization_id,r.dataset_id,r.lead_id)=(l.organization_id,l.dataset_id,l.id)
    LEFT JOIN lead_outcomes o
      ON (o.organization_id,o.dataset_id,o.lead_id)=(l.organization_id,l.dataset_id,l.id)
)
SELECT (SELECT count(*) FROM cohort) AS total_cohort,
       (SELECT count(*) FROM cohort WHERE source IN ('test','internal')) AS excluded_test_internal,
       (SELECT count(*) FROM cohort WHERE source NOT IN ('test','internal')
          AND deleted_at IS NOT NULL) AS excluded_deleted,
       count(*) AS inbound_leads,
       count(*) FILTER (WHERE do_not_contact) AS suppressed_leads,
       count(first_human_response_at) AS response_observed,
       count(*) FILTER (WHERE first_human_response_at IS NULL) AS no_recorded_response,
       percentile_cont(0.5) WITHIN GROUP (
           ORDER BY extract(epoch FROM (first_human_response_at-created_at))/3600.0
       ) AS response_median_hours,
       percentile_cont(0.9) WITHIN GROUP (
           ORDER BY extract(epoch FROM (first_human_response_at-created_at))/3600.0
       ) AS response_p90_hours,
       count(*) FILTER (WHERE matured AND complete) AS qualification_denominator,
       count(*) FILTER (WHERE matured AND complete AND qualified_at IS NOT NULL
          AND qualified_at <= created_at + interval '30 days') AS qualified_30d,
       count(*) FILTER (WHERE NOT matured) AS immature_leads,
       count(*) FILTER (WHERE matured AND NOT complete) AS missing_or_incomplete_outcomes
FROM facts
