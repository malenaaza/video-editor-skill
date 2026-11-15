"""Builds the cut plan for a video: which source frames to keep, snapped to the frame grid.

Run from the project's build folder. Needs only Python, FFmpeg and ffprobe.

  python -I cutplan.py build <source video> <transcript.json> [--cuts cuts.json] [options]
      Finds the pauses, removes them and the ranges in cuts.json, keeps a tail after the
      last word, and writes plan.json. Prints what it kept, and every stretch without
      words that is still in the cut (handling noise, hums: check each one).
  python -I cutplan.py filter [--plan plan.json] [--out cut-filter.txt]
      Writes the FFmpeg filter that makes the cut, and prints the command to run it.
  python -I cutplan.py to-source <t> [<t> ...]     times in the cut -> times in the source
  python -I cutplan.py to-output <t> [<t> ...]     times in the source -> times in the cut

cuts.json holds the judgment calls, in source seconds (the same clock as the transcript):
  {"remove":  [[12.40, 19.85, "first take of the intro"], [31.02, 31.40, "um"]],
   "protect": [[44.10, 44.90, "dip inside 'absolutamente'"]]}
"remove" ranges are always cut. "protect" ranges are never cut by the pause remover.

All times in plan.json are true source times: the transcript's clock plus the audio
stream's start time (some phones start the audio a little after the picture). Every kept
piece starts and ends on a whole video frame, and the audio is cut at the same instants,
so picture and sound can't drift apart over many cuts.
"""
import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction

sys.stdout.reconfigure(encoding="utf-8")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)


def probe(video):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,r_frame_rate,avg_frame_rate,start_time,sample_rate:format=duration",
               "-of", "json", video]).stdout
    info = json.loads(out)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if v is None or au is None:
        sys.exit("The source needs one video and one audio stream.")
    rate = v.get("avg_frame_rate") or v["r_frame_rate"]
    if rate in ("0/0", "0"):
        rate = v["r_frame_rate"]

    def start(s):
        try:
            return float(s.get("start_time", 0))
        except (TypeError, ValueError):
            return 0.0

    return {"fps": rate, "duration": float(info["format"]["duration"]),
            "audio_offset": round(start(au) - start(v), 4), "sample_rate": int(au.get("sample_rate", 48000))}


def loudness(video):
    err = run(["ffmpeg", "-nostdin", "-hide_banner", "-i", video, "-vn", "-af", "ebur128", "-f", "null", "-"]).stderr
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(found[-1]) if found else None


def silences(video, noise_db, min_len, duration):
    err = run(["ffmpeg", "-nostdin", "-hide_banner", "-i", video, "-vn", "-af",
               f"highpass=f=70,silencedetect=noise={noise_db}dB:d={min_len}", "-f", "null", "-"]).stderr
    out, start = [], None
    for line in err.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            start = max(float(m.group(1)), 0.0)
        m = re.search(r"silence_end: (-?[\d.]+)", line)
        if m and start is not None:
            out.append([start, float(m.group(1))])
            start = None
    if start is not None:
        out.append([start, duration])
    return out


def load_words(path, offset):
    data = json.load(open(path, encoding="utf-8"))
    words = []
    for seg in data.get("segments", []):
        for w in seg.get("words", []):
            words.append([w["start"] + offset, w["end"] + offset, w["word"].strip()])
    return words


def subtract(keep, cut):
    """Remove the ranges in `cut` from the ranges in `keep`."""
    for a, b in sorted(cut):
        nxt = []
        for s, e in keep:
            if b <= s or a >= e:
                nxt.append([s, e])
                continue
            if a > s:
                nxt.append([s, a])
            if b < e:
                nxt.append([b, e])
        keep = nxt
    return keep


def overlaps(a, b, ranges):
    return any(a < e and b > s for s, e in ranges)


def build(a):
    info = probe(a.source)
    fps = Fraction(info["fps"])
    offset = info["audio_offset"] if a.audio_offset is None else a.audio_offset
    words = load_words(a.transcript, offset)
    if not words:
        sys.exit("The transcript has no word times. Transcribe with word timestamps first.")
    cuts = json.load(open(a.cuts, encoding="utf-8")) if a.cuts else {}
    remove = [[r[0] + offset, r[1] + offset] + list(r[2:]) for r in cuts.get("remove", [])]
    protect = [[r[0] + offset, r[1] + offset] for r in cuts.get("protect", [])]

    noise = a.noise
    lufs = None
    if noise is None:
        lufs = loudness(a.source)
        noise = -48 if lufs is not None and lufs <= -30 else -38
    sil = silences(a.source, noise, a.min_silence, info["duration"])

    # Where the video ends: a tail after the last kept word. A trailing word fades out slowly
    # and Whisper ends it early, so take the later of Whisper's end and where the sound stops.
    kept_words = [w for w in words if not any(r[0] <= (w[0] + w[1]) / 2 < r[1] for r in remove)]
    if not kept_words:
        sys.exit("Every word falls inside a removed range.")
    last_end = kept_words[-1][1]
    for s, e in sil:
        if s >= kept_words[-1][0] and s <= last_end + 1.0:
            last_end = max(last_end, s)
            break
    end = min(last_end + a.tail, info["duration"])

    pause_cuts = []
    for s, e in sil:
        if s >= last_end - 0.01:
            continue  # the pause after the last word is kept (the tail)
        if a.keep_pause > 0:  # natural pace: shorten long pauses instead of removing them
            if e - s <= a.keep_pause:
                continue
            cs, ce = s + a.keep_pause * 0.4, e - a.keep_pause * 0.6
        else:
            cs, ce = s + a.pad_after, e - a.pad_before
        if s <= 0.001:
            cs = 0.0  # lead-in before the first word
        if ce - cs < a.min_cut or overlaps(cs, ce, protect):
            continue
        pause_cuts.append([cs, ce])

    keep = subtract([[0.0, end]], pause_cuts)
    keep = subtract(keep, [r[:2] for r in remove])

    # Snap to whole frames, drop slivers, join pieces that touch.
    frames = []
    for s, e in keep:
        f0, f1 = round(s * fps), round(e * fps)
        if f1 - f0 < a.min_frames:
            continue
        if frames and f0 <= frames[-1][1]:
            frames[-1][1] = max(frames[-1][1], f1)
        else:
            frames.append([f0, f1])
    if not frames:
        sys.exit("Nothing left to keep.")
    offsets, total = [], 0
    for f0, f1 in frames:
        offsets.append(total)
        total += f1 - f0

    plan = {"source": a.source, "fps": str(fps), "speed": a.speed, "audio_offset": offset,
            "sample_rate": info["sample_rate"], "silence_db": noise, "frames": frames, "offsets": offsets,
            "total_frames": total, "removed": [[round(r[0], 3), round(r[1], 3)] + r[2:] for r in remove]}
    json.dump(plan, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    fpsf = float(fps)
    print(f"Source: {info['duration']:.2f} s at {fpsf:.3f} fps. Audio starts {offset:+.3f} s against the picture.")
    if lufs is not None:
        print(f"Voice loudness {lufs:.1f} LUFS, so silence threshold {noise} dB.")
    print(f"Kept {len(frames)} pieces, {total} frames = {total / fpsf:.2f} s"
          + (f" ({total / fpsf / a.speed:.2f} s at {a.speed}x)" if a.speed != 1 else "")
          + f". Removed {len(pause_cuts)} pauses and {len(remove)} listed ranges.")

    # Stretches still in the cut with no words: handling noise, hums, or words Whisper missed.
    covered = []
    for w0, w1, _ in kept_words:
        for (f0, f1), o in zip(frames, offsets):
            s, e = max(w0, f0 / fpsf), min(w1, f1 / fpsf)
            if e > s:
                covered.append([o / fpsf + s - f0 / fpsf, o / fpsf + e - f0 / fpsf])
    quiet = []
    for s, e in subtract([[0.0, total / fpsf]], covered):
        if e - s >= a.wordless:
            quiet.append((s, e - s, to_source(plan, s)))
    tail_from = total / fpsf - a.tail - 0.05
    quiet = [q for q in quiet if q[2] is not None and q[0] < tail_from]
    if quiet:
        print(f"Stretches of {a.wordless} s or more with no words still in the cut (check each; "
              "add to cuts.json \"remove\" if nobody is speaking):")
        for o, length, src in quiet:
            print(f"  cut {o:7.2f} s, source {src - offset:7.2f} s (transcript clock), {length:.2f} s")
    print("Wrote", a.out)


def load_plan(path):
    plan = json.load(open(path, encoding="utf-8"))
    plan["_fps"] = float(Fraction(plan["fps"]))
    return plan


def to_output(plan, t):
    """Source time -> time in the cut before speed-up, or None if that instant was removed."""
    fps = plan.get("_fps") or float(Fraction(plan["fps"]))
    for (f0, f1), o in zip(plan["frames"], plan["offsets"]):
        if f0 / fps <= t < f1 / fps:
            return o / fps + t - f0 / fps
    return None


def to_source(plan, t):
    fps = plan.get("_fps") or float(Fraction(plan["fps"]))
    for (f0, f1), o in zip(plan["frames"], plan["offsets"]):
        if o / fps <= t < (o + f1 - f0) / fps:
            return f0 / fps + t - o / fps
    return None


def write_filter(a):
    plan = load_plan(a.plan)
    fps = Fraction(plan["fps"])
    speed = plan.get("speed", 1) or 1
    frames = plan["frames"]
    select = "+".join(f"between(n\\,{f0}\\,{f1 - 1})" for f0, f1 in frames)
    v = f"[0:v]select='{select}',setpts=N/({fps})/TB"
    if speed != 1:
        v += f",setpts=PTS/{speed},fps={fps}"
    lines = [v + "[v];"]
    fade = 0.008
    n = len(frames)
    lines.append(f"[0:a]asplit={n}" + "".join(f"[s{i}]" for i in range(n)) + ";" if n > 1 else "[0:a]anull[s0];")
    for i, (f0, f1) in enumerate(frames):
        s, e = float(f0 / fps), float(f1 / fps)
        d = e - s
        lines.append(f"[s{i}]atrim={s:.6f}:{e:.6f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d={fade},afade=t=out:st={max(d - fade, 0):.6f}:d={fade}[a{i}];")
    tail = f"concat=n={n}:v=0:a=1" if n > 1 else "anull"
    if speed != 1:
        tail += f",atempo={speed}"
    lines.append("".join(f"[a{i}]" for i in range(n)) + tail + "[a]")
    open(a.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    total = plan["total_frames"]
    print(f"Wrote {a.out}: {n} pieces, {total} frames ({total / float(fps) / speed:.2f} s).")
    print("Run it (use -filter_complex_script instead of -/filter_complex on FFmpeg 6 or older; add the "
          "hardware decoder and the in-between encoder from my-setup.md; put grade, LUT or zooms in a later pass "
          "or append them to the [v] chain):")
    print(f'  ffmpeg -i "{plan["source"]}" -/filter_complex {a.out} -map "[v]" -map "[a]" '
          f"<in-between encoder> -c:a pcm_s16le cut.mov")
    print("Then check: frame count of the result must be "
          + (f"{total}" if speed == 1 else f"about {round(total / speed)}") + ", and video and audio the same length.")


def convert(a, fn):
    plan = load_plan(a.plan)
    speed = plan.get("speed", 1) or 1
    for t in a.times:
        if fn is to_source:
            r = to_source(plan, t * speed)
            r = None if r is None else r - plan["audio_offset"]
            print(f"cut {t:.3f} -> " + ("past the end of the cut" if r is None else f"source {r:.3f} (transcript clock)"))
        else:
            r = to_output(plan, t + plan["audio_offset"])
            print(f"source {t:.3f} -> " + ("removed" if r is None else f"cut {r / speed:.3f}"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("source")
    b.add_argument("transcript")
    b.add_argument("--cuts", help="cuts.json with remove and protect ranges")
    b.add_argument("--out", default="plan.json")
    b.add_argument("--noise", type=float, help="silence threshold in dB (default: -38, or -48 for quiet voices)")
    b.add_argument("--min-silence", type=float, default=0.14)
    b.add_argument("--pad-after", type=float, default=0.05, help="kept after a silence starts")
    b.add_argument("--pad-before", type=float, default=0.10, help="kept before a silence ends")
    b.add_argument("--min-cut", type=float, default=0.04, help="don't bother with cuts shorter than this")
    b.add_argument("--keep-pause", type=float, default=0.0,
                   help="natural pace: shorten pauses to this length (e.g. 0.3) instead of removing them")
    b.add_argument("--tail", type=float, default=0.5, help="kept after the last word")
    b.add_argument("--speed", type=float, default=1.0, help="speed-up applied after cutting, from my-setup.md")
    b.add_argument("--min-frames", type=int, default=3, help="drop kept pieces shorter than this")
    b.add_argument("--wordless", type=float, default=0.4, help="report kept stretches without words this long")
    b.add_argument("--audio-offset", type=float, help="override the audio start time read from the file")
    f = sub.add_parser("filter")
    f.add_argument("--plan", default="plan.json")
    f.add_argument("--out", default="cut-filter.txt")
    for name in ("to-source", "to-output"):
        c = sub.add_parser(name)
        c.add_argument("times", nargs="+", type=float)
        c.add_argument("--plan", default="plan.json")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a)
    elif a.cmd == "filter":
        write_filter(a)
    else:
        convert(a, to_source if a.cmd == "to-source" else to_output)


if __name__ == "__main__":
    main()
