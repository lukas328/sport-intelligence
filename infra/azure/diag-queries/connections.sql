-- After the infra deploy (#88): connection slots and who holds them (read only).
SHOW max_connections;
SHOW superuser_reserved_connections;
SELECT usename, application_name, state, count(*) FROM pg_stat_activity
 WHERE datname IS NOT NULL GROUP BY 1, 2, 3 ORDER BY 4 DESC;
SELECT name, setting FROM pg_settings WHERE name IN ('log_connections', 'log_disconnections');
