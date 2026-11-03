# Addendum 01: plan

Date: 2026-11-03 · Status: planned, waiting for "weiter"

The running milestone was finished first: M0 to M9 are done and green in CI, including the extras after
M9 (live tagging, recovery codes, key rotation, performance budgets, phone layout). The addendum is in the
repo as `docs/BRIEF_ADDENDUM_01.md`; PLAN.md section 5, ADR 017 and OPEN_QUESTIONS (Q-ADD-1 to 6) are
updated.

## Where each item lands
Because M1 to M9 are finished, their addendum items move into four new milestones before launch
(addendum 1.3). Order: schema and protection first, then what coaches use weekly, then automation, then
club operations.

| Addendum item | Original milestone | New milestone |
|---|---|---|
| Data model section 3, roles incl. parents, admin handover, players in several teams | M1 | A1 |
| Consent per purpose with history, parent consent | M1 | A1 |
| Youth and opponent protection 4.9 | M1, M5 | A1 |
| Match formats and match clock, similar-kit warning | M2, M3, M4 | A1 |
| Partner adapters (section 7), P2 preparations (section 6) | M9 | A1 |
| Own tags and smart playlists 4.4 | M2 | A2 |
| Presentation mode 4.1 | M7 | A2 |
| Spotlight 4.2 | M3 | A2 (player), A3 (golden-set accuracy) |
| Multi-angle player 4.5 | M5 | A2 |
| Player feed with self-assessment 4.7 | M7 | A2 |
| Scouting report and A6 goalkeeper card 4.6 | M7 | A2 |
| Automatic event baseline (needed by P1) | M4 | A3 |
| Automatic highlights 4.3 | M4 | A3 |
| Special cases 4.8 (several files, tournaments, side change, training videos, poor Wi-Fi) | M2, M3 | A3 |
| QR bill, VAT, dunning 4.10 | M8 | A4 |
| Help centre, support, onboarding 4.11 | M8 | A4 |
| Product analytics, status page, alerts, AI quality, storage policy, pentest scope 4.12 | M8, M9 | A4 |
| Marketing site 4.13 | M8 | A4 |
| Usability test, 3 real matches, extended go-live criteria (section 10) | M9 | A4 / Launch |
| Ask your data 5.1, statistics matrix and Sportscode 5.4, problem to training 5.6, training planning 5.7 | new | M10 |
| Native apps 5.5, phone as camera 5.2, live tagging with video sync 5.3, public profile 5.8, paper photo 5.9, federation licences 5.10 | new | M11 |
| P2 items section 6 | new | M12+ (A1 prepares the interfaces) |

## What changes in what is already built
- **Roles and policies:** five new roles; every endpoint gets rows in the policy matrix test. Parents see
  only their own child's content, which needs a guardianship link and a filter in feeds, clips and reports.
- **Consent:** the two existing kinds (`video_analysis`, `identification`) migrate to the five purposes;
  highlights, sharing and model training check them. Share links already hide names; public sharing of
  youth content becomes impossible instead of "without player rows".
- **Opponents:** the tagger and imports already work with numbers; opponent names entered by coaches get a
  "public source" note and are excluded from shares, PDFs, highlights and exports.
- **Matches:** `MatchFormat` replaces the fixed 2 × 30 minutes (`HALF_S = 1800`) in clock mapping, live mode,
  metrics and the season view. Several video files per match via `MatchSegment`.
- **Camera switch:** the existing goal-cam switch becomes the multi-angle player with picture-in-picture.
- **Live mode:** stays as the optional match-clock mode; M11 adds device time and video sync (Q-ADD-2).
- **Billing:** card subscriptions exist; annual QR-bill invoicing, VAT and dunning are added next to Stripe.
- **Paper reports:** the JSON importer stays; the photo path (5.9) feeds the same schema.
- **Assistant:** reuses the number validator and fallback rules of the summaries (ADR 015).

## Risks
1. **Automation gap (biggest).** P1 and the P0 items highlights, player feed and scouting report assume
   automatic events; today they come from tagging and imports, and tracking is a heuristic baseline that
   misses the BRIEF targets on synthetic data. Without real videos and trained models, A3 cannot meet
   its acceptance criteria. Decision path in Q-ADD-1.
2. **Accuracy targets need test material:** spotlight 95 %, multi-angle < 2 frames, portrait crop 90 %,
   paper photos 95 % (Q-ADD-6).
3. **Scope:** A1 to A4 together are larger than M5 to M8. Launch dates should be planned per milestone,
   not as one block.
4. **Legal and tax:** consent texts, terms, VAT status and QR-bill details need an external review before
   real invoices go out (Q-ADD-3, Q-ADD-5).
5. **Usability and real-match tests** need people and halls; they cannot be simulated by me.
6. **Rendering cost:** burned-in spotlight and portrait reels add worker time per match; must stay inside
   P10 (≤ 45 min, < CHF 2). Measured from A2 on.

## Vision-Check of the current state
- P1 Automatisch zuerst: **partly violated**. Events still need tagging or imports; tracking runs
  automatically.
- P2 Jede Zahl führt zum Video: kept; every count and insight opens its events and the video.
- P3 Ehrlich statt beeindruckend: kept; estimates are labelled, summaries are number-checked, no silent
  fallbacks.
- P4 Amateur zuerst: largely kept (resumable upload, offline live mode, phone layout). Annual invoice
  payment is missing.
- P5 Team-Plattform, Torhüter als Modul: kept; the goalkeeper tab is part of the analysis, priced as an add-on.
- P6 Nachwuchs schützen: partly kept (youth defaults, no names in shares). Parent role and consent per
  purpose are missing (A1).
- P7 Datenschutz als Standard: kept for opponents (numbers) and data regions in the design. Purposes are
  still coarse.
- P8 Handball-Sprache: kept in de-CH, en, fr. A review by coaches is still open.
- P9 Partner statt alles selbst: kept, nothing built that the non-goals exclude. Adapters come in A1.
- P10 Schnell und günstig: CPU benchmark 60 min in about 28 min; GPU cost not measured on real hardware yet.
