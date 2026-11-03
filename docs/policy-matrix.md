# Permission matrix

Generated from `handball_api/services/policies.py` (`make policy-doc`). Do not edit.
Enforced server-side; verified by `apps/api/tests/test_policy_matrix.py`.

| Action | org_admin | coach | analyst | player | goalkeeper | guest |
|---|---|---|---|---|---|---|
| `org.read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `org.update` | ✓ |  |  |  |  |  |
| `org.members.read` | ✓ |  |  |  |  |  |
| `team.create` | ✓ |  |  |  |  |  |
| `team.delete` | ✓ |  |  |  |  |  |
| `invite.org` | ✓ |  |  |  |  |  |
| `audit.read` | ✓ |  |  |  |  |  |
| `team.read` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `roster.read` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `team.members.read` | ✓ | ✓ | ✓ |  |  |  |
| `season.write` | ✓ | ✓ | ✓ |  |  |  |
| `team.update` | ✓ | ✓ |  |  |  |  |
| `roster.write` | ✓ | ✓ |  |  |  |  |
| `consent.read` | ✓ | ✓ |  |  |  |  |
| `consent.write` | ✓ | ✓ |  |  |  |  |
| `team.members.manage` | ✓ | ✓ |  |  |  |  |
| `invite.team` | ✓ | ✓ |  |  |  |  |
| `match.read` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `match.write` | ✓ | ✓ | ✓ |  |  |  |
| `video.upload` | ✓ | ✓ | ✓ |  |  |  |
| `clip.write` | ✓ | ✓ | ✓ |  |  |  |
| `playlist.read_all` | ✓ | ✓ | ✓ |  |  |  |
| `playlist.write` | ✓ | ✓ | ✓ |  |  |  |
| `comment.write` | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| `comment.moderate` | ✓ | ✓ | ✓ |  |  |  |
| `annotation.write` | ✓ | ✓ | ✓ |  |  |  |
| `event.write` | ✓ | ✓ | ✓ |  |  |  |
| `play.read_all` | ✓ | ✓ | ✓ |  |  |  |
| `play.write` | ✓ | ✓ | ✓ |  |  |  |

- Team actions apply to the teams where the user has that role; org admins act in every team.
- Org admins need two-factor sign-in for org-level write actions after the grace period (`HB_ORG_ADMIN_2FA_GRACE_DAYS`, default 14).
- Guests get access only through share links (M8).
