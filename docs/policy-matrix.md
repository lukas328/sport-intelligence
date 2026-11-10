# Permission matrix

Generated from `handball_api/services/policies.py` (`make policy-doc`). Do not edit.
Enforced server-side; verified by `apps/api/tests/test_policy_matrix.py`.

| Action | org_admin | coach | analyst | player | goalkeeper | guest | goalkeeper_coach | athletic_coach | team_manager | parent |
|---|---|---|---|---|---|---|---|---|---|---|
| `org.read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `org.update` | ✓ |  |  |  |  |  |  |  |  |  |
| `org.members.read` | ✓ |  |  |  |  |  |  |  |  |  |
| `team.create` | ✓ |  |  |  |  |  |  |  |  |  |
| `team.delete` | ✓ |  |  |  |  |  |  |  |  |  |
| `invite.org` | ✓ |  |  |  |  |  |  |  |  |  |
| `audit.read` | ✓ |  |  |  |  |  |  |  |  |  |
| `org.access.manage` | ✓ |  |  |  |  |  |  |  |  |  |
| `team.read` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `roster.read` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `team.members.read` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `season.write` | ✓ | ✓ | ✓ |  |  |  |  |  | ✓ |  |
| `team.update` | ✓ | ✓ |  |  |  |  |  |  |  |  |
| `roster.write` | ✓ | ✓ |  |  |  |  |  |  | ✓ |  |
| `player_status.manage` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `consent.read` | ✓ | ✓ |  |  |  |  |  |  | ✓ |  |
| `consent.write` | ✓ | ✓ |  |  |  |  |  |  | ✓ |  |
| `consent.overview` | ✓ | ✓ | ✓ |  |  |  |  |  | ✓ |  |
| `team.members.manage` | ✓ | ✓ |  |  |  |  |  |  |  |  |
| `invite.team` | ✓ | ✓ |  |  |  |  |  |  | ✓ |  |
| `match.read` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `match.write` | ✓ | ✓ | ✓ |  |  |  |  |  | ✓ |  |
| `video.upload` | ✓ | ✓ | ✓ |  |  |  |  |  | ✓ |  |
| `clip.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ |  |  |
| `playlist.read_all` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ |  |  |
| `playlist.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ |  |  |
| `comment.write` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `comment.moderate` | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| `annotation.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ |  |  |
| `event.write` | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| `play.read_all` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ |  |  |
| `play.write` | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| `assignment.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ |  |  |
| `assistant.use` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ |  |  |
| `training.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `player_line.read_all` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `official.manage` | ✓ | ✓ |  |  |  |  |  |  | ✓ |  |
| `join_requests.manage` | ✓ | ✓ |  |  |  |  |  |  | ✓ |  |

- Team actions apply to the teams where the user has that role; org admins act in every team.
- Org admins need two-factor sign-in for org-level write actions after the grace period (`HB_ORG_ADMIN_2FA_GRACE_DAYS`, default 14).
- Guests get access only through share links (M8).
- Parents (`parent`) get no team access: they see their own children only (guardianships, `/me/consents`) and manage their consents per purpose.
- Players decide their own consents (`/me/consents`); minors need a parent or guardian.
- Youth teams (addendum 01, 4.9): share links only for plays, no consent for public purposes (public highlights, public profile), season player lists unranked.
- Opponent players: number only; a name needs a public source and is never public.
- Training slots and own drills: `training.write` in the team. A drill shared in the club is read by the readers of every team and changed only by the team that made it.
- Club admin handover: `PATCH /orgs/{id}/members/{user}`; the last admin cannot step down.
