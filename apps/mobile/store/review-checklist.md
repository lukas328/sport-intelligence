# App review checklist (Apple App Store Review Guidelines, Google Play policies)

| Item | Status |
|---|---|
| Demo account for the reviewers (a club with an analysed demo match, `support.demo_match`) | to create on production before submission |
| Login only with e-mail and password: Sign in with Apple not required (no third-party social login in the app) | ✅ |
| Account deletion can be started in the app (Guideline 5.1.1(v)) | ✅ More, Delete account (opens the deletion in the settings) |
| Permission texts for camera and microphone in de and en (`app.json`) | ✅ |
| Notifications only after a permission prompt, nothing essential depends on them | ✅ |
| No hidden features, no external purchases (subscriptions are bought on the web by clubs; the app has no paywall or purchase links) | ✅ |
| Privacy labels / Data safety form match the app (`store/*.md`) | ✅ texts ready |
| Privacy policy URL | https://handball-intelligence.com/de/datenschutz/ (draft, legal review pending: Q-ADD-5) |
| Content of minors: no public content in the app; youth protection rules of the API apply | ✅ |
| Background activity: uploads continue only while the app is open or allowed by the system | ✅ |
| Screenshots (6.7", 5.5", 12.9" iPad; Android phone and tablet) | to produce from a device build |
| Cold start under 2 s on a mid-range device | to measure on a device build (not possible in CI) |
| 70-minute recording on a mid-range phone without interruption | to test on a device (keep awake, storage and battery checks are in place) |
