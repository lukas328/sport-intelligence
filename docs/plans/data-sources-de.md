# Official game data for Germany (and Austria): sources

As of 2026-11-05. Research for `federation-onboarding.md` (open question 3): where we can legitimately get
clubs, teams, schedules, rosters and game logs for German games, from Bundesliga down to Kreisliga and
youth. Rule: no work-arounds for bot protection (no user-agent spoofing, no headless browser, no scraping
against terms). Every "reachable" below is one plain `curl` request from the cloud session through the
configured proxy; blocked hosts were not retried.

## The landscape changed this season

- **Handball360** is the DHB's new unified admin system (match operations, player passes, licences),
  decided at the DHB Bundestag in November 2025 and run for the DHB by TOOOLS S.L. on the iSquad platform
  ([DHB: Über Handball360](https://dhb.de/handball360/ueber-handball360),
  [Impressum Handball360](https://dhb.de/impressum-handball360),
  [Bundestag notice](https://www.bwhv.org/fileadmin/user_upload/Amtliche_Bekanntmachung_Bundestag_vom_16.11.2025.pdf)).
  Nine of the 17 Landesverbände postponed the switch by up to a year
  ([Volksstimme](https://www.volksstimme.de/sport/handball/riss-durch-deutschland-handball360-spaltet-die-basis-4311461),
  [Tagesspiegel](https://www.tagesspiegel.de/article16002375.ece)). First games with the electronic
  report were in the Regionalliga Südwest on 22/23 Aug 2026
  ([DHB news](https://www.dhb.de/news/handball360-premiere-geglueckt-saisonauftakt-erfolgreich)).
- **handball.net** (DHB) is the single public portal for every league in Germany. It was relaunched in
  August 2026 for Handball360. The DHB says the club widgets are suspended for now and will come back
  "zeitnah", that schedules can be added to a calendar, and that minors show by name only
  ([DHB: relaunch](https://www.dhb.de/news/handball-net-relaunch-2026-neue-funktionen-handball360),
  [DHB: missing schedules](https://www.dhb.de/warum-aktuell-noch-nicht-alle-spielplaene-auf-handballnet-zu-finden-sind)).
- **Handball4all (H4a)** no longer publishes German leagues itself. Its portal links each association to
  handball.net ([H4a portal](https://www.handball4all.de/home/portal)). In Westfalen, handball.net replaced
  the H4a browser on 1 Jan 2025
  ([HV Westfalen PDF](https://handballwestfalen.de/fileadmin/user_upload/2025_02_Handball_Spielplansuche.pdf)).
- **nuLiga** (nu Datenautomaten GmbH) is still the live system for the associations that postponed the
  switch. Public pages with a 2026/27 season exist for BHV (Bayern), HHV (Hessen), HVNB
  (Niedersachsen-Bremen), HVS (Sachsen), HVSA (Sachsen-Anhalt), THV (Thüringen), HVMV
  (Mecklenburg-Vorpommern, including the Regionalliga Ostsee-Spree) and MHV (Mitteldeutsche Oberliga).
- **SIS-Handball** is no longer developed. Westfalen moved to H4a's Phoenix II in 2014
  ([HV Westfalen newsletter](https://www.handballwestfalen.de/fileadmin/user_upload/NEWSLETTER_HVW.pdf)).
  It is not a source.

## Sources

| Source | Coverage | Data | Access and terms | Format | Reachable from here |
|---|---|---|---|---|---|
| [handball.net](https://www.handball.net) (DHB) | All of Germany: HBL, HBF, 3. Liga, JBLH, every association down to Kreisliga and youth | Clubs, teams, leagues, schedules, halls, results, tables, line-ups, live ticker, player statistics; logs for games with the electronic report | No public API documentation. Community reports describe a JSON API under `/api` with access "only on request". robots.txt: `Content-Signal: search=yes, ai-train=no, use=reference`, with ClaudeBot, GPTBot and others disallowed. Terms page (`/nutzungsbedingungen`) could not be read | HTML app, internal JSON, calendar export | **Blocked**: Cloudflare 403 for a plain `curl` request. Not retried |
| Handball360 ([handball360.net](https://www.handball360.net)) | Associations that switched in 2026/27 | Source system behind handball.net: rosters, electronic report, passes | Logins for clubs, coaches, referees and officials only. No public data. DHB is the data controller and TOOOLS S.L. is its processor | n/a | Info site 200, nothing public to read |
| nuLiga public pages, e.g. [BHV](https://bhv-handball.liga.nu/), [HHV](https://hhv-handball.liga.nu/), [HVNB](https://hvnb-handball.liga.nu/), [HVS](https://hvs-handball.liga.nu/), [HVSA](https://hvsa-handball.liga.nu/), [THV](https://thv-handball.liga.nu/), [HVMV](https://hvmv-handball.liga.nu/), [MHV](https://mhv-handball.liga.nu/) | Those associations: Regionalliga and Oberliga down to Bezirks- and Kreisliga, all youth age groups (BHV 2026/27 alone lists 134 groups) | League tree, group tables, schedules (date, time, hall, game number, result), team pages, club and hall directories, per-group player statistics (goals, 7 m, suspensions, cards). Per game, `groupMeetingReport` has both rosters with shirt number, name, goals, 7 m, cards and suspension times, plus time-outs, officials and a full log ("Spielverlauf": time, score, event, shirt number, name). A `meetingReportHB` PDF is linked | Public, no login. robots.txt disallows only `*.inc` and `*.csi`. No usage terms found (the legal notice page returned empty). Contains names of minors. A systematic copy of the database would touch database rights (§ 87b UrhG), so bulk use needs permission | HTML (WebObjects), PDF | **Yes** (200) |
| nuLiga REST API "nuPortalRS" ([DE docs](https://hbde-portal.liga.nu/rs/documentation/), AT: `hbat-portal.liga.nu/rs`) | Same associations as the nuLiga pages; AT: all of Austria | Documented resources: federations, seasons, championships, groups, tables, group and club meetings, clubs, club teams, meetings, meeting events, meeting players, line-ups | OAuth access token (client ID and secret per portal, scopes). Clubs use credentials from their association, e.g. [ContaoBayern/contao-nuligadata-bundle](https://github.com/ContaoBayern/contao-nuligadata-bundle) for BHV | JSON/XML, WADL, client libraries (Java, PHP, Ruby) | Docs 200. API 401 without a token, as expected |
| H4a legacy JSON (`spo.handball4all.de/service/if_g_json.php`, used by the [H4a portal](https://www.handball4all.de/home/portal)) | In practice almost nothing for 2026/27. Württemberg returns no leagues for 2025/26 or 2026/27, and other BW orgs return "permission denied". Only Vorarlberg (AT) still lists a cup | League lists, schedules, halls, iCal per game (commands `po`, `ps`, `pcu`, `pgy`, `gi`, `ical`) | Undocumented and meant for the portal app. robots.txt disallows `/misc/`, which includes the SBO report PDFs (`sboPublicReports.php`). Calendar subscriptions have been down since 29 Sep 2026 ([H4a news](https://www.handball4all.de/home/aktuell/detail/news/kalender-abo-derzeit-nicht-verfuegbar)) | JSON | Yes (200) |
| DHB press reports ([dhbdata.fmp.sportradar.com](https://dhbdata.fmp.sportradar.com/match/83388/pressReport.pdf)), already used in `services/official_report.py` | DHB-run competitions: 3. Liga and Jugendbundesliga (tested JBLH mA 25/26 game 84679) | Rosters with shirt numbers, goals, 7 m, warnings, suspensions, disqualifications, time-outs, goal sequence with match time, hall, referees | Public PDF by numeric ID. The portal root redirects to `/login`. robots.txt `Allow: /`. No terms stated. Game IDs appear in handball.net URLs (`sportradar.dhbdata.<id>`), and dhb.de links schedules to handball.net, so IDs must come from a link the coach pastes | PDF (`pdftotext`) | **Yes** (200, PDF) |
| Sportradar licensed data | HBL, HBF, DHB competitions, HLA; long-term Sportradar deals with HBL, DHB, HBF and HLA were reported in 2020 ([1](https://intergameonline.com/igaming/news/german-handball-deal-for-sportradar), [2](https://www.intergameonline.com/igaming/dkb-handball-bundesliga-and-sportradar-renew-partnership)) | Full schedules, line-ups, play-by-play, live data | Commercial contract | API/feeds | Not tested (no public endpoint) |
| Exports the coach provides | Any league on handball.net or nuLiga | Schedule as ICS (handball.net calendar export), report PDFs or links | The coach's own download, the same as the existing `ics` adapter and report-by-link import | ICS, PDF | n/a (no server fetch from handball.net) |

### Austria (ÖHB)

| Source | Coverage | Data | Access | Reachable |
|---|---|---|---|---|
| [ÖHB nuLiga](https://oehb-handball.liga.nu/cgi-bin/WebObjects/nuLigaHBAT.woa/wa/home) (one championship "Handball Austria 2026/27" for all of Austria since 2016/17; the provincial associations were separate before) and the competition pages on [oehb.at](https://www.oehb.at/de/bewerbe/maennerbewerbe) | HLA Meisterliga and Challenge, cups, youth championships (ÖMS), provincial leagues | Same as German nuLiga. oehb.at links the `meetingReportHB` PDF for each game (tested: HLA game 92478, roster, officials, result, log) and the nuScoreLive ticker (`hbat-live.liga.nu`) | Public pages and PDFs. robots.txt disallows only `*.inc` and `*.csi`. API through nuPortalRS (`hbat-portal.liga.nu/rs`, token) | **Yes** (200) |
| HLA press reports on Sportradar (`infographics.sportradar.com/hla/pageSnapshot/pdf/de/<id>`) | HLA | Match report PDF | Public PDF by ID; Sportradar is the HLA data partner | Yes (200, PDF) |
| Vorarlberg on H4a | VHV cups | See the H4a row above | Legacy | Yes |

## Recommendation

1. **Now, without a contract (per game, user-triggered):** extend the report-by-link import
   (`services/official_report.py`) to nuLiga links: `groupMeetingReport` HTML and `meetingReportHB` PDF on
   `*-handball.liga.nu` (DE) and `oehb-handball.liga.nu` (AT). They carry every goal with time, shirt number
   and scorer, plus 7 m and suspensions. Together with the dhbdata PDFs (3. Liga, JBLH), the HLA Sportradar
   PDFs and the handball.ch matchcentre, this covers report import for every level where the coach can find
   the link. Fetch only on request, one game at a time, with a fixed host list as today. Do not crawl.
   Done 2026-11-05 (providers `nuliga` and `hla`, see `docs/integrations.md`). The HLA Sportradar PDF
   turned out to have no timed log of the goals (only result, half-time, missed 7 m with time and
   player totals), so for HLA games the ÖHB nuLiga report is the better link.
2. **Schedule prefill in DE, without a contract:** have the coach import the team's calendar exported from
   handball.net (existing `ics` adapter) instead of fetching it from our servers. In nuLiga associations the
   coach can instead paste the nuLiga group link, read once on request under the same rules as point 1.
   No automatic club and team search in DE yet.
3. **Team search and daily sync for the nuLiga associations (BHV, HHV, HVNB, HVS, HVSA, THV, HVMV, MHV,
   and ÖHB):** ask for nuPortalRS API credentials. This is the cleanest technical route (documented JSON,
   tokens, clubs, teams, meetings, events). It is temporary for the German associations, which will move
   to Handball360 by 2027/28 at the latest.
4. **Long-term for all of Germany:** a data agreement with the DHB for the handball.net / Handball360 data
   (clubs, teams, schedules, line-ups with numbers, game events). There is no public alternative, and the
   handball.net API is "on request" only. Sportradar only makes sense for HBL and HBF and is a commercial
   licence; for 3. Liga and JBLH the public dhbdata PDFs are enough for now.
5. **Do not use:** handball.net automatically (Cloudflare, robots content signals); H4a `/misc/`
   (robots) and the H4a legacy JSON (undocumented, empty for 2026/27); SIS.

### Next steps (emails)

- **DHB** (kontakt@dhb.de, "Technik: Leiter Digitales Marketing" per the [DHB imprint](https://www.dhb.de/impressum);
  handball.net and Handball360 belong to the DHB): ask for read access to the handball.net / Handball360 data
  for a coaching product (clubs, teams per season and league, schedules with halls, results, line-ups with
  shirt numbers, game events), with the terms and fees, how minors' data must be handled (we show names only
  to the team's coach until consent, no public player profiles), and whether the club widgets or the
  calendar feed may be fetched by a server once they are back. Mention the Swiss model (handball.ch) and that
  we link back to handball.net.
- **BHV first, then HHV and HVNB** (largest nuLiga associations; contact via their nuLiga "Kontakt" page or
  association office): ask for nuPortalRS client credentials (client ID and secret) with read scopes for
  championships, groups, meetings, meeting events and club teams, and whether per-game reading of the
  public report pages is acceptable in the meantime. Ask whether nu Datenautomaten must sign off, since the
  credentials are issued per portal.
- **ÖHB** (contact via [oehb.at](https://www.oehb.at/de)): the same request for `hbat-portal.liga.nu`.
- **Handball4all AG** (email@handball4all.de, Stuttgart): no request needed for Germany. Ask only if
  Vorarlberg footage matters.
- **Sportradar:** only if HBL or HBF clubs become customers; ask for a quote on schedules, line-ups and
  play-by-play for HBL, HBF, 3. Liga and JBLH.

## Notes

- The WebFetch tool could not resolve most hosts in this environment, so all checks above were single `curl`
  requests through the proxy (2026-11-05). For handball.net, one earlier request with a descriptive
  (non-browser) user agent returned 200 HTML that was not inspected. The plain `curl` request got the
  Cloudflare 403, and the host was then treated as blocked.
- Responses were not stored in the repo, apart from the test fixtures of the report import
  (`apps/api/tests/fixtures/official_report/`: nuLiga BHV game 8390512, ÖHB games 81811 and 92532,
  HLA 70984286), with every person's name replaced by a fake one. Sample IDs used: nuLiga BHV group 495716 and game 8390512, dhbdata
  83388 and 84679, ÖHB game 92478, HLA 70984286.
