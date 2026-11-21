"""Puts a second camera's picture into the main recording, for clips filmed at the same time (an iPhone filming
from the side while the main camera keeps recording). The sound always stays the main camera's, so the voice
never changes and the picture can switch anywhere, even in the middle of a sentence.

  <speech python> -I syncclip.py find <main recording> <second clip> [<second clip> ...] [--margin 1.0]
      Finds where each clip starts in the main recording by comparing their sound, and writes angles.json:
      the second camera's picture for the whole time it recorded, less --margin seconds at each end (pressing
      record and stop). Edit angles.json to change the stretches: add, remove, or change "from" and "to".
  <speech python> -I syncclip.py build <main recording> [--angles angles.json] [--out angles.mov]
         [--encoder "<in-between encoder from my-setup.md>"]
      Writes the main recording with the second camera's picture in those stretches and the main camera's
      sound. Use it instead of the main recording from then on: transcribe, cut, retouch and captions work on
      it unchanged.

Run conform.py on each clip first (same frame rate at a steady rate, same size, no HDR): build refuses a clip
whose size or frame rate differs from the main recording's. Times in angles.json are seconds from the start of
the main recording, as a player shows them.

How the sync works: both sounds are reduced to their loudness every 10 ms, which two different microphones
agree on far better than on the waveform, and slid against each other to find the best match. The match is then
refined on the waveform itself, to about a millisecond. A clip longer than 30 s is also matched at its start and
at its end: if they differ by more than half a frame, the two cameras' clocks drift and it says so. A weak
match (a clip with no speech, or a different take) is reported, not used.

Needs numpy (the speech or face Python has it) and FFmpeg.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from fractions import Fraction

import numpy as np

RATE = 16000          # Hz, for the waveform refinement
HOP = 0.01            # s, for the loudness curve
MIN_SCORE = 0.35      # correlation of the loudness curves below which a match is not trusted
MIN_LEAD = 1.5        # how much better than the next-best place the match must be


def audio(path, rate=RATE):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
                        "-f", "f32le", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        sys.exit(f"{path} has no sound to sync with. Keep the second camera's microphone on, even though its sound "
                 "isn't used.")
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def loudness_curve(x, rate=RATE):
    """Log loudness every HOP seconds, minus its own half-second average: what is left is where the sound gets
    louder or quieter, which doesn't depend on the microphone's level or tone."""
    n = int(rate * HOP)
    m = len(x) // n
    if m < 50:
        return np.zeros(0)
    e = np.log(np.sqrt((x[:m * n].reshape(m, n) ** 2).mean(axis=1)) + 1e-6)
    k = 50
    pad = np.pad(e, (k // 2, k - k // 2 - 1), mode="edge")
    return e - np.convolve(pad, np.ones(k) / k, mode="valid")


def correlate(a, b):
    """Cross-correlation for every lag: c[k + len(b) - 1] is how well b matches a when b[0] sits at a[k]."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    c = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    return np.concatenate([c[-(len(b) - 1):], c[:len(a)]]) if len(b) > 1 else c[:len(a)]


def overlap_score(a, b, lag):
    """Pearson correlation of a and b where they overlap, with b starting at a[lag]."""
    s, e = max(0, lag), min(len(a), lag + len(b))
    if e - s < 100:
        return 0.0
    x, y = a[s:e], b[s - lag:e - lag]
    x, y = x - x.mean(), y - y.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d else 0.0


def coarse(main_curve, clip_curve):
    """(lag in curve steps, score, lead over the next-best place)."""
    c = correlate(main_curve, clip_curve)
    lags = np.arange(-(len(clip_curve) - 1), len(main_curve))
    need = min(len(clip_curve), max(300, len(clip_curve) // 2))  # at least half the clip (or 3 s) must overlap
    overlap = np.minimum(len(main_curve), lags + len(clip_curve)) - np.maximum(0, lags)
    c = np.where(overlap >= need, c, -np.inf)
    best = int(np.argmax(c))
    lag = int(lags[best])
    score = overlap_score(main_curve, clip_curve, lag)
    away = np.abs(lags - lag) > 50  # the next-best place at least half a second away
    rest = c[away & np.isfinite(c)]
    second = max(float(rest.max()), 1e-9) if len(rest) else 1e-9
    return lag, score, float(c[best]) / second if c[best] > 0 else 0.0


def refine(main, clip, start, window=None, search=0.06):
    """The clip's start in the main recording, in seconds, to about a millisecond, near `start` (seconds).
    Only the clip's samples from `window` = (from, to) seconds are used."""
    w0, w1 = window or (0.0, len(clip) / RATE)
    piece = np.diff(clip[int(w0 * RATE):int(w1 * RATE)])  # the change between samples: timing, not tone
    lo = int((start + w0 - search) * RATE)
    hi = int((start + w1 + search) * RATE)
    seg = np.diff(main[max(0, lo):max(0, min(len(main), hi))])
    if len(seg) <= len(piece) or len(piece) < RATE // 2:
        return start
    valid = correlate(seg, piece)[len(piece) - 1:len(seg)]  # lags where the piece lies wholly inside seg
    best = int(np.argmax(valid))
    found = (max(0, lo) + best) / RATE - w0
    return found if abs(found - start) <= search else start


def find_offset(main, clip, fps):
    """{"offset": seconds, "score", "lead", "drift": seconds or None}; offset is where the clip's first sound
    is in the main recording (negative when the clip started first)."""
    lag, score, lead = coarse(loudness_curve(main), loudness_curve(clip))
    offset = refine(main, clip, lag * HOP)
    drift = None
    length = len(clip) / RATE
    if length > 30:
        first = refine(main, clip, offset, window=(0, 10))
        last = refine(main, clip, offset, window=(length - 10, length))
        drift = last - first
    return {"offset": round(offset, 4), "score": round(score, 3), "lead": round(lead, 2),
            "drift": None if drift is None else round(drift, 4), "trusted": score >= MIN_SCORE and lead >= MIN_LEAD}


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"Can't read {path}: {r.stderr.strip()}")
    data = json.loads(r.stdout)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), {})
    sound = next((s for s in data["streams"] if s.get("codec_type") == "audio"), {})
    fps = Fraction(video.get("r_frame_rate", "25/1")) if video.get("r_frame_rate", "0/0") != "0/0" else Fraction(25)
    return {"width": video.get("width"), "height": video.get("height"), "fps": fps,
            "video_start": float(video.get("start_time", 0) or 0), "audio_start": float(sound.get("start_time", 0) or 0),
            "duration": float(data.get("format", {}).get("duration", 0) or 0)}


def stamp(seconds):
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    return f"{sign}{int(seconds // 60)}:{seconds % 60:05.2f}"


def find(a):
    info = probe(a.main)
    fps = float(info["fps"])
    main = audio(a.main)
    angles = []
    for path in a.clips:
        clip = audio(path)
        r = find_offset(main, clip, fps)
        length = len(clip) / RATE
        print(f"{os.path.basename(path)}: starts at {stamp(r['offset'])} in the main recording, {length:.1f} s long "
              f"(match {r['score']:.2f}, {r['lead']:.1f}x better than anywhere else).")
        if not r["trusted"]:
            print("  NOT SURE: the sounds don't match clearly (a clip with no speech, very different sound, or "
                  "another take). Not added: check the clip, or set its offset by hand in angles.json.")
            continue
        if r["drift"] is not None and abs(r["drift"]) > 0.5 / fps:
            print(f"  The two clocks drift {r['drift'] * 1000:+.0f} ms over the clip: run conform.py on it first; if "
                  "it still drifts, use shorter stretches from it.")
        start = max(0.0, r["offset"]) + a.margin
        end = min(info["duration"], r["offset"] + length) - a.margin
        if end - start < 0.5:
            print("  Too short once the margins are taken off: not added.")
            continue
        start, end = round(np.ceil(start * fps - 1e-6) / fps, 3), round(np.floor(end * fps + 1e-6) / fps, 3)  # whole frames, inwards
        angles.append({"clip": path, "offset": r["offset"], "from": start, "to": end})
        print(f"  Its picture is used from {stamp(start)} to {stamp(end)}.")
    with open(a.angles, "w", encoding="utf-8") as f:
        json.dump({"main": a.main, "angles": angles}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {a.angles}. Change the stretches there if wanted, then run build.")


def build(a):
    with open(a.angles, encoding="utf-8") as f:
        data = json.load(f)
    angles = data["angles"]
    if not angles:
        sys.exit(f"{a.angles} has no stretches: nothing to build.")
    info = probe(a.main)
    clips = []
    for entry in angles:
        if entry["clip"] not in clips:
            clips.append(entry["clip"])
    inputs, graph, last = ["-i", a.main], [], "0:v"
    for i, path in enumerate(clips, start=1):
        c = probe(path)
        if (c["width"], c["height"], c["fps"]) != (info["width"], info["height"], info["fps"]):
            sys.exit(f"{path} is {c['width']}x{c['height']} at {float(c['fps']):g} fps, the main recording "
                     f"{info['width']}x{info['height']} at {float(info['fps']):g}: run conform.py on it first.")
        mine = [e for e in angles if e["clip"] == path]
        # Where the clip's frames land on the main recording's clock: its sound starts `offset` seconds after
        # the main recording's sound, and each file's picture and sound keep their own start times.
        shift = info["audio_start"] + mine[0]["offset"] - c["audio_start"]
        enable = "+".join(f"between(t\\,{info['video_start'] + e['from']:.4f}\\,{info['video_start'] + e['to']:.4f})"
                          for e in mine)
        inputs += ["-i", path]
        graph.append(f"[{i}:v]setpts=PTS+{shift:.6f}/TB[c{i}]")
        graph.append(f"[{last}][c{i}]overlay=enable='{enable}':eof_action=pass:format=auto[v{i}]")
        last = f"v{i}"
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", f"[{last}]",
           "-map", "0:a?", "-c:a", "copy", *shlex.split(a.encoder), a.out]
    if os.path.abspath(a.out) == os.path.abspath(a.main):
        sys.exit("--out must be a new file: the main recording is never overwritten.")
    if subprocess.run(cmd).returncode:
        sys.exit("FFmpeg failed: nothing was written.")
    used = sum(e["to"] - e["from"] for e in angles)
    print(f"Wrote {a.out}: {len(angles)} stretch(es) from the second camera, {used:.1f} s in all, with the main "
          "camera's sound throughout. Use it instead of the main recording from here on.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    f = sub.add_parser("find")
    f.add_argument("main")
    f.add_argument("clips", nargs="+")
    f.add_argument("--margin", type=float, default=1.0, help="seconds left out at each end of a clip (default 1)")
    f.add_argument("--angles", default="angles.json")
    b = sub.add_parser("build")
    b.add_argument("main")
    b.add_argument("--angles", default="angles.json")
    b.add_argument("--out", default="angles.mov")
    b.add_argument("--encoder", default="-c:v libx264 -crf 14 -preset medium")
    a = ap.parse_args()
    {"find": find, "build": build}[a.command](a)


if __name__ == "__main__":
    main()
