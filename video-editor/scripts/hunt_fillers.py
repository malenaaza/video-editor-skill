"""Finds fillers that the whole-file passes miss: "ehh" and hums glued onto a word.

Usage: python -I hunt_fillers.py --language es <audio.wav> [out.json]

Whisper merges a filler that sits right against a word into that word, so even the small-model
filler pass (fillers.py) can come back clean while the user still hears "ehhh". This pass
transcribes short overlapping windows (6 s, every 3 s) with the filler prompt and without
carrying text over from the previous window, which makes the model write fillers it would
otherwise smooth over. It lists every filler it hears and every word longer than 0.6 s
(a stretched word often hides a filler or a hum), with times in the input file.

Each hit is only a candidate. Read the level map around it (a filler is a flat, steady stretch),
then test the cut: the removed piece alone must transcribe as only the filler, and the 2 s
before and after, joined, must keep every word whole (checkcuts.py does this).
Needs openai-whisper (the speech environment). Takes any audio or video file: FFmpeg converts it
to the 16 kHz mono that Whisper expects.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
import whisper

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filler_prompts import prompt_for  # noqa: E402

FILLERS = {"eh", "ehh", "ehhh", "eeh", "eeeh", "em", "emm", "mm", "mmm", "hmm", "um", "umm", "uh", "uhh", "ah", "ahh"}

p = argparse.ArgumentParser()
p.add_argument("--language", required=True)
p.add_argument("audio")
p.add_argument("out", nargs="?", default="hunt.json")
p.add_argument("--model", default="small")
a = p.parse_args()

sys.stdout.reconfigure(encoding="utf-8")
sr = 16000
pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", a.audio, "-vn", "-f", "s16le", "-ac", "1",
                      "-ar", str(sr), "-"], capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
model = whisper.load_model(a.model)
prompt = prompt_for(a.language)

hits = []
for start in np.arange(0, len(audio) / sr, 3.0):
    clip = audio[int(start * sr):int((start + 6) * sr)]
    if len(clip) < sr:
        break
    result = model.transcribe(clip, language=a.language, word_timestamps=True, fp16=False,
                              initial_prompt=prompt, condition_on_previous_text=False)
    for seg in result["segments"]:
        for word in seg["words"]:
            text = word["word"].strip().lower().strip(".,;:!?¿¡…")
            long_word = word["end"] - word["start"] > 0.6
            if text in FILLERS or long_word:
                hits.append([round(start + word["start"], 2), round(start + word["end"], 2),
                             word["word"].strip(), "filler" if text in FILLERS else "long word"])

merged = []
for h in sorted(hits):
    if not merged or h[0] - merged[-1][0] > 0.3:
        merged.append(h)
for h in merged:
    print(f"{h[0]:8.2f}-{h[1]:8.2f}  {h[3]:9}  {h[2]}")
json.dump(merged, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(merged), "candidates, saved to", a.out)
