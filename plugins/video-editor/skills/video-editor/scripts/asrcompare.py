"""Compares Whisper and Parakeet on the user's own voice, to decide which one transcribes their videos.

  <speech python> -I asrcompare.py <audio-or-video> [--start 0] [--seconds 120] [--language es] [--model medium]

Both engines transcribe the same piece (two minutes by default; pick one with pauses, fillers and the brand's
names). It prints, for each:
  - how long it took, and how many times faster than the audio that is;
  - its text, and the words where the two disagree, with the time (read them: the one that's right is the better);
  - the fillers it wrote ("eh", "em", "mmm"...): the filler hunt needs an engine that writes them;
  - how close its word starts are to where speech really starts after each pause, measured on the sound itself:
    cuts are made at those times, so this is the number that matters most for the edit.
Nothing is changed. Needs faster-whisper and onnx-asr in the same Python (asr.py has the details).
"""
import argparse
import difflib
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asr  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# Sounds only: "este" and "o sea" are fillers in Spanish but also ordinary words ("y este habla"), so counting them
# here would mislead; the filler hunt (references/fillers.md) judges those in context.
FILLERS = {"eh", "em", "ehm", "emm", "mm", "mmm", "hmm", "um", "uh", "ah", "aja"}


def norm(word):
    return "".join(c for c in word.lower() if c.isalnum())


def speech_starts(audio, rate=16000, gap=0.35, level=None):
    """Where speech starts again after a pause of at least `gap` seconds, from the loudness every 10 ms. The level
    is set from the recording itself (a tenth of its loud parts), so room noise doesn't count as speech."""
    frame = rate // 100
    m = len(audio) // frame
    if m == 0:
        return []
    loudness = np.sqrt((audio[:m * frame].reshape(m, frame) ** 2).mean(axis=1))
    level = level if level is not None else max(np.percentile(loudness, 95) * 0.1, 1e-4)
    starts, quiet = [], int(gap * 100)
    for i, loud in enumerate(loudness > level):
        if loud and quiet >= int(gap * 100):
            starts.append(i / 100)
        quiet = 0 if loud else quiet + 1
    return starts


def start_error(word_starts, real_starts, reach=0.6):
    """For each real start of speech, how far the nearest word start is (seconds); starts with no word within
    `reach` are left out (a breath or a click, not a word)."""
    errors = []
    for t in real_starts:
        if word_starts:
            nearest = min(word_starts, key=lambda w: abs(w - t))
            if abs(nearest - t) <= reach:
                errors.append(nearest - t)
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--language", default="es")
    ap.add_argument("--model", default="medium", help="the Whisper model to compare (default medium, as transcribe.py)")
    a = ap.parse_args()
    audio = asr.load_audio(a.audio)[int(a.start * 16000):int((a.start + a.seconds) * 16000)]
    length = len(audio) / 16000
    real = speech_starts(audio)
    results = {}
    for name, engine, model in (("Whisper " + a.model, "faster", a.model), ("Parakeet", "parakeet", None)):
        loaded = asr.load(model, engine)
        began = time.time()
        text, words = asr.transcribe(loaded, engine, audio, a.language, words=True)
        took = time.time() - began
        results[name] = (text, words, took)
    print(f"{length:.0f} s of {os.path.basename(a.audio)} from {a.start:.0f} s, {len(real)} starts of speech after a pause.\n")
    names = list(results)
    for name in names:
        text, words, took = results[name]
        errors = start_error([w[0] for w in words], real)
        fillers = [w[2] for w in words if norm(w[2]) in FILLERS]
        print(f"{name}: {took:.1f} s ({length / took:.0f}x faster than the audio), {len(words)} words")
        if errors:
            mean = np.mean(np.abs(errors))
            print(f"  word starts vs real starts of speech: {mean:.2f} s off on average, worst {max(np.abs(errors)):.2f} s, "
                  f"{sum(abs(e) > 0.1 for e in errors)} of {len(errors)} more than 0.1 s off")
        print(f"  fillers written: {len(fillers)} {fillers[:12]}")
        print(f"  text: {text[:400]}{'...' if len(text) > 400 else ''}\n")
    (ta, wa, _), (tb, wb, _) = results[names[0]], results[names[1]]
    a_words, b_words = [norm(w[2]) for w in wa], [norm(w[2]) for w in wb]
    shown = 0
    print("Where they disagree (time, " + names[0] + " | " + names[1] + "):")
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a_words, b_words, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        when = wa[i1][0] if i1 < len(wa) else (wb[j1][0] if j1 < len(wb) else 0)
        left = " ".join(w[2] for w in wa[i1:i2]) or "-"
        right = " ".join(w[2] for w in wb[j1:j2]) or "-"
        print(f"  {a.start + when:7.1f} s  {left}  |  {right}")
        shown += 1
        if shown >= 25:
            print("  ...")
            break
    if not shown:
        print("  nowhere: the same words.")
    print("\nThe better one: the right words where they disagree, fillers written, and word starts closest to the real "
          "ones. Save the choice in my-setup.md as `Transcription engine:`.")


if __name__ == "__main__":
    main()
