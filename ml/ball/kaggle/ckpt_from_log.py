"""Rebuild a ball-net checkpoint from the "R6CKPT <tag> i/n <base64>" lines a training kernel prints (the Kaggle
log survives a cancelled run, /kaggle/working does not).

usage: python ckpt_from_log.py <kernel log (Kaggle JSON log or plain text)> <out.pt> [tag]
Without a tag the last complete checkpoint in the log is taken; the weights come back as float32."""
import base64, io, json, re, sys, zlib

import torch


def text_of(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    try:
        ev = json.loads(raw)
        return "".join(e.get("data", "") for e in ev if e.get("stream_name", "stdout") == "stdout")
    except ValueError:
        return raw


def main(log, out, want=None):
    parts, order = {}, []
    for m in re.finditer(r"R6CKPT (\S+) (\d+)/(\d+) ([A-Za-z0-9+/=]+)", text_of(log)):
        tag, i, n = m.group(1), int(m.group(2)), int(m.group(3))
        if tag not in parts:
            parts[tag] = [None] * n; order.append(tag)
        parts[tag][i - 1] = m.group(4)
    full = [t for t in order if all(parts[t])]
    print("checkpoints in the log:", order, "complete:", full)
    tag = want or (full[-1] if full else None)
    if tag not in full:
        sys.exit(f"no complete checkpoint {tag!r}")
    sd = torch.load(io.BytesIO(zlib.decompress(base64.b64decode("".join(parts[tag])))), map_location="cpu", weights_only=True)
    torch.save({k: (v.float() if v.is_floating_point() else v) for k, v in sd.items()}, out)
    print("wrote", out, "from", tag)


if __name__ == "__main__":
    main(*sys.argv[1:4])
