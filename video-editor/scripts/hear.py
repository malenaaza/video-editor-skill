"""Transcribes short pieces of a recording on their own, to settle what is said where.

  python -I hear.py --language es [--wav voice.wav] [--engine openai|faster] [--model small] a b [a b ...]

Each piece (a to b, seconds) is transcribed alone, with the filler prompt for the language and with
no text carried over from before, so a filler, a repeat or a stretched word shows up as it sounds.
Use it on a hit from hunt_fillers.py or heldsounds.py, on a word Whisper stretched over 0.8 s, or on
a cut you are unsure of. `--engine faster --model medium` hears slurred words that `small` mishears.
Prints the text and every word with its time. Any audio or video file works for --wav.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asr  # noqa: E402
from filler_prompts import prompt_for  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--language", required=True)
ap.add_argument("--wav", default="voice.wav")
ap.add_argument("--engine", choices=["openai", "faster"], default="openai")
ap.add_argument("--model", default="small")
ap.add_argument("times", type=float, nargs="+", help="start and end of each piece, in pairs")
a = ap.parse_args()
if len(a.times) % 2:
    sys.exit("Give the pieces as pairs of start and end times.")
x = asr.load_audio(a.wav)
model = asr.load(a.model, a.engine)
for start, end in zip(a.times[::2], a.times[1::2]):
    text, found = asr.transcribe(model, a.engine, x[int(start * 16000):int(end * 16000)], a.language,
                                 prompt_for(a.language), words=True)
    print(f"{start:.2f}-{end:.2f}: {text!r}\n      " + " ".join(f"{w}[{start + s:.2f}-{start + e:.2f}]" for s, e, w in found), flush=True)
