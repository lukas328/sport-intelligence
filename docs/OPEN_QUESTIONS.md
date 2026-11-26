# Open questions

Reviewed against `main` on 2026-11-16. Every question carries one status:
**Answered** (date, answer, where it lives), **Superseded** (why), **Open (Lukas)** (owner decision,
with a recommendation and what the code does until then) or **Open (recognition / test)** (not
built or not measured yet; status and next step). History is in git.

## Was nur Lukas entscheiden kann

Stand 2026-11-16. 🔴 vor dem ersten echten Verein, 🟡 vor dem Pilot, ⚪ später. «Ohne Entscheid» sagt,
was der Code heute tut.

1. 🔴 **Firma, MWST und Bankkonto** (Q-PROD-3, Q-ADD-3). Unter welcher Firma (GmbH oder
   Einzelfirma) läuft das Produkt, und ist sie mehrwertsteuerpflichtig? Empfehlung: Firma vor dem
   ersten Verein, MWST mit einer Treuhand klären, nur CHF. Ohne Entscheid: Impressum «Angaben
   folgen», Rechnungen mit dem Platzhalter «Handball AI GmbH» und Beispiel-IBAN, Bezahlung aus.
2. 🔴 **Rechtstexte und Folgenabschätzung** (Q-LEGAL-1, Q-ADD-5). Wer prüft AGB, Datenschutz,
   Impressum, Hallenhinweis und Einwilligungstexte und erstellt die Datenschutz-Folgenabschätzung
   (Videos von Minderjährigen)? Empfehlung: eine Fachperson für Datenschutzrecht in einem Auftrag,
   inklusive der Frist «Originalvideos 90 Tage». Ohne Entscheid: Entwürfe mit «noch nicht rechtlich
   geprüft», `LAUNCHED` bleibt false.
3. 🔴 **Einwilligung bei Jugendteams** (Q-LEGAL-2, Q-UX-10, Q-ADD-7). Darf über den
   Einwilligungs-Link eines Teams jede erwachsene Spielerin und jeder Elternteil für jede Person im
   Team antworten, und gilt die Einwilligung der Eltern nach dem 18. Geburtstag weiter? Empfehlung:
   so lassen und von der Fachperson aus Punkt 2 bestätigen lassen. Ohne Entscheid: ein Link pro
   Team, 90 Tage gültig, mit Protokoll; Eltern-Einwilligungen gelten, bis die volljährige Person
   sie ändert.
4. 🔴 **Auftragsverarbeitung** (Q-INFRA-1, Q-SITE-4). Akzeptierst du die AVVs von Microsoft (Azure)
   und Cloudflare (R2) in den Konten? Empfehlung: ja, beim Anlegen der Konten, danach beide in der
   Datenschutzerklärung nennen. Ohne Entscheid: kein echtes Vereinsvideo in die Produktion.
4a. 🔴 **Ball-Netze und DeepSport-Lizenz** (Auslieferung). Alle Ball-Netze ab Runde 3, auch hr1 und
   hrp1 (heute im Produkt hinter dem Schalter Ball v2), sind mit DeepSport-Bildern trainiert
   (CC BY-NC-SA 4.0, nur nicht-kommerziell). Kommerziell auslieferbar ist erst ein Netz ohne diese
   Daten. Läuft: `handball-ml-hr-nods` (hr1 ohne DeepSport, Kaggle, 25.11.), danach Messung gegen hr1
   auf Ball-Testset 2. Bei hrp1 zusätzlich die Lizenz der ImageNet-Gewichte (timm `hrnet_w18`)
   prüfen. Empfehlung: vor dem ersten zahlenden Verein nur Netze ohne DeepSport ausliefern; bis dahin
   Ball v2 nur im Test. Ohne Entscheid: Ball v2 bleibt Testbetrieb (`handball_vision.ballnet`,
   Lizenzhinweis).
5. 🟡 **Wem gehört ein Team** (Q-AUTH-OWNER). Wie wird geprüft, dass wer ein Team im Einstieg
   speichert, wirklich dazugehört? Empfehlung: im Pilot (a) Übergabe durch den Support, weil die
   Pilotvereine bekannt sind; (b) Bestätigung über die Verbandsadresse erst vor dem breiten Start.
   Ohne Entscheid: wer zuerst speichert, wird Administrator; bei einem bestehenden Team gibt es
   eine Zugangsanfrage und einen Mail-Link an den Support.
6. 🟡 **Probezeit** (Q-BILL-TRIAL). Bekommt jeder neue Verein bei der Registrierung 30 Tage alles
   gratis, ohne Karte? Empfehlung: ja, so lassen, mit dem Satz «30 Tage alles gratis. Danach
   entscheidest du.» Ohne Entscheid: Bezahlung ist aus (`billing_enforce` false), also alles gratis;
   sobald sie an ist, startet die Probezeit bei der Registrierung (`trial_on_signup`).
7. 🟡 **Preise und Gratis-Plan** (Q-PROD-4). Bleiben CHF 0 / 39 / 199 (Jahr = 10 Monate), und
   bleibt «Gratis» ohne automatische Analyse ein Plan? Empfehlung: Pilot gratis, Preise vor dem
   ersten Geld festlegen, dann `PRICES_FINAL = true`. Ohne Entscheid: Platzhalter mit «noch nicht
   endgültig».
8. 🟡 **Daten von handball.ch** (Q-DATA-5). Holst du beim Schweizerischen Handball-Verband eine
   Erlaubnis oder Partnerschaft für die öffentliche, aber nicht dokumentierte Schnittstelle ein?
   Empfehlung: ja, vor dem Pilot schriftlich anfragen. Ohne Entscheid: Spiele, Kader und Tabelle
   kommen aus den öffentlichen Daten (zwischengespeichert, täglich abgeglichen).
9. 🟡 **Vereinsvideos fürs Training der Erkennung** (Q-DATA-4). Dürfen Videos und Antworten der
   Vereine zum Verbessern der Erkennung genutzt werden? Empfehlung: im Pilot nicht; später eine
   eigene, freiwillige Einwilligung pro Verein, ausgeschaltet als Vorgabe. Ohne Entscheid: nichts
   wird dafür genutzt; die Einwilligungsart `training_data` gibt es, sie ist nicht in Gebrauch.
10. ⚪ **Bereiche aus der früheren Version** (Q-OLD-AREAS). Spielzüge, Gegnerprofil, «Zum Zeigen»
    und alte Playlists neu bauen, in Sammlungen aufgehen lassen oder mit Export abschalten?
    Empfehlung: im Pilot so lassen und schauen, ob ein Verein sie braucht; Ungenutztes danach mit
    Export abschalten. Ohne Entscheid: erreichbar, mit dem Hinweis «aus der früheren Version».
11. ⚪ **Marke und App-Kennungen** (Q-PROD-1, Q-M11-3). Lässt du «Handball Intelligence» prüfen
    (Swissreg, EUIPO, Klassen 9, 41, 42), und sollen die App-Kennungen `ch.handballai.app` an den
    Namen angeglichen werden? Empfehlung: Markenrecherche vor Ausgaben für Werbung, Kennungen vor
    dem ersten Store-Upload angleichen (danach geht es nicht mehr). Ohne Entscheid:
    `ch.handballai.app`, keine Handy-Apps im Pilot.
12. ⚪ **Dienste mit Kosten** (Q-ADD-4, Q-BILL-1, Q-AUTH-1, Q-M10-1, Q-M11-1, GPU in Q-INFRA-1).
    Wann kommen Stripe, Google- und Apple-Anmeldung, ein Anthropic-Key, Support-Chat, Statusseite
    und eine GPU dazu? Empfehlung: zum Pilot keiner; Stripe, bevor du Geld verlangst; GPU, wenn ein
    ganzes Spiel auf CPU zu lange dauert (ein Ausschnitt von 5 Minuten braucht heute rund 20
    Minuten). Ohne Entscheid: alles aus, Analyse auf CPU.
    **GPU teilweise entschieden (Lukas, 2026-11-19):** GPU kommt von Azure, nicht von Modal.
    Weil Switzerland North keine passende GPU hat, zieht dafür wahrscheinlich die ganze Umgebung
    in eine andere Azure-Region um. Das macht Lukas später selbst; bis dahin bleibt alles in der
    Schweiz und die Analyse auf Staging auf der CPU. Kein Modal-Backend bauen.

Nicht entschieden werden muss, aber nur mit dir geht: echte Trainer für den Usability-Test
(Q-UX-1), ein iPhone für den Safari-Test (Q-QA-1), ein ganzes Spiel als Video für die Messung von
Prüfzeit und drei Dingen (Q-REC-SHOTZONE).

## Beantwortet am 2026-11-16

- **Q-PROD-2**: App und Website in de-CH, fr und en; de-DE nicht gebaut.
- **Q-DATA-2**: Import nach eigenem Schema gebaut; echte Spielberichte kommen per Link (handball.ch, DHB, nuLiga, HLA).
- **Q-AUTH-2**: 2FA für Vereinsadmins nach 14 Tagen Schonfrist bleibt.
- **Q-AUTH-2b**: Erinnerung an 2FA erst, wenn es etwas zu schützen gibt, bleibt.
- **Q-AUTH-LINK**: Anmeldelink 24 Stunden gültig, einmalig, bleibt.
- **Q-ROLES-1, Q-ROLES-2, Q-ROLES-3**: so wie gebaut (Kader im Team sichtbar, Einladungsrechte, Saison 1. Juli bis 30. Juni).
- **Q-INFRA-1**: Azure Switzerland North und R2 EU entschieden und im Terraform-Standard; GPU später (Punkt 12).
- **Q-INFRA-2**: Repository `lukas328/sport-intelligence`, GitHub Actions.
- **Q-INFRA-3**: SMTP-Anschluss (ADR 009); Anbieter Azure Communication Services, kein neuer Vertrag.
- **Q-INFRA-5**: Next.js 15.5 bleibt.
- **Q-ML-1, Q-ML-2, Q-ML-5, Q-ML-6**: Das ausgelieferte Analyse-Image enthält nur YOLOX-s und PP-OCRv4 (Apache-2.0); kein ReID- und kein Ballmodell.
- **Q-LEGAL-3**: Originalvideos 90 Tage, danach die komprimierte Fassung (Code und Datenschutz-Entwurf).
- **Q-ADD-1**: Das Produkt ist «Vorschlag und Bestätigung» (Prüfen), Automatik ist kein Startversprechen.
- **Q-ADD-2**: Spieltag bleibt optional unter «Mehr».
- **Q-UX-2**: Archivo kommt mit dem ersten Handy-Build.
- **Q-UX-ADR, Q-UX-MATRIX, Q-UX-3, Q-UX-4, Q-UX-6 bis Q-UX-9, Q-UX-11 bis Q-UX-14, Q-UX-19, Q-UX-20**: Stand der Gestaltung «Anlauf» so wie gebaut; was fehlt, kommt nicht vor dem Pilot.
- **Q-VIDEO-PARTS, Q-PARTS-MARKS, Q-PARTS-OVERLAY, Q-PARTS-ORDER-RERUN**: Teile gebaut und gemergt; die drei Lücken bleiben für den Pilot bewusst.
- **Q-SITE-2, Q-SITE-4, Q-SITE-5, Q-SITE-6**: keine feste Analysedauer; Speicherort stimmt; keine öffentliche Demo in der App; Hilfe-Zuordnung wird nachgeführt.
- **Q-REC-SHOTZONE** (Entscheid): «Von wo?» per Tipp, drei Dinge nur aus getippten Wurforten.

Überholt: Q-ML-3, Q-ADD-6, Q-ADD-8, Q-UX-5, Q-PARTS-RENDITIONS, Q-SITE-1, Q-SITE-7.

---

## Product and business
- **Q-PROD-1 Product name and domain. Open (Lukas): trademark and bundle ids only.** Decided
  2026-11-12/13: **Handball Intelligence**, logo «Taktik» (docs/design/brand2/taktik), domain
  `handball-intelligence.com`, app `app.handball-intelligence.com`, `support@handball-intelligence.com`,
  set in all defaults (`apps/site/src/lib/site.ts`, API config). DNS, mail records and app-link
  files are part of the deployment (docs/site/SEO.md, «Vor dem Livegang»). *Left:* trademark search
  (Swissreg, EUIPO, classes 9, 41, 42); mobile bundle ids `ch.handballai.app` (apps/mobile/app.json);
  the company name is Q-PROD-3. *Recommendation:* search before spending on the brand; align the
  bundle ids before the first store upload.
- **Q-PROD-2 Languages. Answered 2026-11-16.** The app ships de-CH, fr and en
  (`apps/web/messages`), the site and legal drafts de, fr and en. de-DE ("ß") would be another locale;
  not planned.
- **Q-PROD-3 Company entity, VAT and currencies. Open (Lukas).** `packages/plans/plans.json` has CHF
  only. *Recommendation:* found the company before the first club, CHF only, VAT with a fiduciary.
  *Until then:* `invoice_creditor_*` in `core/config.py` holds placeholders («Handball AI GmbH»,
  example IBAN), the imprint says the details follow (`NEXT_PUBLIC_COMPANY_*` empty).
- **Q-PROD-4 Prices and the free plan. Open (Lukas).** CHF 0 / 39 / 199 per month, a year is 10
  monthly fees, goalkeeper add-on CHF 7 (`packages/plans/plans.json`); the site says «Die Preise sind
  noch nicht endgültig» while `PRICES_FINAL` is false. Also open: whether «Gratis» (no automatic
  analysis) stays a plan. *Recommendation:* free pilot, prices before the first payment.

## Data and test material
- **Q-DATA-1 Test videos. Answered.** Never in git; R2 test-data bucket via `scripts/testdata.py`,
  metadata in `ml/eval/golden_set/manifest.json` (`data/README.md`). Real tests so far: two NLB clips
  (docs/ux-test/echttest/BERICHT.md).
- **Q-DATA-2 Paper match reports. Answered 2026-11-16.** Importer built against our assumed schema
  (`services/paper_reports.py`, `docs/schemas/paper-report.schema.json`); real reports come by link
  from handball.ch, DHB, nuLiga and HLA (`services/official_report.py`, docs/integrations.md). A
  club-specific schema is no longer awaited.
- **Q-DATA-3 Golden set annotation. Open (recognition).** No annotation tool or budget chosen. Ground
  truth so far is counted by hand per clip (BERICHT.md). *Next step:* one full match counted by hand
  (goals with time and place), the same match as the Q-REC-SHOTZONE measurement.
- **Q-DATA-4 Customer data for training. Open (Lukas).** *Recommendation:* not in the pilot; later a
  separate opt-in per organisation, off by default. *Until then:* nothing is used; the consent kind
  `training_data` (models/enums.py) exists unused; the terms draft allows it only with explicit
  consent per person (purpose «Verbesserung der Erkennung»), off by default, for minors never without
  the parents.
- **Q-DATA-5 handball.ch. Open (Lukas): permission.** Built since the brief: clubs, teams, schedule,
  roster suggestions, standing and match reports come from handball.ch's public, undocumented
  interface (`services/official.py`, `integrations/handball_ch.py`, cached, daily sync).
  *Recommendation:* ask the SHV in writing for permission or a partnership before the pilot
  (docs/plans/federation-onboarding.md, open question 1).

## Accounts and roles
- **Q-AUTH-1 Google and Apple sign-in. Open (Lukas), later.** Built (ADR 010); needs a Google OAuth
  client and a paid Apple Developer account. Without them the buttons stay hidden.
- **Q-AUTH-2 2FA for org admins. Answered 2026-11-16.** Enforced for org-level write actions after
  14 days (`org_admin_2fa_grace_days`), so onboarding is not blocked.
- **Q-ROLES-1 Players see the roster. Answered 2026-11-16.** As built; statistics follow
  `players_see_team_stats` (default off for youth teams, models/tenancy.py).
- **Q-ROLES-2 Who invites whom. Answered 2026-11-16.** As built: coaches invite to their own team,
  only org admins invite org admins (`services/invitations.py`, `Action.INVITE_ORG`).
- **Q-ROLES-3 Season. Answered 2026-11-16.** 1 July to 30 June (`services/orgs.py`); other cut-offs
  only on request from a club.

## Infrastructure
- **Q-INFRA-1 Hosting. Answered (ADR 002, ADR 025).** Cloudflare R2 (EU) for video; Azure Container
  Apps, Postgres Flexible Server, Redis, Key Vault in Switzerland North (default in
  `infra/terraform/azure/variables.tf`). GPU: CPU worker for the pilot; the real-clip tests took about
  20 minutes for a 5-minute clip on CPU, a whole match is not measured; a GPU is a cost decision
  (Lukas list, item 12). Deployment: GO_LIVE.md, docs/LIVEGANG.md.
- **Q-INFRA-2 GitHub and CI. Answered.** `lukas328/sport-intelligence`, GitHub Actions; deploy
  workflow is being prepared with the infrastructure.
- **Q-INFRA-3 E-mail provider. Answered 2026-11-16.** The code speaks SMTP only (ADR 009,
  `email_backend = "smtp"`); provider: Azure Communication Services Email (Europe, same Azure
  contract, no new account), as proposed in docs/LIVEGANG.md. SPF, DKIM, DMARC with the deployment.
- **Q-INFRA-4 MinIO. Answered.** Local S3 is SeaweedFS (ADR 006).
- **Q-INFRA-5 Next.js version. Answered 2026-11-16.** Stay on 15.5 (web and site on 15.5.28);
  upgrade in its own step after the pilot.

## ML and licences
- **Q-ML-1 Ultralytics licence. Answered.** No; Apache-2.0 detectors (ADR 003).
- **Q-ML-2 Dataset licences. Answered 2026-11-16 for the pilot.** No shipped model is trained on
  these sets; the check in `ml/datasets/LICENSES.md` is needed only before we train our own model on
  them.
- **Q-ML-3 Model and dataset access. Superseded.** The cloud environment now has Kaggle, Roboflow and
  Modal connected; Hugging Face, Zenodo and Google Drive are not checked. The ONNX detector and
  registry path (ADR 012, 025) stays.
- **Q-ML-4 Validation of physical load. Open (recognition), outside the core.** Needs one match with
  a reference system or measured sprints. *Until then:* values carry «geschätzt», no comparison
  across camera positions.
- **Q-ML-5 Re-identification licence. Answered.** Risk accepted by the product owner for the
  feasibility phase (2026-11-04); no image ships `reid.onnx` (ml/models/reid-fastreid.md,
  apps/gpu-worker/Dockerfile ships YOLOX-s and PP-OCRv4 only). Before re-id is shipped: legal
  clearance or our own model.
- **Q-ML-6 Ball data. Answered.** Non-commercial data allowed for feasibility; no ball model ships
  (Q-UX-15). A shipped ball model needs a retraining without them.
- **Q-ML-7 Target footage. Answered.** Raw amateur recordings, rarely an overlay; the overlay reader
  is a bonus.

## Legal and privacy
- **Q-LEGAL-1 Legal review. Open (Lukas).** Drafts: `apps/site/content/legal/{de,fr,en}/`
  (agb, datenschutz, impressum), hall notice `/{locale}/aufnahme/`, consent texts. Missing: legal
  review, data protection impact assessment, records of processing, DPA template for clubs,
  sub-processors by name (Microsoft, Cloudflare). *Recommendation:* one data-protection lawyer for
  all of it before the first real club video.
- **Q-LEGAL-2 Youth consent. Open (Lukas).** Built: the club records consent per player, plus the
  team consent link (Q-UX-10); parent accounts exist (`services/family.py`). *Recommendation:* keep,
  have it confirmed in the Q-LEGAL-1 review.
- **Q-LEGAL-3 Retention. Answered 2026-11-16.** Originals are reduced to the compressed version after
  90 days, admins are told a week before (`raw_video_days`, `services/monitoring.py retention`); the
  privacy draft says the same. Reviewed with Q-LEGAL-1.

## QA
- **Q-QA-1 iPhone/Safari. Open (test).** Playwright WebKit covers the engine, not iOS; playback
  across two files (Q-PARTS-RENDITIONS) is untested on an iPhone. *Decided procedure:* Lukas' own
  iPhone on staging before the pilot (upload, Prüfen with «Von wo?», playback across the break); no
  device cloud.

## Billing
- **Q-BILL-EU5 VAT and terms for clubs in the EU. Open (Lukas, legal advice).** Since Europa step 2
  clubs outside CH and LI pay in EUR (same amount). Their invoices carry no Swiss VAT, only the note
  «Leistung an einen Empfänger im Ausland, ohne Schweizer Mehrwertsteuer». To settle: reverse charge
  for clubs with a VAT id, clubs without one (OSS?), mandatory invoice details, an EU version of the
  terms (§11 Swiss law) and withdrawal. *Until then:* no EU club on a paid plan
  (docs/plans/europa.md, EU5); EUR checkout also needs `HB_STRIPE_PRICE_TEAM_EUR` and
  `HB_STRIPE_PRICE_CLUB_EUR`.
- **Q-BILL-1 Stripe. Open (Lukas), later.** Needs an account, test keys, webhook secret and price ids.
  *Until then:* `billing_enforce` is false, nothing is charged; the settings page says online payment
  is not set up.
- **Q-BILL-TRIAL Trial at sign-up. Open (Lukas): confirm the rule.** Built 2026-11-13: creating a club
  starts the Team plan's 30-day trial without payment details (`services/orgs.py create_org`,
  `trial_on_signup`, default on; `trial_used` prevents a second trial); at the end
  `billing.effective_plan` falls back to Free, nothing is deleted. Test
  `test_billing.py::test_new_club_starts_the_trial_and_its_first_video_is_analysed`. Wording to
  confirm: «30 Tage alles gratis. Danach entscheidest du.»

## Addendum 01
- **Q-ADD-1 Automatic events before launch. Answered 2026-11-16.** The product is built as
  suggest-and-confirm: the analysis proposes goal moments, the coach confirms them in Prüfen (ADR 029,
  Q-UX-20); match reports by link fill the rest. Automatic events are no launch promise.
- **Q-ADD-2 Live tagging. Answered.** Spieltag (match clock, offline queue) stays optional under
  «Mehr»; device-time sync is not planned before the pilot.
- **Q-ADD-3 VAT and invoicing. Open (Lukas)**, together with Q-PROD-3. *Until then:* VAT rate
  configurable (`invoice_vat_registered` false, 8.1 %), QR bill marked «rechtlich prüfen lassen».
- **Q-ADD-4 Extra providers. Open (Lukas), later.** Support chat, status page, PostHog, mail series.
  *Recommendation:* none for the pilot; errors and logs in Azure. *Until then:* adapters set to
  `none`.
- **Q-ADD-5 Legal templates. Open (Lukas)**, part of Q-LEGAL-1. Drafts show «noch nicht rechtlich
  geprüft»; company details follow by build variables.
- **Q-ADD-6 Test material for the addendum. Superseded.** Spotlight, multi-angle, portrait crop and
  the like are outside the core (ADR 029); the core is tested on real clips (BERICHT.md), several
  files in the fifth real-video test.
- **Q-ADD-7 Child turns 18. Open (Lukas)**, part of Q-LEGAL-2. *Until then:* adult players decide
  for themselves and may revoke what a parent gave (`services/family.py`); earlier parent consents
  stay valid until changed.
- **Q-ADD-8 Real footage, network access. Superseded.** Kaggle and Roboflow are connected in the
  environment (Q-ML-3); the real tests use club clips. YouTube is not downloaded (ADR 018).

## Addendum milestones (M10, M11)
- **Q-M10-1 Data assistant key. Open (Lukas), later.** Off without a key (503). Live evaluation:
  `HB_ANTHROPIC_API_KEY=... uv run pytest -m live apps/api/tests/test_assistant.py`.
- **Q-M10-2 Sportscode check. Open (test), outside the core.** Export round-trips through our import;
  ask a club with Sportscode to open one file when one asks for it.
- **Q-M11-1 Paper sheets test set. Open (Lukas), later.** Needs 10 photos with true values and a key;
  off until then, review before import always.
- **Q-M11-2 Device measurements. Open (test), with the native apps.** Cold start and a 70-minute
  recording, measured on the first device build.
- **Q-M11-3 Store accounts and push. Open (Lukas), later.** Apple Developer, Google Play, EAS project,
  APNs, FCM; bundle ids are Q-PROD-1. The web app runs on phones; native apps after the pilot.

## Design and usability
- **Q-UX-1 Usability test with real people. Open (test).** Three rounds were run by test sessions
  (docs/ux-test-status.md), not by real coaches. *Decided procedure:* the first two pilot coaches,
  20 minutes each on their phone: create the team from `/einstieg`, upload a video, answer Prüfen with
  «Von wo?», open the scenes behind a thing.
- **Q-UX-2 Typeface in the Expo app. Answered 2026-11-16.** Archivo via `expo-font` with the first
  device build (Q-M11-3); system font until then.

### Redesign «Anlauf» (ADR 029, ADR 030)
- **Q-UX-ADR ADR number** (was the second Q-UX-1). **Answered:** ADR 029.
- **Q-UX-MATRIX Matrix and data assistant** (was the second Q-UX-2). **Answered 2026-11-16:** both
  live under Szenen: «Als Tabelle» (`?view=table`, old pivot at `matrix?pivot=1`),
  `/assistant?q=` leads to the scene search (ux-test-status B02, B21).
- **Q-UX-3 Video tab tools. Answered 2026-11-16:** setup steps left the Video tab (B10); the tool
  rail (events, defence systems, notes; `work-rail.tsx`) stays for the pilot.
- **Q-UX-4 Spieltag. Answered 2026-11-16:** one address with two levels, big buttons by default,
  `?mode=marks` and «Pro Spielerin erfassen» for detail (B22); no further merge planned.
- **Q-UX-5 Prüfen. Superseded** by Q-UX-20 (the question screen is built).
- **Q-UX-6 Opponent colour. Answered:** sent only when picked (confirmed on real video, G7).
- **Q-UX-7 Clash rule. Answered:** thresholds in `lib/color.ts kit()` (ANLAUF.md); tune with real
  kits when a pilot club reports a clash.
- **Q-UX-8 Goals conceded by position. Answered:** from shot zones; 7 m, fast breaks, empty goal and
  long range have none.
- **Q-UX-9 Season themes. Answered:** at least two matches with video, positions from six goals and
  30 %.
- **Q-UX-10 Consent link. Open (Lukas)**, part of Q-LEGAL-2. Built: one link per team, 90 days,
  players as number, first name and initial; any adult player or parent may answer for any player;
  limited by rate limits and the audit log.
- **Q-UX-11 Old collections. Answered:** read-only, no migration.
- **Q-UX-12 Onboarding. Answered 2026-11-16:** two steps built (B27); the mail «Deine Spieler
  mitnehmen» is not built (inviting players sits behind «Teamfunktionen»).
- **Q-UX-13 Share a single scene. Answered 2026-11-16:** API and shared page support it; no button
  per scene before the pilot.
- **Q-UX-14 Dark scheme. Answered 2026-11-16:** one light scheme (ADR 030, DESIGN.md); no dark scheme
  before the pilot.
- **Q-UX-15 Ball and holder. Open (recognition).** Lukas: UI first. `ballpossession` exists in
  `handball_vision`, the API does not consume it; `SceneCameraOut.ball` stays empty and the screen
  says «Ball in dieser Szene nicht erkannt».
- **Q-UX-16 Field detection in real halls. Open (recognition)**, see Q-REC-CALQUALITY: the court is
  always asked; only the NLB clips are tested.
- **Q-UX-17 Runs and tactics camera on real video. Open (recognition).** The tactics camera was
  checked on real clips (third and fourth runs: one or two people too many, see Q-REC-CAMERA,
  Q-REC-OFFCOURT); runs depend on Q-REC-CANDTIME (the way before the goal needs the right time).
- **Q-UX-18 Smoothing of paths. Open (recognition).** Catmull-Rom for display only; filtering jitter
  and ID switches waits for Q-REC-OFFCOURT.
- **Q-UX-19 League table. Answered:** from handball.ch when linked (`GET /teams/{id}/official`); no
  table for unlinked teams, none planned.
- **Q-UX-20 Prüfen as questions. Answered (built 2026-11-12):** court, goal candidates, then own
  tracks without a name. Left for recognition: the person box is an estimate (Q-REC-PERSONBOX);
  «Gegner» as an answer needs an API to mark a track as not ours, until then «Weiss nicht».

## Accounts from the entry (UX test round 1, second delivery)
- **Q-AUTH-2b Two-factor reminder later. Answered 2026-11-16:** as built (reminder once there is
  something to protect, on the team page and as a dot in the account menu, dismissible for 7 days);
  the obligation is Q-AUTH-2.
- **Q-AUTH-LINK Sign-in link valid for a day. Answered 2026-11-16:** 24 hours, single use
  (`magic_link_ttl_minutes`); coaches read such mails hours later (round 2, N15). A six-digit code is
  the fallback if this proves too open.
- **Q-AUTH-OWNER Who does a team belong to? Open (Lukas).** Saving a team from `/einstieg` makes that
  person its first admin; a team already in the app gets an access request to its admins plus the
  link «Dieses Team gehört mir, aber jemand anderes hat es schon» (mail to the support). Options:
  (a) hand-over by the support, (b) confirmation via the federation's address, (c) a second person
  of the club confirms. *Recommendation:* (a) for the pilot, (b) before the broad launch.

## A match in several files
- **Q-VIDEO-PARTS Two files for one match. Answered (decided 2026-11-13, built and merged).** Parts in
  a fixed order on one match timeline (`services/matches.parts_of`, `services/timeline.py`), an
  offset per file instead of joining files, HLS playlists joined across parts, order from the camera
  clock or upload order with «Tauschen». Side rule: recordings less than 60 s apart are «Teil 1 /
  Teil 2» without a side change, otherwise halves; per later part «Seitenwechsel vor diesem Teil: ja
  / nein» (migration 0045). Second half waits for the first, takes over its court («Ecken der 1.
  Halbzeit übernehmen»), and opens half 2 of the clock. Checked on real video in the fifth run
  (BERICHT.md). Known small gap: the second half's throw-off is asked only for videos over 65 minutes
  (P4).
- **Q-PARTS-MARKS Courtside marks over a break. Answered 2026-11-16:** one offset per mark session
  stays; marks of the second half are off by a break that is in no file. Accepted for the pilot
  (marks are a side path).
- **Q-PARTS-OVERLAY Workbench overlays. Answered 2026-11-16:** spotlight and mini court read the first
  part only and show nothing in the second half rather than wrong positions; accepted for the pilot
  (tactics camera, runs, places and load read each part).
- **Q-PARTS-RENDITIONS Playback across files. Superseded:** desktop and phone playback passed the
  fifth run; the iPhone check is Q-QA-1.
- **Q-PARTS-ORDER-RERUN Side hint after a swap. Answered 2026-11-16:** not recomputed automatically;
  «Erneut versuchen» on that part runs it with the new hint.

## Areas from the earlier product
- **Q-OLD-AREAS Open (Lukas).** Spielzüge, opponent profile, «Zum Zeigen» and old playlists still
  work, each with a line that it comes from the earlier version; nothing deleted. Options: rebuild,
  fold into Sammlungen, or retire with a data export. *Recommendation:* leave as is in the pilot,
  retire what no pilot club uses.

## Recognition (real-video tests, docs/ux-test/echttest/BERICHT.md, runs 1 to 7)

The recognition code has not changed since 2026-11-12 apart from parts; the items below are open
unless marked.

- **Q-REC-SHOTZONE Shot position for the three things. Answered (decided 2026-11-14, built).** Prüfen
  asks «Von wo?» with one tap after the team of a confirmed goal (`shot_zone` la, rl, rm, rr, ra, kr,
  m7, gs or unknown; `PUT …/goals/{event}/spot`); only places a person gave make the three things and
  count as «mit Wurfort» (`by_coach`); estimates are drawn hollow and count nowhere; «Weiss nicht» is
  asked again in «Wurfort nachtragen». The small court lies as the camera sees it
  (`GET …/goals/{event}/view`); the side comes from the ends the analysis found
  (`shot_positions.goal_by_sides`). Seventh run: right in 8 of 9 goals, the fast-break miss is fixed
  (W1) but not seen again on real video; Prüfen with 22 questions took about 6 to 7 minutes on a
  5-minute clip (sixth and seventh runs). *Open
  (test):* a whole match (50 to 60 goals): do three things appear, how long does Prüfen take. Open
  small finding W4 (title count includes estimated places).
- **Q-REC-SCOREBOARD The hall's scoreboard is not read.** Measured in the fourth run: the text reader
  returns the clock without colon («849»), so `hallboard.py`'s clock rule never anchors, and the
  seven-segment score digits are not found. *Next:* accept three- and four-digit clock fields as
  mm:ss, find the board by red on black, a seven-segment reader.
- **Q-REC-CALQUALITY Court quality not measured.** `observe.py` sets the reprojection error to 0; the
  interface therefore always asks for the court (E03). *Next:* compute the error from the line fit.
- **Q-REC-SIDES Defended side flips** (clip 2, twice). Did not flip in clip 1 (fourth run); «Von wo?»
  depends on it. *Next:* hold the side per half unless the goalkeepers clearly swap.
- **Q-REC-CANDTIME Goal candidates come 4 to 7 s late** (the throw-off after the goal). Scenes of
  candidates now run 12 s before to 5 s after, which catches most shots. *Next:* place the candidate
  at the shot, not the restart.
- **Q-REC-CAMERA Tactics camera in a checked scene.** One or two people too many, a referee missing
  (fourth run); the mirroring is gone since G3.
- **Q-REC-OPPKIT Team split needs both shirt colours.** `teams.relabel_by_clusters` labels nothing
  without the opponent's colour, so the interface asks for it. *Next:* split by the two largest
  clusters and name only our team.
- **Q-REC-PERSONBOX Person boxes with a panning camera.** The worker has the per-frame homography
  (`motion.CameraMotion`) but does not hand it out; person questions only with a fixed camera (E05).
- **Q-REC-OFFCOURT People beside the court tracked as players** (up to 14 dots instead of 7). The
  interface draws only positions on the court (1 m margin) and says positions are estimated (G3).
  *Next:* separate players from spectators and bench; goalkeeper kit as its own class.

## Website (docs/site/KONZEPT.md, docs/site/SEO.md)
- **Q-SITE-1 Prices on the website. Superseded** by Q-PROD-4 (one question); the site follows
  `PRICES_FINAL`.
- **Q-SITE-2 Analysis duration. Answered 2026-11-16:** no fixed number anywhere; the site says the
  app sends a message, the app shows minutes once measurable («Die Minuten bis fertig stehen hier,
  sobald die Analyse richtig läuft.»). A number comes once a whole match is measured on the target
  hardware.
- **Q-SITE-3 «Über uns». Open (Lukas), later.** The page says what we want and how we work, with no
  people (SEO.md section 9, «Braucht Lukas»). Whether to name people, place and pilot clubs is yours.
- **Q-SITE-4 Storage location stated as fact. Answered 2026-11-16:** matches ADR 002, ADR 025 and the
  Terraform default (Switzerland North, R2 EU); providers by name come with Q-LEGAL-1.
- **Q-SITE-5 Public demo. Answered 2026-11-16:** no public demo in the app before the pilot; signed-in
  clubs have the demo match, visitors the site's invented match (`apps/site/public/demo/match.json`).
- **Q-SITE-6 Help guides outside the core. Answered 2026-11-16:** update `help-map.ts` to the Anlauf
  screens (Prüfen, Szenen, Saison, Team), then delete the unlisted guides; not done yet.
- **Q-SITE-7 Trial «30 Tage gratis». Superseded** by Q-BILL-TRIAL (the app starts the trial at
  sign-up).
- **Q-SITE-8 Mail when the three things are ready. Answered 2026-11-13:** built and confirmed in the
  UX test.
- **Q-SITE-9 Team field and colour. Answered:** `/einstieg?q=…&farbe=…&lang=…`, `farbe` only once
  picked.
