# Runbooks

Short, executable procedures. Each names who may run it and how to verify the result.

| Runbook | When |
|---|---|
| [deploy.md](deploy.md) | every release |
| [backup-restore.md](backup-restore.md) | nightly backups, monthly restore test, real restore |
| [incident.md](incident.md) | outage, data leak suspicion, failed jobs piling up |
| [support.md](support.md) | reprocess a match, lost 2FA device, extend a trial, data subject requests |
| [secrets.md](secrets.md) | rotate keys and tokens |
| [local-stack-without-docker.md](local-stack-without-docker.md) | `make up` cannot pull images (cloud sessions): start web and API against demo data from host services |
