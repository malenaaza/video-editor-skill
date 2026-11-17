"""Check proposed filler cuts: what each cut removes, and how the join reads.

Usage (from the project folder): python -I checkcuts.py --language es [--audio audio.wav] [--engine faster --model medium] a1 b1 a2 b2 ...
(a, b = start and end of each cut, in source seconds)

For each cut it prints what the removed piece says (it should be only the filler) and
what the 2 s before and after say once joined (every word should be whole).
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asr  # noqa: E402
from filler_prompts import prompt_for  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
p = argparse.ArgumentParser()
p.add_argument("--language", required=True)
p.add_argument("--audio", default="audio.wav")
p.add_argument("--engine", choices=["openai", "faster"], default="openai")
p.add_argument("--model", default="small", help="small mishears slurred words: try --engine faster --model medium")
p.add_argument("times", nargs="+", type=float)
a = p.parse_args()
if len(a.times) % 2:
    sys.exit("Give the cuts as pairs of start and end times.")

model = asr.load(a.model, a.engine)
tmp = Path(tempfile.mkdtemp())


def text(path):
    return asr.transcribe(model, a.engine, asr.load_audio(path), a.language, prompt_for(a.language))[0]


for start, end in zip(a.times[::2], a.times[1::2]):
    removed, joined = tmp / "removed.wav", tmp / "joined.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start}", "-to", f"{end}", "-i", a.audio, str(removed)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.audio, "-filter_complex",
                    f"[0:a]atrim={max(start - 2.0, 0)}:{start},asetpts=PTS-STARTPTS,afade=t=out:st=1.988:d=0.012[x];"
                    f"[0:a]atrim={end}:{end + 2.0},asetpts=PTS-STARTPTS,afade=t=in:d=0.012[y];[x][y]concat=n=2:v=0:a=1[o]",
                    "-map", "[o]", str(joined)], check=True)
    print(f"{start:.2f}-{end:.2f}  removed: {text(removed)!r}\n             joined:  {text(joined)!r}")
