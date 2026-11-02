-- Local only. Runtime role without superuser/BYPASSRLS so that Row Level Security applies (ADR 005).
-- In production the role is created by Terraform with a secret from the secret manager.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'handball_app') THEN
    CREATE ROLE handball_app LOGIN PASSWORD 'handball_app' NOSUPERUSER NOBYPASSRLS;
  END IF;
END $$;
