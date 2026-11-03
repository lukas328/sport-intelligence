# 019. Video session: presentations, phone remote, offline pack, exports

- Status: accepted
- Date: 2026-11-03

## Context
Addendum 01, 4.1 asks for a presentation mode with presenter view, a phone remote over WebSocket
(< 300 ms), offline playback in the cabin, MP4 export with burned-in drawings and a PDF.

## Decision
- **Remote: Server-Sent Events plus POST instead of a raw WebSocket.** The presenter subscribes to
  `/presentations/{id}/remote/stream?key=…` (SSE), the phone posts commands. Both go through the same
  origin proxy and Redis pub/sub bus as the job progress stream, so no second protocol, no extra
  proxy configuration and the same cookie auth (both devices must be signed in with an account that
  may edit the presentation; the pairing key only selects the channel). Latency is one Redis
  publish plus one SSE write; the presenter shows the measured latency of every command.
- **Offline: per-presentation Cache Storage pack.** The app downloads the presentation data, the
  presenter page and only the HLS segments inside the clip windows (lowest rendition) into
  `hb-pres-<id>`; the service worker answers from it when the network is gone. A ZIP with MP4 and
  local player is not needed: the MP4 export covers "take it on a stick".
- **MP4 export in the worker** (ffmpeg): clip windows cut from the analysis proxy, slow-motion ranges
  with `setpts`, hold points as still frames with drawings rendered by Pillow (same geometry as the
  player), text and stat slides as title cards, concatenated at 1280x720, 25 fps.
- **PDF in the API**: stills cut from the thumbnail sprite (no video decoding in the API) plus notes.
- **Spotlight** is drawn on a canvas in the browser from the tracks and the court-to-image homography,
  with interpolation and a soft fade on track loss. Burning it into exports needs per-frame overlays;
  it is done together with the highlight renderer in A3 (same machinery as the portrait crop).

## Consequences
- The remote works wherever the app works (no WebSocket upgrade through proxies).
- Offline packs live in one browser profile; the coach packs on the laptop used in the cabin.
