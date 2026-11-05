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

## Segment library: clock for the batches from the owner's computer
`local_ingest.py` uploads `handball-segs-lNN` without clock data. `library.py` lists the account's
`handball-segs-*` datasets on Kaggle and, for each one not yet done, downloads index.json and the
info JSONs, then one segment at a time, reads the match clock (`segment_clock.py`, as the ingest
does) and deletes the segment. Segments the cloud ingest already read (bNN) are not downloaded.
Results go to `<scratch>/library/library.json` (per game as in the ingest state.json, plus
`kaggle_dataset`); resumable after every segment, `--watch 900` polls for new datasets. File
names that differ from a `videos*.csv` name only in case, punctuation or a `.fNNN` suffix are
mapped to that name. `segment_clock.py --labels` and `match_official.py` (catalog: `video.source`
`local`, `kaggle_dataset` `handball-segs-lNN`) read the ingest state and the library together.

Started as a detached background process (also in `<scratch>/library/run.sh`, to restart it after
a container restart; stop with `pkill -g $(pgrep -f 'ml/data/library.py --watch')`):

    S=/tmp/claude-0/-home-user/3dc450e2-2499-5e21-b252-1c4e366c6b5a/scratchpad
    export KAGGLE_USERNAME=lukasde1000 KAGGLE_KEY=injected-by-proxy KAGGLE_CONFIG_DIR=$S/kg REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt
    export PATH=$S/torchenv/.venv/bin:$PATH
    cd /home/user/handball-ai
    setsid nohup nice -n 10 $S/torchenv/.venv/bin/python -I ml/data/library.py --watch 900 > $S/library/library.log 2>&1 < /dev/null &

Offline test of the whole path: `--local-dir DIR` reads `DIR/handball-segs-*/` folders laid out
like a dataset (index.json, segments, info JSONs) instead of Kaggle; use another `--libdir`.
