# Match video workspace: reference patterns

Research date: 2026-11-05. Scope: how established video-analysis, video-review, match-centre and
triage products structure their screens, condensed into patterns for our match video workspace
("Die Halle": club colour stage on top, calm workbench below, Barlow and Barlow Condensed,
hairlines instead of cards, one Harzgelb signal per screen; see `docs/design/identity/DECISIONS.md`).

How to read this file:

- **Verified** means the statement is taken from the cited page (vendor docs, help centre, changelog).
- **Unverified** means it comes from secondary sources, memory of the product, or the page would not
  load (several help centres returned 403). Treat those as hypotheses to check in a trial account.
- Many help pages are vendor material. They describe what exists, not whether it is good.

---

## 1. Sports video analysis

### Hudl Sportscode (desktop, pro analysts)

- **Layout.** Movie window, a code window (tagging buttons) and a timeline of *code rows*: one row per
  code (for example "Attack A", "Goal"), each row holding *instances* (time ranges) in chronological
  order. Verified via the manual structure and the toolbar page:
  https://www.hudl.com/support/manuals/sportscode/code/the-timeline/the-timeline-toolbar
- **Rows have a colour chip left of the row name**, set per row (or many rows at once) from a palette.
  Colour belongs to the row, not to individual instances. Verified:
  https://www.hudl.com/support/manuals/sportscode/review-and-analyze/code-rows/working-with-code-rows
- **Labels** (descriptors such as player, zone, outcome) are attached to instances via right-click on
  the instance, which opens the label tree. Verified (toolbar page).
- **Toolbar verbs are concrete and analysis-shaped**: Make Movie, New Row, New Merged Row (rows built
  from a selection), New Timeline (from selected instances), Matrix (counts of codes x labels),
  Organizer, Sorter, Find. Playback settings include "Merge Rows" (chronological across rows),
  "Sequential Rows", "Append slow" (play real speed then 50% slow-mo) and "Overlay Text" (row name,
  instance number, labels over the movie). Verified (toolbar page).
- **Counts** live in the Code Matrix: a grid of codes against labels, clickable to play the instances
  behind a number. Verified that the Matrix exists and opens from the timeline; cell-click behaviour is
  standard Sportscode practice but **unverified** from the fetched text.
- **Crafted feel:** the timeline is the database. Every number in a matrix can be played as video. The
  vocabulary is the analyst's own (instance, row, label), not generic "items".

### Hudl (team film room, Hudl Assist breakdowns)

- **Layout (volleyball guide, the most detailed current Hudl page):** search bar plus Filters above the
  video; a *context bar* top-left over the video showing current action type, player and score; an
  annotation toolbar above the video; a right sidebar switching between Video, Reports, Comments, List,
  Saved Clips, Review, Grid and Timeline. Verified:
  https://www.hudl.com/support/hudl-volleyball/guides/navigate-video
- **Three views of the same events:** List (chronological, grouped by rally), Grid (spreadsheet below
  the player with result, quality, score, zones, speed, phase, video time), Timeline (horizontal, *one
  row per team per contact type*: Serve, Receive, Set, Attack, Dig, Block ...). Clicking any item in any
  view seeks the video. Verified (same page).
- **Comments** are written in a box that shows the current timestamp and rally; they pin to that moment.
  Audience selector: Everyone, a group (Coaches, Athletes) or a person; @ mentions notify. Verified
  (same page).
- **Drawings:** Text, Arrow, Line, Circle, Block, Freehand, Laser pen; Undo and Delete Effect. Verified
  (same page).
- **Playlists:** select saved clips, add to existing playlist or highlight, or "Send to Team
  Highlights". Verified (same page).
- **Hudl Assist (breakdown service):** football breakdowns carry 16 data columns (formation, down,
  distance, result ...). Clicking a visual or a number filters the film to matching clips; the first
  filter splits O/D/K. Verified: https://hudl.com/products/assist
- **Crafted feel:** a number is always a filter for video. The context bar puts score and action on the
  frame so the coach never loses the game state.

### Nacsport

- **Tagging windows** are coach-built button templates: categories (rows) and descriptors (qualifiers).
  Each click on a category creates a register (clip) with preset pre/post-roll or manual start/stop.
  Verified (reseller docs): https://sportperformanceanalysis.com/article/nacsport-videoanalysis-software-overview
- **Timeline:** one row per category; registers can be edited, resized, annotated with notes or
  drawings; rows can be shown/hidden by colour, and the colour filter applies to timeline and matrix
  alike; the timeline can be collapsed to give the video more room. Verified:
  https://support.analysispro.com/kb/article/266/timeline-basics
- **Hotkeys** to move up/down category rows and registers are described by a reseller; exact keys
  **unverified**. Nacsport 9 expanded hotkeys on tagging buttons and added a Clip Filter usable from the
  timeline. Verified: https://www.analysispro.com/blog/nacsport-9
- **Matrix** of categories x descriptors, exportable as picture or Excel; row/column order fixed in the
  template so it is stable across matches. Verified:
  https://support.analysispro.com/kb/article/269/data-matrix
- **Crafted feel:** stability. The same template, the same row order and colours every match, so a
  coach's eye learns where "goal" sits.

### Catapult Pro Video (Focus) and Metrica Play

- **Focus timeline** shows all tags of a session chronologically, one row per tag type (operator guide,
  **partly verified**: https://sites.google.com/catapultsports.com/gamedayoperators/focus/focus-logger).
- **Focus 7.7 Row View** for presentations: clip durations visible as lengths, drag clips between rows,
  drag whole rows, flags and notes per clip, custom clip colours (example given: red critical, green
  success, blue improvement), real-time multi-user editing; List view spans tags from several matches.
  Verified: https://www.catapult.com/blog/pro-video-focus-7-7-release
- **Metrica Play:** telestration attached to events (spotlights, rings, future trail, areas, drawings,
  text, auto-pause at the event). Verified via Metrica's own codeball docs: https://pypi.org/project/codeball
  Metrica's tagging UI itself: **unverified** (no public docs found).
- **Crafted feel:** durations shown as length, not as a number column. Annotation is attached to the
  event, not to the screen.

### Wyscout (Hudl)

- Before playback the user chooses a *video option*: Full match, Effective time, Goals, Highlights, Key
  events. Selecting key events produces a clip list under the video; the player skips clip to clip.
  Goal markers on the scrubber are **ball icons**. Verified:
  https://hudl.com/support/wyscout/guides/watching-video
- **Crafted feel:** "effective time" as a first-class way to watch (dead time removed) and a
  sport-native marker glyph instead of a generic dot.

### Dartfish (dartfish.tv tagging)

- **Keys:** Shift+I / Shift+O set entry and exit at the playhead; Space or K play/pause; R replays from
  the event entry; U / Z zoom the event timeline in/out; Left/Right go to previous/next event; Tab moves
  between edit fields; Alt+Enter saves; Esc cancels; B creates a default 4-second event at the
  playhead. Verified: https://support.dartfish.tv/en/support/solutions/articles/27000081586 and
  https://support.dartfish.tv/support/solutions/articles/27000048166-how-to-tag-a-video-clip
- **Crafted feel:** "R = replay from entry" is the single most useful review key for checking a proposed
  moment; the timeline has its own zoom keys.

### Spiideo Perform

- Tag timeline sits directly below the player and shows all tags by default; arrow buttons either side
  jump to previous/next tag; a "# Tags" button hides tag types. Verified:
  https://support.spiideo.com/en/articles/11487856-use-your-spiideo-tags
- Tag panels with A-Z / 0-9 hotkeys; one-click tags with pre/post-roll, or duration tags (press to start,
  press again to stop, with a running timer above the tag); two-level tags where second-level buttons
  stay greyed until a first level is pressed and must be chosen within 6 seconds; Cancel to undo a wrong
  first level. Verified: https://support.spiideo.com/en/articles/4708322-tagging-in-spiideo-perform
- Imported tags are aligned by choosing one reference tag and nudging it frame-by-frame or by 5 s.
  Verified: https://support.spiideo.com/en/articles/12818090-import-and-export-tags-in-spiideo-perform
  (Directly analogous to our throw-off sync.)
- **Crafted feel:** timers and greyed states give immediate feedback; alignment by one anchor event.

### Veo (Editor and Analytics)

- AI flags goals, shots, corners, free kicks (football, rugby, lacrosse); users add missing events,
  drag mis-placed shots, filter events by type, team or player; drawing: arrows, shapes, freehand,
  spotlight. Shot, heat and pass maps come with Analytics and **each stat links to its video moment**.
  Verified: https://www.veo.com/product/veo-editor
- Under the video, **filled circles are clips, outlined circles are (AI) events**; timeline filter for
  own team vs opponent; periods, events, clips and bookmarks accessible from the timeline. From search
  snippet of https://support.veo.com/hc/en-us/articles/4453318310161 (page itself returned 403:
  **partly verified**). Keyboard shortcut list exists in Help & Resources, keys **unverified**.
- **Crafted feel:** filled vs outlined marker separates "proposed by machine" from "made by a person"
  without a second colour.

---

## 2. General video review and editing

### Frame.io

- **Comments at timecode:** pause, type; the comment card shows the timecode and clicking it seeks there.
  Typing in the comment box auto-pauses playback. Verified:
  https://help.frame.io/en/articles/9105251-commenting-on-your-media
- **Range comments:** I / O set in and out, or drag brackets under the play bar; on the scrubber a range
  comment is a bubble with a long tail; clicking the card makes the range the playback window; Esc returns
  to full playback. Enter sends. Verified (same page).
- **Annotations:** arrow, line, box, freehand on the frame; shown only when the comment card is selected,
  not during normal playback. Verified (same page).
- **V4:** after sending a comment, focus returns to the player so J/K/L keep working; typing again pauses;
  pixel-anchored comments (click a point on the frame); hover on the timeline shows frame previews;
  comment filters (annotations, attachments, reactions); every comment has a link. Verified:
  https://blog.frame.io/2024/05/28/frame-io-v4-features-player-and-commenting/
- **J/K/L** shuttle (J rewind 1x/2x/4x/8x, K play/pause, L forward), arrows step frames. Verified:
  https://help.frame.io/en/articles/7785-keyboard-shortcuts-legacy
- Comment sorting by timecode, newest, oldest, commenter; hashtags for filtering. Verified:
  https://support.frame.io/en/articles/3331455-commenting
- **Crafted feel:** focus management. Writing never fights playback; the keyboard always knows where it is.

### Descript

- Markers appear as section headers in the script and as bookmarks (purple) on the timeline; drag to move.
  Time ruler carries timecode, markers, comments and audio levels; lanes stack above the script track.
  Zoom: "Fit scene" and "Fit composition" in the top-right of the timeline. Verified:
  https://help.descript.com/hc/en-us/articles/10164735239693 and
  https://help.descript.com/hc/en-us/articles/10249275208717
- **Crafted feel:** two named zoom presets instead of a raw slider; the ruler is an information layer.

### Premiere Pro (and NLE conventions generally)

- M adds a marker at the playhead, M again opens the marker dialog; eight marker colours, mappable to
  keys; a Markers panel lists all markers, sortable and filterable by colour; double-click to edit.
  Mostly secondary sources (PremiumBeat, ProVideo Coalition, Adobe community): **partly verified**.
  https://www.provideocoalition.com/tool-tip-tuesday-for-adobe-premiere-pro-clearing-select-marker-colors/
- **Convention to inherit:** I/O, J/K/L, M, arrow frame-step are muscle memory for anyone who has cut
  video. DaVinci Resolve follows the same conventions (**unverified** here, not fetched).

### YouTube Studio

- Chapters are defined as timestamps in the description (start at 0:00, ascending) and render as
  segments of the scrubber. Studio editor lanes: **unverified** (no source found).
- **Pattern to inherit:** segmenting the scrubber itself (for us: halves, timeouts).

---

## 3. Match centres (reading results)

- **Opta / The Analyst match momentum:** per-minute value = difference between the two teams' threat
  (max possession value per minute, capped 0-0.1, recency-weighted over 3-4 minutes, smoothed to avoid
  jumpy minutes). Verified: https://theanalyst.com/articles/what-is-match-momentum
- **Flashscore Match Momentum:** one bar per minute; each minute shows only the team with the higher
  value; taller bar = higher scoring probability; lives in the Statistics section; updates each minute.
  Verified: https://www.flashscore.com/news/momentum/W82o7eCa/
- **SofaScore Attack Momentum:** rises and falls with pressure; sustained dominance reads as steady
  peaks; inputs include dangerous passes and shots. Verified (vendor article, via search):
  https://www.sofascore.com/news/how-sofascores-attack-momentum-changed-sport-analysis
  Visual form (home above, away below a centre axis in team colours, goal and card icons on the axis,
  half-time gap): from product use, **unverified** by text source.
- **FotMob:** momentum graph added in 2023; live xG sits in a mini stat section on the Facts tab, deeper
  data in Stats, player xG/xA in Lineup. Verified: https://www.fotmob.com/topnews/3627-live-xg-data-is-now-fotmob
  Chart drawing details **unverified**.
- **ESPN win probability:** criticism worth noting: a live probability readout adds little; the chart
  is useful *after* the fact, as a full-game shape. Source (opinion):
  https://defector.com/espns-win-probability-graphic-wants-to-give-you-gambling-brain
- **BBC Sport / Bundesliga app key-event timelines:** no usable source found, **unverified**.
- **Crafted feel common to all:** one shared time axis for score, momentum and events; minimal chrome;
  team identity carried by side (above/below, left/right) more than by colour alone.

---

## 4. Fast review and triage

- **Superhuman:** E marks done (archive) and moves on; H brings it back; Cmd+K command palette exposes
  every action and teaches its shortcut; split inbox separates "needs you now" from the rest. Vendor
  blog and reviews: https://blog.superhuman.com/inbox-zero-in-7-steps/ (help article 403,
  **partly verified**). Sub-100 ms claim **unverified**.
- **Gmail:** Auto-advance setting opens the next (or previous) conversation after archive/delete; `]`
  and `[` archive and move. Verified (official 2010 post plus guides):
  https://gmail.googleblog.com/2010/10/new-in-labs-auto-advance-to-next.html
- **Linear triage:** Accept, Escalate, Merge, Decline (prompts for a reason comment), Snooze, by key or
  menu; `?` shows shortcuts. Verified: https://linear.app/changelog/2021-06-29-linear-release-and-issue-triage
  Exact keys **unverified**.
- **Linear redesign (craft):** reduce chrome colour, align labels/icons/buttons on both axes ("something
  you'll feel after a few minutes"), LCH-generated themes from three inputs (base, accent, contrast),
  more density and contrast in the Inbox. Verified:
  https://linear.app/now/how-we-redesigned-the-linear-ui and
  https://linear.app/changelog/2024-03-20-new-linear-ui
- **Roboflow Annotate review mode:** A approve, R reject, Left/Right previous/next image, Esc deselect,
  Cmd+Z undo. Verified: https://docs.roboflow.com/annotate/use-roboflow-annotate/keyboard-shortcuts
- **Label Studio Enterprise review:** Accept, Fix + Accept, Reject (back to annotator); a task can count
  as reviewed after one accepted annotation or all. Hotkeys customisable, listed in editor settings.
  Verified: https://docs.humansignal.com/guide/quality and https://labelstud.io/guide/hotkeys
- **CVAT:** review mode with an Issue tool (mark a region, describe the problem); job states new / in
  progress / rejected / completed; shortcut hints on hover; customisable shortcuts with conflict
  warnings. Verified: https://docs.cvat.ai/docs/qa-analytics/manual-qa/
- **Crafted feel:** one key per decision, auto-advance, undo always available, the queue length visible.

---

## 5. What makes a UI look generated, and remedies

Sources:

1. Anthropic, "Improving frontend design through Skills" (2025-11-12): unguided output converges on
   Inter, purple gradients on white, minimal motion, predictable layouts, "cookie-cutter design that
   lacks context-specific character". Remedy: commit to one aesthetic, CSS variables, "dominant colors
   with sharp accents outperform timid, evenly-distributed palettes", motion only at high-impact moments.
   https://claude.com/resources/articles/improving-frontend-design-through-skills
2. Rakesh Mondal, "Why Your SaaS UI Looks AI-Generated" (2026-06-28): equal-weight cards; untouched
   default components; every screen a dashboard; one spacing value everywhere; spinner-only empty and
   error states; placeholder copy; no clear primary action. Remedies: one dominant element per screen,
   layout chosen by task (editor, list-detail, guided setup), spacing rhythm (tight within groups, clear
   between), designed edge states, specific microcopy, one emphasised primary action.
   https://www.saasui.design/blog/saas-ui-looks-ai-generated
3. Keela Vamshi (GeekyAnts), "Why Everything Your AI Builds Looks the Same" (2026-08-19): oversized
   sans headlines, purple gradients, rounded cards and bento grids, soft shadows, one icon family, neutral
   copy. Remedies: semantic tokens, a preferred component path, documented product rules (drawer vs
   modal, how AI confidence is shown), approved examples *and anti-examples*, lint arbitrary colours and
   spacing, visual regression. https://geekyants.com/blog/why-everything-your-ai-builds-looks-the-same
4. Linear redesign (above): craft is alignment, restraint in chrome colour, and density tuned on purpose.

Concrete tells to check our screens against: card grid of equal KPI tiles; every block with border +
radius + shadow; icon next to every heading; a badge colour for every status; "Overview" / "Insights"
style headings; emoji or sparkle icons on AI features; same gap everywhere; centred empty state with a
grey illustration; tooltips explaining what a label should have said.

---

## 6. Synthesis: patterns to adopt (22)

Each: **pattern** / where seen / why for our coaches / how it looks in Die Halle.

1. **Video is the anchor, everything seeks it.** / Hudl (any list, grid or timeline item seeks), Veo
   (every stat links to video), Hudl Assist. / Coaches trust a number only after seeing the clip. /
   Every row, bar, shot dot and table cell in the workbench is clickable and seeks; hover shows the
   video time in Barlow tabular figures. No number without a way to the video.
2. **One shared time axis under the video.** / Spiideo, Veo, Sportscode, match-centre momentum charts. /
   Possession timeline, goals, comments and attacks are all "when"; one axis removes mental mapping. /
   A single full-width ruler (0:00 to 60:00 game time) below the player; lanes stacked on it,
   separated by hairlines, not boxes.
3. **Lanes per meaning, team by side.** / Sportscode code rows, Hudl volleyball timeline (row per team
   per action), momentum charts (home above, away below). / Handball is two-sided; side is faster to
   read than colour. / Lanes: Goals, Attacks, Possession, Comments. In the Possession lane team A is
   above a centre hairline, team B below, each in its club-derived tone. Lane labels in Barlow
   Condensed caps at the left edge, 11-12 px.
4. **Game time, not file time.** / Wyscout "effective time"; match centres use match minutes. / The
   video starts minutes before throw-off; coaches think "47th minute". / Ruler and all lists show game
   clock (H1 23:41); file time only in a secondary mono-like tabular figure on hover. Half-time is a
   visible gap in the axis.
5. **Halves and timeouts segment the scrubber.** / YouTube chapters, Sportscode periods, Veo periods. /
   Orientation in a 90-minute file. / Scrubber split into H1 / H2 segments by a thicker hairline;
   team timeouts as small ticks with "TO" labels.
6. **Proposed vs confirmed by fill, not by colour.** / Veo (outlined = event, filled = clip). / Goal
   proposals need a visible "not yet confirmed" state without adding colour noise. / Proposed goal:
   outlined ring on the Goals lane; confirmed: filled in team tone; rejected: removed, recoverable via
   undo. The one pending item in focus gets the Harzgelb signal.
7. **One-key decisions with auto-advance.** / Roboflow (A/R), Superhuman (E), Gmail (auto-advance, `]`),
   Linear triage. / 30 to 60 proposals per match; mouse travel kills the session. / In goal review:
   `A` = goal team A, `B` = goal team B, `X` = not a goal, then auto-seek to the next proposal with
   pre-roll. Key letters printed next to the buttons in small caps.
8. **Replay-from-entry key.** / Dartfish (R replays from event entry). / A coach checks a goal by
   watching the last 5 seconds again, not by scrubbing. / `R` replays the proposal from its pre-roll;
   Space play/pause; J/K/L shuttle; Left/Right step frames.
9. **Always-visible undo.** / Roboflow Cmd+Z, Superhuman H, Spiideo Cancel. / Fast keys mean mistakes;
   fear of mistakes makes people slow. / After each decision a one-line hairline-bordered note at the
   bottom of the review list: "Goal B at H2 12:04 confirmed. Z to undo." No toast stack.
10. **Queue length and progress as a printed count.** / Superhuman inbox zero, Label Studio review
    stream, Linear triage. / Coaches want to know how much is left before training. / "14 of 38
    reviewed" in Barlow Condensed with a thin progress hairline under the stage; running score
    (confirmed A : B) next to the official score from the match report.
11. **Reconcile against the official record.** / Spiideo (align imports by one reference tag), Hudl Assist
    (data next to film). / The match report is the truth; the app's job is to show differences. / Two
    columns like a printed score sheet: report score progression vs confirmed goals; mismatching lines
    marked with the signal, each line seeks the video.
12. **Anchor-based sync.** / Spiideo import alignment (pick one reference, nudge by frame or 5 s). /
    Throw-off setting is exactly this. / "Set H1 throw-off" = pause on the frame, press `T`; nudge with
    arrows (frame) and Shift+arrows (5 s); the ruler re-labels live.
13. **Comments pinned to time, optionally a range, focus returns to the player.** / Frame.io (I/O
    ranges, auto-pause on typing, focus back to player), Hudl (timestamp shown in the comment box). /
    Coaches comment while watching. / Comment field shows "H1 18:22" before text; I/O for range; Enter
    sends and playback keys work again immediately. Comments appear as small ticks in the Comments lane.
14. **Drawings belong to a comment and show only when it is selected.** / Frame.io, Metrica (drawing per
    event). / Keeps playback clean; drawings make sense only with context. / Pencil tool inside the
    comment composer; on playback the frame is clean; selecting the comment pauses and overlays.
15. **Audience on every comment and clip.** / Hudl (Everyone / group / person). / Club reality: coaches
    vs players vs parents, youth consent. / A plain text selector "Coaches only / Team / Player" before
    send; default Coaches only. No lock icons everywhere, one word.
16. **Count tables are filters (matrix pattern).** / Sportscode and Nacsport matrix, Hudl Assist
    (click a number to filter film). / "7 of 11 fast breaks scored" must lead to those 11 clips. /
    Stats rendered as a printed match-sheet table, tabular figures, hairline rules; each count is a link
    that filters the attacks list and the timeline.
17. **Stable order and colour across matches.** / Nacsport templates (fixed row order), Sportscode row
    colours. / Recognition over reading: goals are always the top lane, team A always above. / Lane order
    and team tones are fixed in the design system, never reordered by data.
18. **Duration drawn as length.** / Catapult Row View. / Attack length and possession spells are
    tactical facts. / Attacks lane shows each attack as a bar of its real length; list rows show a tiny
    length bar instead of a "Duration" column only.
19. **Timeline zoom with named presets.** / Descript (Fit scene / Fit composition), Dartfish (U/Z). /
    A 60-minute axis cannot show a 4-second event. / Two presets: "Game" (whole match) and "Moment"
    (±30 s around playhead), plus `+`/`-`. Labels as text buttons, not a slider.
20. **Momentum as a minute-bar chart, read after the game.** / Flashscore (one bar per minute),
    Opta (smoothed, recency-weighted), ESPN criticism (charts after the fact, not live gauges). /
    Possession share per minute tells the story of runs better than one percentage. / A possession
    "Verlauf" strip: one bar per game minute, team A up, team B down, goals as small marks on the centre
    line, half-time gap. One sentence above it as the reading ("B controlled 38-45, then lost it").
21. **Context bar on the frame.** / Hudl volleyball (action type, player, score top-left over video). /
    While scrubbing, coaches lose the score state. / Thin overlay top-left: game clock, score at this
    moment, current attack team. Barlow Condensed, semi-transparent dark, no box radius.
22. **Keyboard map visible, discoverable on `?`.** / Linear `?`, Superhuman Cmd+K, CVAT hover hints. /
    Coaches are not power users by default; visible keys teach. / Key letters in buttons, `?` opens a
    one-column printed key sheet styled like the match sheet.

## 7. Anti-patterns (11)

1. **KPI tile grid.** Equal cards for "Possession 54%", "Goals 28", "Attacks 61". Use one match-sheet row
   with one value marked by the signal.
2. **Card around everything.** Border + radius + shadow on the video, the list, the stats. Workbench uses
   hairlines and whitespace; only the stage is a surface.
3. **Separate charts with separate x-axes.** Momentum, goals and comments each in their own widget with
   their own time scale. One axis.
4. **Colour as the only team signal.** Two club colours can be similar (red vs orange) or fail for
   colour-blind users. Use side (above/below) plus colour.
5. **Rainbow event types.** A colour per event type (Sportscode-style row colours exported 1:1). Keep two
   team tones, neutral ink, and one signal.
6. **Modal per decision.** Confirming a goal must not open a dialog. Inline keys, inline undo.
7. **Toast stacks.** Floating confirmations piling up bottom-right. A single status line in place.
8. **Raw file timestamps.** "01:13:42" when the coach thinks "H2 28:10".
9. **Live-gauge style percentages without the shape.** A big "54%" donut. Show the minute strip instead;
   the total is a footnote.
10. **Generic AI decoration.** Sparkle icons on "AI proposals", gradient banners, "Insights" headings,
    emoji. Say "Proposed by tracking, 38 moments" in plain text.
11. **Spinner-only states.** "Processing..." with a spinner for a 40-minute job. Show stage, progress and
    what the coach can already do (e.g. set throw-off while tracking runs).

## 8. Review rubric (score a screenshot 1 to 5)

1 = clearly fails, 3 = partly, 5 = fully. A screen below 3 on questions 1, 2 or 7 is not ready.

1. **Anchor:** Is the video plus one shared time axis unmistakably the centre, with lists and stats
   subordinate? (1: dashboard of equal blocks; 5: video and axis dominate, everything else hangs off them.)
2. **One signal:** Is there exactly one Harzgelb mark, and does it sit on the single thing needing action
   now? (1: none or several; 5: one, obviously right.)
3. **Hairlines over cards:** Is structure made with rules, alignment and spacing rhythm rather than boxes,
   shadows and radii? (1: card grid; 5: reads like a printed match sheet.)
4. **Game language:** Are times in game clock (H1/H2), teams by name, terms a handball coach uses
   (Angriff, Tempogegenstoss, 7 m), copy specific? (1: generic SaaS labels; 5: could only be our product.)
5. **Team by side:** Can you tell team A from team B without relying on colour? (1: colour only; 5: side,
   order and label agree everywhere.)
6. **Numbers lead to video:** Does every count, bar and dot visibly afford a jump to the clip? (1: dead
   numbers; 5: every number is a filter or seek.)
7. **Review speed:** In the goal-review state, are the decision keys, current item, remaining count and
   undo all visible without moving the eyes off the video area? (1: mouse-only, no count; 5: all four.)
8. **Proposed vs confirmed:** Is machine output visually distinct from coach-confirmed data, without
   extra colours? (1: indistinguishable; 5: fill/outline or similar, consistent across lanes and lists.)
9. **Typographic hierarchy:** Barlow Condensed for labels and big figures, Barlow for text, tabular
   figures in all number columns, at most three sizes on the workbench? (1: mixed defaults; 5: disciplined.)
10. **Edge states:** Do empty, processing and error states tell the coach what to do next in a sentence?
    (1: spinner or blank; 5: specific next step, matching the identity.)
