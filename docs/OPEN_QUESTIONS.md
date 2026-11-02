# Open questions

Each question has the **assumption** I work with until it is answered. Status: open unless marked.

## Product and business
- **Q-PROD-1 Product name and domain.** "Handball AI" is very close to the competitor *handball.ai*
  named in the brief (trademark and confusion risk). *Assumption:* working title only; no domain hard-coded
  (problem URIs use `urn:handball-platform:...`).
- **Q-PROD-2 Languages.** de-CH ("ss") first. Germany uses "ß". *Assumption:* v1 ships de-CH only, a de-DE
  variant can be added as a separate locale later.
- **Q-PROD-3 Company entity, VAT and currencies for Stripe** (CHF only, or CHF + EUR). *Assumption:* CHF and EUR prices in config.
- **Q-PROD-4 Prices** are placeholders from BRIEF 13.

## Data and test material
- **Q-DATA-1 Test videos** (you mentioned you have some). Needed per video: camera type (fixed / auto-follow,
  Veo, Spiideo, ...), resolution and fps, venue, whether goal cams exist, final score and scorers (ground
  truth), and **consent of the filmed players** (minors?). *Assumption:* videos are never committed to
  git; they go to a bucket (or Git LFS) and the repo holds only `ml/eval/golden_set/manifest.json`.
- **Q-DATA-2 Paper match report JSON schema and files** (BRIEF 15). *Assumption:* importer is built in M4
  once the schema is provided; files live in `data/paper_reports/` (gitignored by default, they contain names).
- **Q-DATA-3 Golden set annotation**: who annotates the 5 full matches, with which tool (CVAT, Label Studio,
  own backoffice tool from M8)? Budget?
- **Q-DATA-4 Customer data for training**: opt-in in the terms or separate consent (BRIEF 12)?
  *Assumption:* separate, explicit opt-in per organisation, off by default.
- **Q-DATA-5 handball.ch**: is there an official data access (API, export, partnership)? *Assumption:* stub
  adapter only, nothing is scraped (BRIEF 7.4).

## Infrastructure
- **Q-INFRA-1 Hosting provider** (ADR 002 proposed: Exoscale or Infomaniak in CH, AWS Zurich fallback) and
  **GPU provider** with CH/EU processing and DPA. Needs price/availability check.
- **Q-INFRA-2 GitHub repository and org**, CI secrets, preview deploy target. *Assumption:* GitHub Actions,
  preview job disabled until hosting exists (`vars.PREVIEW_DEPLOY_ENABLED`).
- **Q-INFRA-3 E-mail provider** Postmark vs Resend (ADR in M1). *Assumption:* Postmark (EU data residency to verify).
- **Q-INFRA-4 MinIO** no longer ships community images; local S3 is SeaweedFS (ADR 006). Answered, for information.
- **Q-INFRA-5 Next.js version**: the brief pins Next.js 15; Next.js 16 is current. *Assumption:* stay on 15.5.x
  as specified, upgrade in a dedicated step if wanted.

## ML and licences
- **Q-ML-1 Ultralytics Enterprise licence**: buy or not? *Assumption:* no; Apache-2.0 detectors in production (ADR 003).
- **Q-ML-2 Licences** of TeamTrack, UNIRI-HBD and the Roboflow set need a legal check for commercial
  training (recorded in `ml/datasets/LICENSES.md`).

## Legal and privacy
- **Q-LEGAL-1** Privacy policy, DPA (AVV) and terms need legal review (placeholders from M8/M9).
- **Q-LEGAL-2 Youth consent workflow**: do parents get their own account, or does the club upload signed
  consent? *Assumption:* club records consent per player (who, when, document reference); parent accounts later.
- **Q-LEGAL-3 Retention periods** for raw video vs. derived data. *Assumption:* configurable per organisation,
  default raw video 24 months.

## QA
- **Q-QA-1 iPhone/Safari acceptance** (M2) needs a real device or a device cloud (BrowserStack/Sauce Labs).
  Playwright WebKit covers the engine, not iOS.
