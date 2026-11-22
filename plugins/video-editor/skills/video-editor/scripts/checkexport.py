"""Checks a finished export for what a viewer would notice and nobody looked for, before it is delivered.

  python -I checkexport.py <export.mp4> [--expect cut-transcript.json --heard export-transcript.json]

FAIL (exit 1: fix it, export again, check again before telling the user it's done):
  - black frames in the middle of the video (a missing piece of picture), anywhere but its first and last half second;
  - single-frame flashes: one frame unlike the frames on both sides of it, which match each other. A cut that leaves
    one stray frame of another take looks exactly like this, and nobody sees it in a contact sheet;
  - picture and sound of different lengths (more than 0.1 s): the sound drifts or stops before the end.
WARN (tell the user in one line, and fix it when it's cheap):
  - digital silence (the sound is exactly zero) for 0.25 s or more inside the video: it sounds like the sound cut out,
    because a real room is never silent. Leave a little room tone in pauses instead of muting them;
  - colour tags missing (primaries, transfer, matrix): some players then guess, and faces look darker and redder;
  - with --expect and --heard (the cut voice's transcript and a transcript of the export's own sound, both in
    transcribe.py's format): words that were in the cut but aren't heard in the export, usually a word clipped at a cut.

Writes <export>-check.txt next to the export. Needs numpy and FFmpeg (the speech Python has numpy).
"""
import argparse
import difflib
import json
import os
import subprocess
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

SMALL = (64, 36)      # frames are compared at this size: enough to see a flash, fast for a long video
EDGE = 0.5            # seconds at each end where black is allowed (a fade in or out)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"Can't read {path}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def frames_small(path):
    """Every frame as a small grey picture: (array frames x h x w, fps)."""
    info = probe(path)
    video = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    if video is None:
        sys.exit(f"{path} has no picture.")
    num, den = (int(x) for x in video.get("avg_frame_rate", "25/1").split("/"))
    fps = num / den if den and num else 25.0
    w, h = SMALL
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h}", "-pix_fmt", "gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32), fps


def runs(indexes):
    out = []
    for i in indexes:
        if out and i == out[-1][1] + 1:
            out[-1] = (out[-1][0], i)
        else:
            out.append((i, i))
    return out


def black_frames(frames, fps):
    """Runs of black frames (first frame, last frame) outside the first and last EDGE seconds."""
    if not len(frames):
        return []
    means = frames.reshape(len(frames), -1).mean(axis=1)
    spread = frames.reshape(len(frames), -1).std(axis=1)
    black = np.where((means < 24) & (spread < 6))[0]
    edge = int(round(EDGE * fps))
    return [r for r in runs(black.tolist()) if r[0] >= edge and r[1] < len(frames) - edge]


def flashes(frames):
    """Frames unlike both neighbours while the neighbours match each other: a stray single frame."""
    if len(frames) < 3:
        return []
    flat = frames.reshape(len(frames), -1)
    before = np.abs(flat[1:-1] - flat[:-2]).mean(axis=1)
    after = np.abs(flat[1:-1] - flat[2:]).mean(axis=1)
    across = np.abs(flat[2:] - flat[:-2]).mean(axis=1)
    typical = np.median(np.abs(np.diff(flat, axis=0)).mean(axis=1))
    big = max(12.0, typical * 6)
    # The neighbours must be at least 4 times closer to each other than to the frame between them. A fixed limit
    # on `across` missed a white flash on a small video, where ordinary motion moved the neighbours 6 apart.
    hits = np.where((before > big) & (after > big) & (across * 4 < np.minimum(before, after)))[0] + 1
    return hits.tolist()


def stream_lengths(info):
    """(picture seconds, sound seconds or None)."""
    def length(kind):
        s = next((s for s in info["streams"] if s.get("codec_type") == kind), None)
        if s is None:
            return None
        if s.get("duration"):
            return float(s["duration"])
        return float(info.get("format", {}).get("duration", 0) or 0)
    return length("video"), length("audio")


def digital_silence(path, rate=16000, shortest=0.25):
    """Stretches (start, end) seconds where the sound is exactly zero for `shortest` seconds or more, inside the
    video (not in its first and last EDGE seconds)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16)
    if not len(x):
        return []
    zero = np.abs(x.astype(np.int32)) <= 1
    out, start = [], None
    for i in np.flatnonzero(np.diff(np.concatenate([[0], zero.astype(np.int8), [0]]))):
        if start is None:
            start = i
        else:
            a, b = start / rate, i / rate
            if b - a >= shortest and a >= EDGE and b <= len(x) / rate - EDGE:
                out.append((round(a, 2), round(b, 2)))
            start = None
    return out


def colour_tags(info):
    video = next((s for s in info["streams"] if s.get("codec_type") == "video"), {})
    missing = [name for key, name in (("color_primaries", "primaries"), ("color_transfer", "transfer"),
                                      ("color_space", "matrix")) if video.get(key) in (None, "", "unknown")]
    return missing


def words_of(transcript):
    return [(w["start"], w["word"].strip()) for s in transcript.get("segments", []) for w in s.get("words", [])]


def norm(word):
    return "".join(c for c in word.lower() if c.isalnum())


def missing_words(expect, heard):
    """Words in the cut's transcript that the export's transcript doesn't have, with their time in the cut."""
    a, b = words_of(expect), words_of(heard)
    lost = []
    for op, i1, i2, _, _ in difflib.SequenceMatcher(None, [norm(w) for _, w in a], [norm(w) for _, w in b],
                                                    autojunk=False).get_opcodes():
        if op in ("delete", "replace"):
            lost.append((a[i1][0], " ".join(w for _, w in a[i1:i2])))
    return lost


def stamp(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export")
    ap.add_argument("--expect", help="transcript of the cut voice (what should be heard)")
    ap.add_argument("--heard", help="transcript of the export's own sound")
    a = ap.parse_args()
    info = probe(a.export)
    frames, fps = frames_small(a.export)
    fails, warns = [], []
    for first, last in black_frames(frames, fps):
        fails.append(f"black picture from {stamp(first / fps)} to {stamp((last + 1) / fps)} ({last - first + 1} frames)")
    for n in flashes(frames):
        fails.append(f"a single-frame flash at {stamp(n / fps)} (frame {n}): a stray frame left by a cut?")
    picture, sound = stream_lengths(info)
    if sound is None:
        warns.append("no sound at all")
    elif picture and abs(picture - sound) > 0.1:
        fails.append(f"picture {picture:.2f} s but sound {sound:.2f} s: they must end together")
    if sound is not None:
        for start, end in digital_silence(a.export):
            warns.append(f"digital silence from {stamp(start)} to {stamp(end)}: sounds like the sound cut out")
    missing = colour_tags(info)
    if missing:
        warns.append(f"colour tags missing ({', '.join(missing)}): end the export's filter chain with "
                     "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709 (FFmpeg 7+ ignores -color_trc)")
    if a.expect and a.heard:
        with open(a.expect, encoding="utf-8") as f:
            expect = json.load(f)
        with open(a.heard, encoding="utf-8") as f:
            heard = json.load(f)
        for t, words in missing_words(expect, heard):
            warns.append(f'not heard in the export: "{words}" (at {stamp(t)} in the cut): clipped at a cut?')
    lines = [f"Check of {os.path.basename(a.export)}: {len(frames)} frames at {fps:g} fps, "
             f"{picture or 0:.2f} s of picture" + (f", {sound:.2f} s of sound" if sound else "")]
    lines += [f"FAIL: {x}" for x in fails] + [f"WARN: {x}" for x in warns]
    lines.append("Result: " + ("FAIL: fix these and export again before delivering" if fails else
                               "OK" + (", with the warnings above" if warns else "")))
    report = "\n".join(lines)
    print(report)
    with open(os.path.splitext(a.export)[0] + "-check.txt", "w", encoding="utf-8") as f:
        f.write(report + "\n")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
