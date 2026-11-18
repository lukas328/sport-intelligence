-- Test traces of the external app review in the TV Thalwil account (BEFUNDE-3): read only.
\pset format aligned
SELECT o.id AS org_id, o.name, o.created_at FROM organizations o WHERE o.name ILIKE '%thalwil%';
SELECT t.id AS team_id, t.name, t.settings->'team_features' AS team_features, t.updated_at
FROM teams t JOIN organizations o ON o.id = t.organization_id WHERE o.name ILIKE '%thalwil%';
SELECT p.id, p.name, p.category, p.created_at, p.updated_at
FROM plays p JOIN organizations o ON o.id = p.organization_id WHERE o.name ILIKE '%thalwil%' ORDER BY p.created_at;
SELECT c.id, c.title, c.draft, c.match_id, c.created_at,
       (SELECT count(*) FROM collection_items i WHERE i.collection_id = c.id) AS items
FROM collections c JOIN organizations o ON o.id = c.organization_id WHERE o.name ILIKE '%thalwil%' ORDER BY c.created_at;
-- what Teamleben holds in this account (switching it off deletes nothing, but shows what is in use)
SELECT 'training_sessions' AS what, count(*) FROM training_sessions s JOIN organizations o ON o.id = s.organization_id WHERE o.name ILIKE '%thalwil%'
UNION ALL SELECT 'training_slots', count(*) FROM training_slots s JOIN organizations o ON o.id = s.organization_id WHERE o.name ILIKE '%thalwil%'
UNION ALL SELECT 'attendances', count(*) FROM attendances s JOIN organizations o ON o.id = s.organization_id WHERE o.name ILIKE '%thalwil%';
