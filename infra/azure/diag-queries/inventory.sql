-- Inventory for the move of staging to an EU region (read only; counts, no e-mail values).
\echo '== size'
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
\echo '== organizations'
SELECT count(*) AS organizations FROM organizations;
\echo '== users by kind (test: our own domain, example domains, «test» or «e2e» in the address)'
SELECT CASE WHEN email ILIKE '%@handball-intelligence.com' OR email ILIKE '%@example.%'
              OR email ILIKE '%test%' OR email ILIKE '%e2e%' THEN 'test' ELSE 'other' END AS kind,
       count(*) AS users,
       count(*) FILTER (WHERE created_at > now() - interval '14 days') AS new_14_days
FROM users GROUP BY 1 ORDER BY 1;
\echo '== organizations with at least one non-test member'
SELECT count(DISTINCT m.organization_id) AS orgs_with_other_users
FROM org_memberships m JOIN users u ON u.id = m.user_id
WHERE NOT (u.email ILIKE '%@handball-intelligence.com' OR u.email ILIKE '%@example.%'
           OR u.email ILIKE '%test%' OR u.email ILIKE '%e2e%');
\echo '== matches'
SELECT count(*) AS matches, count(*) FILTER (WHERE is_demo) AS demo FROM matches;
\echo '== video assets by status, with stored bytes'
SELECT status, count(*) AS assets, pg_size_pretty(coalesce(sum(size_bytes), 0)::bigint) AS bytes
FROM video_assets GROUP BY status ORDER BY status;
\echo '== where the files are: storage key prefixes are org/match/asset in the bucket (count of assets with a key)'
SELECT count(*) FILTER (WHERE storage_key IS NOT NULL) AS with_storage_key, count(*) AS all_assets FROM video_assets;
\echo '== processing jobs by kind and status'
SELECT kind, status, count(*) AS jobs FROM processing_jobs GROUP BY kind, status ORDER BY kind, status;
