"""Map filler times in a finished export back to the source, and find their exact edges.

Usage (from the project's build folder):
  python -I findfill.py <out_start> <out_end> <kind> [<out_start> <out_end> <kind> ...]
kind: cut (remove the whole sound) or short (keep the first 0.15 s of a drawn-out word)

Expects in the build folder the plan.json that cutplan.py writes (or, for older projects,
a plan.py that defines FPS, frames and offsets), and the source audio at ../audio.wav
(change AUDIO below if yours is elsewhere). Times given are in the finished video, after
any speed-up; times printed are on the transcript's clock, ready for cuts.json.
"""
import contextlib
import io
import json
import os
import subprocess
import sys

from fractions import Fraction

import numpy as np

AUDIO = "../audio.wav"
SILENT_DB = -42  # level that counts as the dip between words

sys.stdout.reconfigure(encoding="utf-8")
SPEED, AUDIO_OFFSET = 1.0, 0.0
if os.path.exists("plan.json"):
    plan = json.load(open("plan.json", encoding="utf-8"))
    frames, offsets, FPS = plan["frames"], plan["offsets"], float(Fraction(plan["fps"]))
    SPEED, AUDIO_OFFSET = plan.get("speed", 1) or 1, plan.get("audio_offset", 0)
else:
    scope = {"__name__": "plan"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(open("plan.py", encoding="utf-8").read(), scope)
    frames, offsets, FPS = scope["frames"], scope["offsets"], scope["FPS"]

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", AUDIO, "-af", "highpass=f=70", "-f", "s16le",
                      "-ac", "1", "-ar", "16000", "-"], capture_output=True).stdout
audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
HOP = 160  # 10 ms
rms = np.array([np.sqrt(np.mean(audio[i:i + 320] ** 2) + 1e-12) for i in range(0, len(audio) - 320, HOP)])
db = 20 * np.log10(rms)


def to_source(t):
    """Time in the finished video -> time in ../audio.wav (the transcript's clock)."""
    t *= SPEED
    for (a, b), o in zip(frames, offsets):
        if o / FPS <= t < (o + b - a) / FPS:
            return a / FPS + t - o / FPS - AUDIO_OFFSET
    return None


args = sys.argv[1:]
result = []
while args:
    s, e, kind = float(args[0]), float(args[1]), args[2]
    args = args[3:]
    src_s, src_e = to_source(s + 0.03), to_source(e - 0.03)
    if src_s is None or src_e is None:
        print(f"out {s:.2f}-{e:.2f}: outside the cut, skipped")
        continue
    if src_e - src_s > (e - s) * SPEED + 0.1:  # the word sits right after a cut: start at that cut
        src_s = src_e - (e - s) * SPEED + 0.06
    # walk to the loudest point in the word, then out to the dips on each side
    win = range(max(0, int(src_s * 100)), int(src_e * 100) + 1)
    peak = max(win, key=lambda k: db[k])
    left = peak
    while left > 0 and db[left - 1] > SILENT_DB:
        left -= 1
    right = peak
    while right < len(db) - 1 and db[right + 1] > SILENT_DB:
        right += 1
    a, b = left / 100, (right + 1) / 100
    if kind == "short":
        a = a + 0.15
    env = " ".join(f"{db[k]:.0f}" for k in range(max(left - 8, 0), min(right + 9, len(db)), 2))
    print(f"out {s:.2f}-{e:.2f} -> src {src_s:.2f}-{src_e:.2f} sound {left/100:.2f}-{(right+1)/100:.2f} "
          f"cut {a:.2f}-{b:.2f} ({b - a:.2f}s) {kind}\n   env(20ms): {env}")
    result.append([round(a, 2), round(b, 2)])
print(json.dumps(result))
