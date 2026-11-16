"""Second pass on a finished cut: remove fillers, held sounds and extra pauses without rebuilding masks.

Ported from a five-clip edit. Run it from the build folder, on the joined, leveled voice of the
finished video (16-bit PCM wav, the length of the video) after the cuts and the speed-up:

  python -I drops.py voice.wav --fps 30000/1001 [--drops drops.txt] [--frames 1893]

drops.txt, one drop per line (times in seconds of the finished video; # starts a comment):
  F a b note    remove a..b exactly: a filler or a repeated phrase, edges in the quiet dips around it
  V a b note    a held sound ("deeee") from a to b: shorten it to --keep-held seconds, cut where the
                waveform on both sides of the cut matches (--match-min), so there is no click
  N a b note    a quiet stretch that must stay as it is (no pause trimming there)
It also trims every quiet stretch of --min-pause seconds or more down to --keep-pause, except in
N ranges and in the last 0.6 s (the ending is never tightened).

Every drop is a whole number of video frames, so picture and voice stay in sync. It writes:
  voice-dropped.wav   the voice with the drops removed, 10 ms crossfades at each join
  drops.json          what was removed (kind, start, length, frames), for captions.py --drops
  drops-video.txt     the filter that removes the same frames from the finished video (chained
                      selects of 30 ranges, later drops first so earlier frame numbers don't move)
and prints the command to run it. The frame rate must be the finished video's (after any speed-up).
Held sounds need a clean place to cut: if no place matches well, the drop is skipped and reported;
leave it in and tell the user. Check every cut with checkcuts.py or hear.py (a held sound that is
really a word clips the word).
"""
import argparse
import json
import sys
import wave
from fractions import Fraction

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")


def read_wav(path):
    w = wave.open(path)
    if w.getsampwidth() != 2:
        sys.exit("The voice must be 16-bit PCM. Convert it: ffmpeg -i in.wav -c:a pcm_s16le out.wav")
    sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch).astype(np.float64)
    return sr, ch, x


def parse_drops(path):
    manual = []
    if path:
        for line in open(path, encoding="utf-8"):
            line = line.split("#")[0].strip()
            if line:
                kind, a, b, *note = line.split(None, 3)
                if kind not in ("F", "V", "N"):
                    sys.exit(f"{path}: unknown kind {kind!r} (use F, V or N): {line}")
                manual.append((kind, float(a), float(b), note[0] if note else ""))
    return manual


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("voice")
    ap.add_argument("--fps", help="frame rate of the finished video, e.g. 30 or 30000/1001 (or read it from --plan)")
    ap.add_argument("--plan", default="plan.json", help="plan.json: the frame rate and speed-up are read from it")
    ap.add_argument("--drops", default="drops.txt")
    ap.add_argument("--frames", type=int, help="frame count of the finished video (default: from the voice length)")
    ap.add_argument("--out-voice", default="voice-dropped.wav")
    ap.add_argument("--out-json", default="drops.json")
    ap.add_argument("--out-filter", default="drops-video.txt")
    ap.add_argument("--keep-held", type=float, default=0.19, help="how long a held sound stays")
    ap.add_argument("--keep-pause", type=float, default=0.12, help="how long a trimmed pause stays")
    ap.add_argument("--min-pause", type=float, default=0.20, help="trim quiet stretches at least this long")
    ap.add_argument("--quiet-db", type=float, default=-30.0, help="below this 10 ms level counts as quiet (leveled voice)")
    ap.add_argument("--match-min", type=float, default=0.75, help="how well the waveform must match to cut a held sound")
    ap.add_argument("--no-pauses", action="store_true", help="only the listed drops, no automatic pause trimming")
    ap.add_argument("--list-pauses", action="store_true",
                    help="only list the quiet stretches (--min-pause or longer, under --quiet-db) and stop: an audit of a joined voice")
    a = ap.parse_args()

    if a.fps:
        fps = Fraction(a.fps)
    else:
        try:
            fps = Fraction(json.load(open(a.plan, encoding="utf-8"))["fps"])
        except (OSError, KeyError, ValueError):
            sys.exit("Give the finished video's frame rate with --fps (or run from the folder with plan.json).")
    F = float(1 / fps)  # one frame, seconds
    KEEP_V, KEEP_P, MIN_P, QUIET_DB, MATCH_MIN = a.keep_held, a.keep_pause, a.min_pause, a.quiet_db, a.match_min

    sr, ch, x = read_wav(a.voice)
    mono = x.mean(axis=1) / 32768
    manual = parse_drops(a.drops)
    drops = []  # [kind, start s, frames, note]
    for k, lo, hi, note in manual:
        if k == "F":
            n = max(1, round((hi - lo) / F))
            drops.append(["F", (lo + hi) / 2 - n * F / 2, n, note])
        elif k == "V":
            # find the place and length where the waveform before and after the cut match best
            n, done, best = int((hi - lo - KEEP_V) / F), False, (-2.0, None)
            wn = int(0.012 * sr)
            while n >= 2 and not done:
                best = (-2.0, None)
                for s in np.arange(lo + 0.04, hi - 0.04 - n * F + 1e-9, 0.002):
                    sa = int(round(s * sr))
                    ref = mono[sa - wn:sa + wn]
                    for d in range(-int(0.004 * sr), int(0.004 * sr) + 1, 4):
                        e = sa + int(round(n * F * sr)) + d
                        seg = mono[e - wn:e + wn]
                        c = float((ref * seg).sum() / (np.linalg.norm(ref) * np.linalg.norm(seg) + 1e-12))
                        if c > best[0]:
                            best = (c, s)
                if best[0] >= MATCH_MIN:
                    drops.append(["V", float(best[1]), n, note])
                    done = True
                else:
                    n -= 1
            if not done:
                print(f"V {lo:.2f}-{hi:.2f} skipped: " + ("too short to shorten" if best[1] is None
                      else f"no clean place to cut (best match {best[0]:.2f})"), note)

    # quiet stretches trimmed down to KEEP_P
    H = sr // 100
    nb = len(mono) // H
    db = 20 * np.log10(np.sqrt((mono[:nb * H].reshape(nb, H) ** 2).mean(axis=1)) + 1e-9)
    quiet = db < QUIET_DB
    if a.list_pauses:
        found, i = [], 0
        while i < nb:
            if quiet[i]:
                j = i
                while j < nb and quiet[j]:
                    j += 1
                if (j - i) / 100 >= MIN_P:
                    found.append((i / 100, j / 100))
                i = j
            else:
                i += 1
        for lo, hi in found:
            print(f"{lo:.2f}-{hi:.2f} ({hi - lo:.2f})")
        print(len(found), f"quiet stretches of {MIN_P} s or more below {QUIET_DB} dB; total {sum(hi - lo for lo, hi in found):.2f} s")
        return
    blocked = [(d[1] - 0.02, d[1] + d[2] * F + 0.02) for d in drops] + [(lo, hi) for k, lo, hi, _ in manual if k == "N"]
    i = 0
    while i < nb and not a.no_pauses:
        if quiet[i]:
            j = i
            while j < nb and quiet[j]:
                j += 1
            lo, hi = i / 100, j / 100
            if hi - lo >= MIN_P and not any(lo < e and hi > s for s, e in blocked) and hi < len(mono) / sr - 0.6:
                n = int((hi - lo - KEEP_P) / F)
                if n >= 1:
                    drops.append(["P", (lo + hi) / 2 - n * F / 2, n, f"pause {hi - lo:.2f} s"])
            i = j
        else:
            i += 1
    drops.sort(key=lambda d: d[1])
    for p, q in zip(drops, drops[1:]):
        if q[1] < p[1] + p[2] * F + 0.03:
            sys.exit(f"Drops overlap or touch: {p} and {q}. Merge or move one of them.")

    # audio: remove each drop with a short crossfade; held sounds are cut where the waveform matches
    h = int(0.005 * sr)
    wn = int(0.012 * sr)
    out, pos, err = [], 0, 0.0  # err: samples removed so far minus what the frames call for
    report, frames_removed = [], 0
    for kind, s, n, note in drops:
        sa = int(round(s * sr))
        want = n * F * sr
        match = None
        if kind == "V":
            best, bd = -2.0, 0
            ref = mono[sa - wn:sa + wn]
            for d in range(-int(0.004 * sr), int(0.004 * sr) + 1):
                e = sa + int(round(want)) + d
                seg = mono[e - wn:e + wn]
                c = float((ref * seg).sum() / (np.linalg.norm(ref) * np.linalg.norm(seg) + 1e-12))
                if c > best:
                    best, bd = c, d
            length_samples, match = int(round(want)) + bd, best
        else:
            length_samples = int(round(want - err))
        err += length_samples - want
        seg = x[pos:sa + h].copy()
        if out:
            seg[:2 * h] *= np.linspace(0, 1, 2 * h)[:, None]
        seg[-2 * h:] *= np.linspace(1, 0, 2 * h)[:, None]
        out.append(seg)
        pos = sa + length_samples - h
        f0 = int(round(s / F))
        report.append({"kind": kind, "start": round(s, 3), "len": round(n * F, 4), "frames": [f0, f0 + n - 1],
                       "note": note, "match": None if match is None else round(match, 2)})
        frames_removed += n
    seg = x[pos:].copy()
    if out:
        seg[:2 * h] *= np.linspace(0, 1, 2 * h)[:, None]
    out.append(seg)
    y = out[0]
    for seg in out[1:]:
        y[-2 * h:] += seg[:2 * h]
        y = np.concatenate([y, seg[2 * h:]])
    total_frames = a.frames if a.frames else int(round(len(mono) / sr / F))
    keep_frames = total_frames - frames_removed
    y = y[:int(round(keep_frames * F * sr))]
    o = wave.open(a.out_voice, "wb")
    o.setnchannels(ch)
    o.setsampwidth(2)
    o.setframerate(sr)
    o.writeframes(np.clip(np.round(y), -32768, 32767).astype(np.int16).tobytes())
    o.close()

    json.dump({"frame": F, "fps": str(fps), "old_frames": total_frames, "new_frames": keep_frames, "drops": report},
              open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ranges = [r["frames"] for r in report][::-1]  # later drops first, so earlier frame numbers don't move
    chain = []
    for c in range(0, len(ranges), 30):
        chain.append("select='not(" + "+".join(f"between(n\\,{p}\\,{q})" for p, q in ranges[c:c + 30]) + ")'")
    video = f"[0:v]{','.join(chain)},setpts=N/({fps})/TB[v]" if chain else f"[0:v]setpts=N/({fps})/TB[v]"
    open(a.out_filter, "w", encoding="utf-8").write(video + "\n")

    by = {}
    for r in report:
        by.setdefault(r["kind"], []).append(r["len"])
    names = {"F": "fillers/phrases", "V": "held sounds", "P": "pauses"}
    for k, v in by.items():
        print(f"{names[k]}: {len(v)} drops, {sum(v):.2f} s")
    print(f"sync error {err / sr * 1000:.1f} ms; frames {total_frames} -> {keep_frames}; "
          f"length {total_frames * F:.2f} -> {keep_frames * F:.2f} s")
    held = [r for r in report if r["kind"] == "V"]
    if held:
        print("held sounds cut (start, frames, waveform match):",
              " ".join(f"{r['start']:.2f}({r['frames'][1] - r['frames'][0] + 1}f,{r['match']:.2f})" for r in held))
    for r in held:
        if r["match"] < 0.6:
            print("weak waveform match, listen to this one:", r)
    print(f"Wrote {a.out_voice}, {a.out_json}, {a.out_filter}. Cut the video the same way (use "
          f"-filter_complex_script on FFmpeg 6 or older; add the in-between encoder from my-setup.md):")
    print(f'  ffmpeg -i retouched.mp4 -/filter_complex {a.out_filter} -map "[v]" <in-between encoder> dropped.mp4')
    print(f"Then check: dropped.mp4 must have {keep_frames} frames, and the same length as {a.out_voice}.")


if __name__ == "__main__":
    main()
