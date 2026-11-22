"""Soft key clicks for a typewriter title, timed to the same letters as TitleCard's "typewriter" animation.

  python -I typing.py --line "Mi rutina de" --line "5 minutos" [--lps 16] [--start 0.13] [--every 2] [--out typing.wav]

Give the title's lines and speed exactly as in its props (lettersPerSecond, typingStart). Every character, spaces
included, takes 1/lps seconds, as in the template; a click plays on every --every-th letter (2 by default: one click
per letter sounds busy), never on a space. Each click is a short, bright tick generated here, so it is free to use.
The wav starts at the title's first frame: mix it like the other sound effects (references/sound.md), delayed to the
title's start, at about 0.3 to 0.45 under the voice. Standard library only.
"""
import argparse
import math
import random
import struct
import sys
import wave

sys.stdout.reconfigure(encoding="utf-8")


def click_times(lines, lps, start, every):
    times, index, letter = [], 0, 0
    for line in lines:
        for ch in line:
            if ch != " ":
                if letter % every == 0:
                    times.append(start + index / lps)
                letter += 1
            index += 1
    return times, start + index / lps


def render_clicks(times, seconds, volume=0.5, rate=48000):
    """Mono samples (floats, -1 to 1), `seconds` long, with a soft key click at each time. Also used by the AI chat
    window (chatwindow.py), so its typing sounds the same as a typewriter title's."""
    samples = [0.0] * int(seconds * rate)
    rng = random.Random(7)
    length = int(0.018 * rate)
    for t in times:
        begin = int(t * rate)
        gain = volume * (0.8 + 0.4 * rng.random())
        previous = 0.0
        for k in range(length):
            if begin + k >= len(samples):
                break
            noise = rng.gauss(0, 1) * math.exp(-9 * k / length)
            samples[begin + k] += gain * 0.36 * (noise - previous)  # a difference: bright tick, no low thump
            previous = noise
    return samples


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--line", action="append", required=True, help="one line of the title; repeat for each line")
    ap.add_argument("--lps", type=float, default=16.0, help="letters per second (lettersPerSecond)")
    ap.add_argument("--start", type=float, default=0.13, help="seconds before the first letter (typingStart)")
    ap.add_argument("--every", type=int, default=2, help="a click every N letters")
    ap.add_argument("--volume", type=float, default=0.5)
    ap.add_argument("--out", default="typing.wav")
    a = ap.parse_args()
    times, end = click_times(a.line, a.lps, a.start, max(1, a.every))
    rate = 48000
    samples = render_clicks(times, end + 0.3, a.volume, rate)
    out = wave.open(a.out, "wb")
    out.setnchannels(1)
    out.setsampwidth(2)
    out.setframerate(rate)
    out.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767)) for v in samples))
    out.close()
    print(f"Wrote {a.out}: {len(times)} clicks, typing ends at {end:.2f} s of the title.")


if __name__ == "__main__":
    main()
