# 022. Native apps: Expo, bearer sessions, signed media paths, push through the worker

- Status: accepted
- Date: 2026-11-03

## Context
Addendum 01, 5.5 asks for iOS and Android apps with Expo (React Native) sharing the API client and
logic with the web: player feed, clips, assignments, notifications, presentation remote, recording
mode (5.2), courtside marks (5.3) and attendance (5.7), with push via APNs/FCM, deep links and an
offline cache. The web app authenticates with an HttpOnly session cookie plus a CSRF double submit
(ADR 008); native HLS players cannot send auth headers to segment requests.

## Decision
- **Expo SDK 57** with expo-router (`apps/mobile`), TypeScript strict, the generated
  `@handball/api-client` and the new `@handball/client-core` (offline marks queue, resumable upload
  plan, recording checks, deep-link parser) shared with the web app.
- **Bearer sessions for the apps**: `POST /v1/auth/login` with `x-client: native` returns the
  session token in the body (no cookie); the app keeps it in the keychain (expo-secure-store) and
  sends `Authorization: Bearer`. The API accepts either the cookie or the bearer token. Bearer
  requests carry no cookie, so the CSRF check does not apply; a web page cannot set this header on a
  cross-site request. Browsers never get the token in a response body.
- **Signed media paths**: `POST /videos/{id}/media-token` (normal permission check) returns
  `/v1/media/{id}/{exp}.{hmac}/` valid for four hours. HLS playlists use relative segment URLs, so
  segments resolve inside the signed path without headers. Originals and the proxy MP4 stay
  excluded, as on the cookie route.
- **Push**: devices register Expo push tokens (`/v1/me/devices`); every in-app notification also
  queues a job on the existing worker queue, which posts batches of up to 100 to the Expo push
  service (APNs/FCM behind it). Texts are short and name nobody; the payload carries the web link,
  which the app maps to a screen (`client-core.parse`).
- **Recording upload** uses the existing presigned multipart upload: parts of the server's part
  size, resume state next to the file, large uploads wait for Wi-Fi unless the user allows mobile
  data.

## Consequences
- The apps can be built only with an Expo/EAS project, Apple and Google developer accounts and
  push credentials (OPEN_QUESTIONS Q-M11-3); CI typechecks and tests the app's logic but cannot run
  it on devices. Cold start, a 70-minute recording and store review stay to be done on devices.
- An offline cache of assigned clips needs downloadable clip files (HLS is not stored as a file);
  the app caches lists and the marks queue, clip files come later (MP4 clip export per assignment).
- A leaked bearer token works like a stolen cookie until logout or expiry; logout deletes the
  session server-side and removes the push token.
