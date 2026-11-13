"""Filler pass: transcribe with the `small` model and a prompt that invites fillers.

Usage: python -I fillers.py --language es <audio1> <out1.json> [<audio2> <out2.json> ...]

Uses openai-whisper on purpose: in testing, faster-whisper `small` was 2.6x faster
but missed a filler that openai-whisper caught.
"""
import argparse
import json
import os
import sys

import whisper

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filler_prompts import prompt_for  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
p = argparse.ArgumentParser()
p.add_argument("--language", required=True, help="language code, e.g. es, en")
p.add_argument("pairs", nargs="+", help="audio and output json, in pairs")
a = p.parse_args()
if len(a.pairs) % 2:
    sys.exit("Give the files in pairs: <audio> <out.json> ...")

model = whisper.load_model("small")
for path, out in zip(a.pairs[::2], a.pairs[1::2]):
    r = model.transcribe(path, language=a.language, word_timestamps=True, fp16=False,
                         initial_prompt=prompt_for(a.language))
    json.dump(r, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("==", path)
    for s in r["segments"]:
        print(" ".join(f"{w['word'].strip()}@{w['start']:.2f}-{w['end']:.2f}" for w in s["words"]))
