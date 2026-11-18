-- Remove the test traces of the external app review in the TV Thalwil account (Lukas' OK, 18.11.).
-- Exact ids from the read-only query of run 44260901992; every step checks its row count and the
-- whole file rolls back on any mismatch (run with --single-transaction, ON_ERROR_STOP).
\set ON_ERROR_STOP on
DO $$
DECLARE n int;
BEGIN
  DELETE FROM plays
   WHERE id = '52a42916-cdfd-4b17-b1ea-6f81eb9068e7' AND name = 'Test Claude Review'
     AND organization_id = '96e03be9-2ea8-4e4c-94d1-3e16cf71a528';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'play: expected 1 row, got %', n; END IF;
  RAISE NOTICE 'play «Test Claude Review» deleted';

  DELETE FROM collections
   WHERE id = 'b4cb9ad4-42dc-4d18-8f39-3de843de2013' AND title = 'Gegen Demo HC Beispiel' AND draft
     AND organization_id = '96e03be9-2ea8-4e4c-94d1-3e16cf71a528';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'collection: expected 1 row, got %', n; END IF;
  RAISE NOTICE 'draft collection «Gegen Demo HC Beispiel» deleted (items cascade)';

  -- Teamleben back off; it holds no trainings, slots or attendances (switching off deletes nothing)
  UPDATE teams SET settings = settings || '{"team_features": false}'::jsonb
   WHERE id = '13d6190c-4fc3-440c-a647-42375a237b57'
     AND organization_id = '96e03be9-2ea8-4e4c-94d1-3e16cf71a528'
     AND settings->>'team_features' = 'true';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'team: expected 1 row, got %', n; END IF;
  RAISE NOTICE 'Teamleben switched off for team TV Thalwil';
END $$;
