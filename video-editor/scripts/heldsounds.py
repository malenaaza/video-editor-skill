"""Strict search for truly held sounds ("deeee", "eeeh", a hum) in a finished voice.

Ported from a five-clip edit, where a first detector (spectral-shape correlation) also matched strings
of similar vowels with soft consonants ("el de", "muy muy") and 12 of 27 cuts clipped a word. This
one asks for much more: the spectrum, in 250 Hz bands up to 5 kHz, must change by less than --step dB
(mean over the bands) over 30 ms, for --min seconds or more, while the sound is within 16 dB of the
voice's loud level. Speech keeps changing its spectrum from syllable to syllable; a held sound does
not. With 0.30 s and 3.2 dB it clipped nothing.

  python -I heldsounds.py voice.wav [--words cut.json] [--min 0.30] [--step 3.2]

--words is a Whisper json of the same audio (its times in the same clock): each candidate is printed
with the words around it, so you can see at once whether it is a filler or the middle of a word.
Candidates are only candidates. Before cutting one, listen with hear.py, and after cutting, run
checkcuts.py: a held sound that is really a long word clips it. The last lines are drops.txt lines
for drops.py (V = shorten a held sound).
Needs numpy and FFmpeg. Any audio or video file works; FFmpeg converts it to 16 kHz mono.
"""
import argparse
import json
import subprocess
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("audio")
ap.add_argument("--words", help="Whisper json of the same audio, for context")
ap.add_argument("--min", type=float, default=0.30, help="shortest held sound, seconds")
ap.add_argument("--step", type=float, default=3.2, help="largest mean spectrum change over 30 ms, dB (lower = stricter)")
a = ap.parse_args()

pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", a.audio, "-vn", "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
sr = 16000
N, H = 512, 160  # 32 ms windows every 10 ms
win = np.hanning(N)
freqs = np.fft.rfftfreq(N, 1 / sr)
edges = np.arange(250, 5001, 250.0)
n = (len(x) - N) // H
if n < 10:
    sys.exit("The audio is too short.")
lvl = np.zeros(n)
shape = np.zeros((n, len(edges) - 1))
B = 20000
for c in range(0, n, B):
    frames = np.stack([x[i * H:i * H + N] * win for i in range(c, min(c + B, n))])
    spectrum = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    bands = np.stack([spectrum[:, (freqs >= p) & (freqs < q)].sum(axis=1) for p, q in zip(edges[:-1], edges[1:])], axis=1)
    lb = 10 * np.log10(bands + 1e-10)
    lvl[c:c + len(frames)] = 10 * np.log10(spectrum.sum(axis=1) / N + 1e-10)
    shape[c:c + len(frames)] = lb - lb.mean(axis=1, keepdims=True)
step = np.full(n, 99.0)
step[3:] = np.abs(shape[3:] - shape[:-3]).mean(axis=1)  # change over 30 ms
loud = np.percentile(lvl, 90)
ok = (step < a.step) & (lvl > loud - 16)
runs, i = [], 0
while i < n:
    if ok[i]:
        j = i
        while j < n and (ok[j] or (j + 1 < n and ok[j + 1] and step[j] < a.step + 1.0)):
            j += 1
        start, end = (i - 3) * H / sr, j * H / sr + N / sr / 2  # the first frame compared starts 30 ms earlier
        if end - start >= a.min:
            runs.append((max(start, 0.0), end, float(np.median(step[i:j])), float(lvl[i:j].max() - lvl[i:j].min())))
        i = j
    else:
        i += 1

words = []
if a.words:
    for seg in json.load(open(a.words, encoding="utf-8")).get("segments", []):
        for w in seg.get("words", []):
            words.append((w["start"], w["end"], w["word"].strip()))
for start, end, med, rng in runs:
    context = " ".join(w[2] + (f"[{w[0]:.2f}-{w[1]:.2f}]" if w[1] > start and w[0] < end else "")
                       for w in words if w[1] > start - 0.8 and w[0] < end + 0.8)
    print(f"{start:7.2f}-{end:7.2f} {end - start:.2f}s step {med:.1f} level range {rng:.0f} dB | {context}")
print(len(runs), f"held sounds of {a.min} s or more")
if runs:
    print("drops.txt candidates (check each with hear.py first):")
    for start, end, *_ in runs:
        print(f"V {start:.2f} {end:.2f} held sound")
