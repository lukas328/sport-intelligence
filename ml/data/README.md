# Raw game videos

`videos.csv` lists public game recordings (YouTube; url;start;end;name), mostly raw amateur and
semi-pro footage from many halls. YouTube refuses downloads from cloud machines ("confirm you are
not a bot"), so `download_segments.ps1` runs on a home computer: five 3-minute pieces per game at
720p plus the info JSON (title, description, which often lists goals with timestamps), about
100 to 150 MB per game. Put the result into the shared Google Drive folder; the training pipeline
picks it up from there (segments for self-training, info JSON for goal lists).
