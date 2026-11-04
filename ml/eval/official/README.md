# Official game data for the test videos

Ground truth without labelling: what the federations and clubs publish about the games on Drive.

| Video (Drive) | Result | Data here | Source |
|---|---|---|---|
| CH_SPL2_HSGLeimental_HCArbon_2024 | 28:25 for Arbon | full game log (148 entries: every goal, shot, save, technical error, suspension with match time, shirt number, name) and player stats | handball.ch game 484345 (`fetch_handball_ch.py`) |
| CH_1Liga_HSGLeimental_SCFrauenfeld_2023 | | player stats (goals per player, no shirt numbers, no log) | handball.ch game 448515 |
| DE_Regionalliga_HBMuelheimUrmitz_SuedpfalzTiger_2026 | 39:24 | all 63 goals **with video timestamps**, scorer, penalties, 3 disallowed goals, a missed penalty, half boundaries; rosters with shirt numbers in `description` | video description (club channel) |
| DE_3Liga_HSGKonstanz_WoelfeWuerzburg_2023 | 37:34 | official DHB game log (89 events: every goal, 7-metre, suspension, time-out with match time, shirt number, name) | DHB press report 77228 (`fetch_dhb_report.py`) |
| DE_3Liga_SCMagdeburg2_EmporRostock_2024 | 26:26 | official DHB game log (65 events) | DHB press report 76839 |
| DE_3Liga_HSGKrefeld_TVKorschenbroich_2025 | 37:26 | official DHB game log (81 events) | DHB press report 83388 |
| CH_NLB_SGHorgen_LakersStaefa_2017 | 32:37 (17:22) | result only | video description |
| CH_NLB_SGHorgen_TVMoehlin_2017 | 31:30 | result only | video description |
| CH_RegioCup_TVUznach_HCDietikonUrdorf_2017 | 29:25 after extra time | result only | video description |

Checked so far: the five goals of the 5-minute Leimental clip (match clock 02:00 to 07:00) read
from the score overlay match the official log, scorers included (ADR 026).

German games: handball.net blocks automated access (Cloudflare 403); the DHB press reports on
dhbdata.fmp.sportradar.com cover the 3. Liga (not found there: the Regionalliga games in Cottbus and
Eisenach 2019). Mülheim's goal list comes from the video description.
