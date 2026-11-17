"""The edit in numbers: what was cut, what's left, and how the finished video measures.

  python -I editreport.py <original> <finished video> [--plan plan.json] [--cuts cuts.json] [--drops drops.json]
                          [--out <finished name>-report.txt]

It prints a short report and saves it next to the finished video:
- length: original -> finished, and how much was removed;
- cuts: the pieces kept (plan.json), the retakes and fillers removed (the notes in cuts.json, and drops.json from
  the second pass);
- pauses left in the finished voice: how many quiet stretches of 0.15 s or more, and the longest;
- loudness (LUFS) and true peak of the finished video;
- resolution, frame rate, frame count and file size.
Give these numbers to the user in a few lines, in their language, at the end of an edit. Needs Python and FFmpeg.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from array import array
from fractions import Fraction
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RETAKE = re.compile(r"retake|take|toma|repet|repeat|restart|redo", re.I)
FILLER = re.compile(r"\bum+\b|\buh+\b|\beh+\b|\bmm+\b|filler|muletilla|hum|ehh|e+h|vale|like", re.I)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
                          "stream=codec_type,width,height,r_frame_rate,nb_read_packets:format=duration,size",
                          "-of", "json", path], capture_output=True, text=True, timeout=300).stdout
    info = json.loads(out)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    fmt = info.get("format", {})
    return {"seconds": float(fmt.get("duration", 0) or 0), "bytes": int(fmt.get("size", 0) or 0),
            "width": video.get("width"), "height": video.get("height"),
            "fps": float(Fraction(video["r_frame_rate"])) if video.get("r_frame_rate") else None,
            "frames": int(video["nb_read_packets"]) if video.get("nb_read_packets") else None,
            "audio": any(s.get("codec_type") == "audio" for s in info.get("streams", []))}


def loudness(path):
    err = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null",
                          "-"], capture_output=True, text=True, errors="replace", timeout=600).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    peak = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", err)
    return (float(lufs[-1]) if lufs else None), (float(peak[-1]) if peak and peak[-1] != "-inf" else None)


def pauses(path, minimum=0.15, below_db=22.0):
    """Quiet stretches in the finished voice, measured as in cutplan.py: 10 ms loudness under the voice's peaks."""
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vn", "-af", "highpass=f=70", "-f", "s16le",
                          "-ac", "1", "-ar", "16000", "-"], capture_output=True, timeout=600).stdout
    samples = array("h")
    samples.frombytes(pcm[:len(pcm) // 2 * 2])
    hop = 160
    count = len(samples) // hop
    if count < 50:
        return 0, 0.0
    db = [10 * math.log10(sum(v * v for v in samples[i * hop:(i + 1) * hop]) / hop / 32768 ** 2 + 1e-12) for i in range(count)]
    threshold = sorted(db)[int(0.95 * (count - 1))] - below_db
    runs, i = [], 20  # skip the first 0.2 s and the last 0.6 s (lead-in and the held ending)
    end = count - 60
    while i < end:
        if db[i] < threshold:
            j = i
            while j < end and db[j] < threshold:
                j += 1
            if (j - i) / 100 >= minimum:
                runs.append((j - i) / 100)
            i = j
        else:
            i += 1
    return len(runs), (max(runs) if runs else 0.0)


def notes_of(path):
    if not path or not os.path.exists(path):
        return []
    data = json.load(open(path, encoding="utf-8"))
    return [str(r[2]) if len(r) > 2 else "" for r in data.get("remove", [])]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original")
    ap.add_argument("finished")
    ap.add_argument("--plan", default="plan.json")
    ap.add_argument("--cuts", default="cuts.json")
    ap.add_argument("--drops", default="drops.json")
    ap.add_argument("--out")
    a = ap.parse_args()
    before, after = probe(a.original), probe(a.finished)
    lines = []
    removed = before["seconds"] - after["seconds"]
    share = removed / before["seconds"] * 100 if before["seconds"] else 0
    lines.append(f"Length: {before['seconds']:.1f} s -> {after['seconds']:.1f} s ({removed:.1f} s removed, {share:.0f}%)")
    if os.path.exists(a.plan):
        plan = json.load(open(a.plan, encoding="utf-8"))
        lines.append(f"Pieces kept: {len(plan['frames'])} ({max(len(plan['frames']) - 1, 0)} joins)"
                     + (f", sped up {plan['speed']}x" if plan.get("speed", 1) not in (1, 1.0) else ""))
    notes = notes_of(a.cuts)
    retakes = sum(bool(RETAKE.search(n)) for n in notes)
    fillers = sum(bool(FILLER.search(n)) and not RETAKE.search(n) for n in notes)
    if os.path.exists(a.drops):
        drops = json.load(open(a.drops, encoding="utf-8")).get("drops", [])
        fillers += sum(d["kind"] == "F" for d in drops)
        held = sum(d["kind"] == "V" for d in drops)
    else:
        held = 0
    if notes or held or fillers:
        other = len(notes) - retakes - sum(bool(FILLER.search(n)) and not RETAKE.search(n) for n in notes)
        lines.append(f"Removed: {retakes} retakes, {fillers} fillers" + (f", {held} held sounds shortened" if held else "")
                     + (f", {other} other cuts" if other > 0 else ""))
    if after["audio"]:
        count, longest = pauses(a.finished)
        lines.append(f"Pauses left: {count} of 0.15 s or more" + (f", longest {longest:.2f} s" if count else ""))
        lufs, peak = loudness(a.finished)
        if lufs is not None:
            lines.append(f"Loudness: {lufs:.1f} LUFS" + (f", true peak {peak:.1f} dBFS" if peak is not None else ""))
    else:
        lines.append("No audio in the finished video.")
    size = after["bytes"] / 1024 / 1024
    lines.append(f"Picture: {after['width']}x{after['height']}, {after['fps']:.3g} fps, {after['frames']} frames, "
                 f"{size:.1f} MB" if after["fps"] else f"File: {size:.1f} MB")
    out = a.out or str(Path(a.finished).with_name(Path(a.finished).stem + "-report.txt"))
    if os.path.exists(out) and not a.out:
        stem, n = Path(out).with_suffix(""), 2
        while os.path.exists(f"{stem}-v{n}.txt"):
            n += 1
        out = f"{stem}-v{n}.txt"
    text = "\n".join(lines) + "\n"
    open(out, "w", encoding="utf-8").write(text)
    print(text + f"Saved to {out}")


if __name__ == "__main__":
    main()
