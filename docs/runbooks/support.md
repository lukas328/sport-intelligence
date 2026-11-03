# Support procedures

- **Reprocess a match:** backoffice `/ops` → failed jobs → "Erneut starten" (once per failed job), or
  as coach in the match view. Re-analysis keeps manual track identities.
- **Extend a trial:** `/ops` → club → "14 Tage Verein testen" (audited).
- **Lost 2FA device:** first the person uses one of their recovery codes. Without codes: verify identity via the club admin (call back the number on file) and the
  account e-mail; then disable TOTP for the account in the database with an audit entry. Ask the person
  to enable it again immediately.
- **Data subject requests:** export and deletion are self-service (settings → "Daten und Konto"). For
  players without an account, the club (controller) deletes the roster entry; video stays with the club.
  Respond within 30 days; record the request in the support log.
- **Club deletion with a running subscription:** cancel in the Stripe portal first, then delete.
