# Product analytics (addendum 01, 4.12)

PostHog EU cloud (or self-hosted), loaded only after consent in the banner; without
`NEXT_PUBLIC_POSTHOG_KEY` nothing is loaded and no banner appears. No autocapture, no session
recording, IP not stored. Events carry no names and no video data.

| Event | When |
|---|---|
| `signed_up` | registration succeeded (`invited` true/false) |
| `first_upload` | an upload completed (`role`) |
| `analysis_viewed` | a match with a finished analysis was opened |
| `presentation_held` | the presenter was opened |
| `player_active` | a player opened "Deine Szenen" (once per match and session) |
| `$pageview` | page views |

## Dashboard "Aktivierung und Bindung" (create in PostHog)
1. Funnel (14 days): `signed_up` → `first_upload` → `analysis_viewed` → `presentation_held`.
2. Retention: first event `analysis_viewed`, returning event `analysis_viewed`, weekly, 8 weeks.
3. Trend: weekly unique users with `player_active` (players reached).
4. Trend: `presentation_held` per week (video sessions held).
