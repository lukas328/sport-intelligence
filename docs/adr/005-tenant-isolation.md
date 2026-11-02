# 005. Tenant isolation: application scoping plus Postgres Row Level Security

- Status: accepted (implemented from M1)
- Date: 2026-11-02

## Decision
1. Every tenant table has `organization_id` (`TenantMixin`). Repositories always filter by the current
   organisation, and policies (BRIEF 3) are enforced per resource in the service layer.
2. Second line of defence: Postgres RLS. The API connects as a non-owner role `app_user`; each request
   transaction runs `SET LOCAL app.current_org = '<uuid>'` and policies use `app_current_org()`
   (created in migration 0001). Tables use `FORCE ROW LEVEL SECURITY`.
3. Platform admin and background jobs use explicit, audited bypass paths.
4. Tests: a cross-tenant test suite tries to read and write every resource of org B as org A, at API
   and at DB level.
