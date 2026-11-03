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
