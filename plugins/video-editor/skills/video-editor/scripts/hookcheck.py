"""Checks the first seconds of a finished video: the part that decides whether anyone keeps watching.

  python -I hookcheck.py <export.mp4> --captions captions.json [--sfx-mix sfx-mix.txt] [--title-at 0.0]

captions.json is the finished cut's captions (captions.py), so its times are the export's. It checks:
FAIL (exit 1):
  - the first frame is black or blank: in a feed the first frame is what people see before it plays;
  - the first word is clipped: there is already speech in the first 30 ms, or the first word starts at 0.00;
WARN:
  - more than 0.5 s before the first word: on Reels, TikTok and Shorts people scroll away during silence;
  - a sound effect (an adelay in sfx-mix.txt) lands on the first word: the first word must be heard clean;
  - nothing on screen says anything in the first 1.5 s: most people start with the sound off, so a caption or the
    title (--title-at: when it appears, in seconds) has to be there by then;
and prints the words said in the first 3 seconds, to judge with the user: they must be the promise or the question,
not a greeting (references/script.md, The opening). Writes <export>-hook.txt. Needs numpy and FFmpeg.
"""
import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

QUIET_START = 0.5     # seconds of silence allowed before the first word
TEXT_BY = 1.5         # seconds by which something must be written on screen


def first_frame(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-vf", "scale=96:-2",
                          "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).astype(np.float32)


def opening_sound(path, seconds=0.5, rate=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-t", str(seconds), "-ac", "1",
                          "-ar", str(rate), "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def caption_words(captions):
    return [(float(s), float(e), str(t)) for c in captions for s, e, t in c.get("words", [])]


def sfx_times(path):
    """Start times (seconds) of the effects in an FFmpeg mix file, from its adelay=<ms>|<ms> values."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return sorted(int(m) / 1000 for m in re.findall(r"adelay=(\d+)", text))


def check(frame, sound, words, captions, sfx=(), title_at=None, rate=16000):
    """(fails, warns, opening words)."""
    fails, warns = [], []
    if len(frame) and (frame.mean() < 24 or frame.std() < 4):
        fails.append("the first frame is black or blank: open on a meaningful picture (the face, the product)")
    if not words:
        warns.append("no words in the captions: nothing to check the opening against")
        return fails, warns, ""
    first_start, first_end, first_word = words[0]
    head = sound[:int(0.03 * rate)]
    speech_level = np.percentile(np.abs(sound), 99) if len(sound) else 0
    if first_start <= 0.0 or (len(head) and speech_level > 0.01 and np.abs(head).max() > speech_level * 0.5):
        fails.append(f'the first word ("{first_word}") is clipped: speech is already going at the first frame; keep '
                     "a few frames before it")
    elif first_start > QUIET_START:
        warns.append(f"{first_start:.2f} s before the first word: start on the word (under {QUIET_START} s), people "
                     "scroll away during silence")
    for t in sfx:
        if first_start - 0.15 <= t <= first_end:
            warns.append(f'a sound effect at {t:.2f} s lands on the first word ("{first_word}"): move it off')
    first_caption = min((float(c["start"]) for c in captions if "start" in c), default=None)
    shown = [t for t in (first_caption, title_at) if t is not None]
    if not shown or min(shown) > TEXT_BY:
        warns.append(f"nothing written on screen in the first {TEXT_BY} s: most people watch the start muted, so a "
                     "caption or the title must say what the video is about by then")
    opening = " ".join(w for s, _, w in words if s < 3.0)
    return fails, warns, opening


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export")
    ap.add_argument("--captions", required=True, help="captions.json of the finished cut")
    ap.add_argument("--sfx-mix", help="the sound effects mix file (its adelay values are the effects' times)")
    ap.add_argument("--title-at", type=float, help="when the title appears, in seconds (if there is one)")
    a = ap.parse_args()
    with open(a.captions, encoding="utf-8") as f:
        captions = json.load(f)
    fails, warns, opening = check(first_frame(a.export), opening_sound(a.export), caption_words(captions), captions,
                                  sfx_times(a.sfx_mix) if a.sfx_mix else (), a.title_at)
    lines = [f"Hook check of {os.path.basename(a.export)}:"]
    lines += [f"FAIL: {x}" for x in fails] + [f"WARN: {x}" for x in warns]
    lines.append(f'The first 3 seconds say: "{opening}"')
    lines.append("Is that the promise or the question, said within the first second, not a greeting? Ask the user.")
    lines.append("Result: " + ("FAIL: fix and export again" if fails else "OK" + (", with the warnings above" if warns else "")))
    report = "\n".join(lines)
    print(report)
    with open(os.path.splitext(a.export)[0] + "-hook.txt", "w", encoding="utf-8") as f:
        f.write(report + "\n")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
