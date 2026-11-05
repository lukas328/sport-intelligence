# Raw game videos

`videos.csv` lists public game recordings (YouTube; url;start;end;name), mostly raw amateur and
semi-pro footage from many halls. YouTube refuses downloads from cloud machines ("confirm you are
not a bot"), so `download_segments.ps1` runs on a home computer: five 3-minute pieces per game at
720p plus the info JSON (title, description, which often lists goals with timestamps), about
100 to 150 MB per game. Put the result into the shared Google Drive folder; the training pipeline
picks it up from there (segments for self-training, info JSON for goal lists).

Behind a VPN or company network YouTube answers with the bot check as well: use a phone hotspot
(`videos_priority.csv`, 71 games from many countries and halls, `-Pieces 2`, about 5 GB) or
`-Browser chrome|edge|firefox` to use the signed-in YouTube session (slow, with pauses).

`videos_next.csv` (60 games) is the list to download next: every Swiss game from season
2023/24 on that has a full official game log and is not ingested yet, most goals first. Only
these give free labels for goals, shots and (from 2023/24) shirt numbers.

## Official data per game
`match_official.py` finds the handball.ch game for each name (description link first, else date
window and fuzzy team names over the public match centre API, cached) and writes the game log and
player stats to `official/<name>.json`; `catalog.json` lists every game with its match state,
video properties from the ingest and the Kaggle batch holding its segments. Run it with the
ingest's Python (needs gdown for the info JSONs on Drive); re-running is cheap and picks up new
uploads. First run: 138 of 178 Swiss games matched, 63 with a full game log (3,445 goals; logs
exist from season 2023/24), the rest ambiguous (approximate dates), not on handball.ch (European
cup, friendlies abroad, regional selections) or without team names.
