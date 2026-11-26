# Incidents

1. **Triage (5 min):** `/readyz`, error rate, `/internal/stats`, recent deploys. Assign one incident lead.
2. **Mitigate:** roll back the last deploy, scale workers, pause GPU queue consumers if a pipeline bug
   corrupts results (videos stay playable, analyses can be rerun).
3. **Communicate:** status page / in-app banner; affected clubs by e-mail for anything longer than 1 h.
4. **Data protection:** suspected personal data breach (e.g. cross-tenant access): preserve logs and
   audit entries, assess within 24 h; notify the FDPIC/supervisory authority without undue delay
   (revDSG Art. 24, GDPR Art. 33: 72 h) and affected clubs as controllers. Tenant isolation tests and
   the policy matrix must be extended with a reproducing case before closing.
5. **Post-mortem** within 5 working days, blameless, with actions in the backlog.

## Errors in the browser

The web app reports errors it hits in a browser (React's recoverable errors such as hydration
mismatches, uncaught errors, unhandled promise rejections) to `POST /v1/client-errors`
(`apps/web/src/lib/client-errors.ts`, `apps/api/src/handball_api/routers/client_errors.py`).
Nothing personal: error code and message, stack, route with ids masked, build (`NEXT_PUBLIC_BUILD`:
the commit when the build gets `GIT_SHA`, else the build time) and the kind of device; no cookies,
at most five per browser session and 30 per address in ten minutes. Each lands as one API log line
`client_error`; the staging diagnosis lists the last 24 hours («client errors from browsers»). In
production builds React's messages are minified (`#418` = hydration mismatch) and the stack has
no component names: the route, the device and the count narrow it down, a local build of the same
page gives the full message. A hydration error carries `dom`: the elements with a `data-testid`
React took out (−) and put in (+) as it swapped the server's page for its own, net of each other
(«-p#kickoff|+div#kickoff»); tags and test ids only. Empty when the differing element has no
test id.
