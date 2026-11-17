# Permission matrix

Generated from `handball_api/services/policies.py` (`make policy-doc`). Do not edit.
Enforced server-side; verified by `apps/api/tests/test_policy_matrix.py`.

The product shows four roles (K18): **Trainer** (coach and club admin), **Co-Trainer** (coach rights in the team, no club or subscription), **Spieler**, **Eltern**. The stored roles stay; the second header row says which of the four each one is.

| Action | org_admin | coach | analyst | player | goalkeeper | guest | goalkeeper_coach | athletic_coach | team_manager | parent |
|---|---|---|---|---|---|---|---|---|---|---|
| *shown as* | Trainer | Co-Trainer | Co-Trainer | Spieler | Spieler | Gast (Links) | Co-Trainer | Co-Trainer | Co-Trainer | Eltern |
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
| `match.read` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `playlist.read_all` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `play.read_all` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `player_line.read_all` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `match.write` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `video.upload` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `clip.write` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `annotation.write` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `comment.write` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `event.write` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `playlist.write` | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |  |
| `team.members.read` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `team.members.manage` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `invite.team` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `join_requests.manage` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `team.update` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `season.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `roster.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `player_status.manage` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `consent.read` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `consent.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `consent.overview` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `official.manage` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `match.delete` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `comment.moderate` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `play.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `assignment.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `assistant.use` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |
| `training.write` | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |  |

- Team actions apply to the teams where the user has that role; org admins act in every team.
- A Trainer is stored as `coach` with the organisation role `org_admin`; inviting a Trainer needs `invite.org`. A `coach` without it is a Co-Trainer.
- `analyst`, `team_manager`, `goalkeeper_coach` and `athletic_coach` are older roles with the same rights as `coach`; the product shows them as Co-Trainer.
- Players (`player`, `goalkeeper`) see everything of the team, mark scenes, build collections and share them by link, comment, answer the analysis' questions and upload videos. They do not delete matches or videos, invite people, change the squad, the team, the club or the subscription, and revoke only share links they made.
- Org admins need two-factor sign-in for org-level write actions after the grace period (`HB_ORG_ADMIN_2FA_GRACE_DAYS`, default 14).
- Guests get access only through share links (M8).
- Parents (`parent`) get no team access: they see their own children only (guardianships, `/me/consents`) and manage their consents per purpose.
- Players decide their own consents (`/me/consents`); minors need a parent or guardian.
- Youth teams (addendum 01, 4.9): share links only for plays, no consent for public purposes (public highlights, public profile), season player lists unranked.
- Public highlights need the public highlights consent of every featured player.
- Opponent players: number only; a name needs a public source and is never public.
- Training slots and own drills: `training.write` in the team. A drill shared in the club is read by the readers of every team and changed only by the team that made it.
- Club admin handover: `PATCH /orgs/{id}/members/{user}`; the last admin cannot step down.
