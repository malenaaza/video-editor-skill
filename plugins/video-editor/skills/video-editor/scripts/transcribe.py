# Word-level transcription. Drop-in replacement for:
#   whisper <file> --model medium --word_timestamps True --output_format json --output_dir <dir>
# Writes <dir>/<file stem>.json in the same shape as openai-whisper (text, language, segments[].words[]), whichever
# engine made it, so everything after it works the same.
#
# Usage: python -I transcribe.py <audio-or-video> <output_dir> [--engine whisper|parakeet] [--model medium]
#                                [--language es] [--initial_prompt "..."] [--device auto|cpu|cuda]
#
# whisper (default): faster-whisper. On the CPU it was about 2.5x faster than openai-whisper medium, with the same
# words and word times within 20 ms. With an NVIDIA GPU (--device auto finds it) it is much faster again.
# Word fixes: with whisper and no --initial_prompt, the right spellings in the user's saved list (wordfixes.py) are
# given to the model as a hint, so names it knows come out right; Parakeet ignores hints, so there the list only
# corrects the captions afterwards.
# parakeet: NVIDIA Parakeet v3 through onnx-asr (see asr.py): about 5x faster than faster-whisper medium on the CPU
# in a first test, and it finds the language itself (--language, --initial_prompt and --model are ignored). Use it
# only after asrcompare.py has shown it hears this user's voice as well; its segments are its sentences.
import argparse, json, os, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wordfixes
sys.stdout.reconfigure(encoding="utf-8")
p = argparse.ArgumentParser()
p.add_argument("input"); p.add_argument("output_dir")
p.add_argument("--engine", default="whisper", choices=["whisper", "parakeet"])
p.add_argument("--model", default="medium"); p.add_argument("--language", default=None)
p.add_argument("--initial_prompt", default=None)
p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
a = p.parse_args()

saved = wordfixes.read()
a.initial_prompt = wordfixes.hint_for(a.engine, a.initial_prompt, saved)
if a.engine == "parakeet" and saved:
    print(f"Parakeet takes no vocabulary hint: your {len(saved)} saved word fixes will correct the captions instead.")
elif a.initial_prompt and saved and a.initial_prompt == wordfixes.vocabulary(saved):
    print(f"Whisper hint from your saved word fixes: {a.initial_prompt[:80]}")

# Decode with ffmpeg like openai-whisper does (some PyAV versions break faster-whisper's own decoder).
pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", a.input, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def sentences(words):
    """Parakeet gives words, not segments: a segment per sentence (ending in . ? ! or …), like Whisper's."""
    segs, current = [], []
    for w in words:
        current.append(w)
        if w[2].endswith((".", "?", "!", "…")):
            segs.append(current)
            current = []
    if current:
        segs.append(current)
    return segs


out = {"text": "", "segments": []}
if a.engine == "parakeet":
    import asr
    model = asr.load(None, "parakeet")
    print("Running Parakeet", flush=True)
    _, words = asr.transcribe(model, "parakeet", audio, None, words=True)
    for i, seg in enumerate(sentences(words)):
        text = " " + " ".join(w[2] for w in seg)
        out["segments"].append({"id": i, "start": seg[0][0], "end": seg[-1][1], "text": text,
            "words": [{"word": " " + w[2], "start": w[0], "end": w[1], "probability": None} for w in seg]})
        print(f"[{seg[0][0]:7.2f} --> {seg[-1][1]:7.2f}]{text}", flush=True)
    out["language"] = a.language or "auto"
else:
    from faster_whisper import WhisperModel
    device = a.device
    if device == "auto":
        try:
            import ctranslate2
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    if device == "cuda":
        model = WhisperModel(a.model, device="cuda", compute_type="float16")
    else:
        model = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    print(f"Running on {device}", flush=True)
    # beam_size=1 = greedy, matching openai-whisper's default decoding.
    segs, info = model.transcribe(audio, language=a.language, initial_prompt=a.initial_prompt,
                                  word_timestamps=True, beam_size=1)
    for i, s in enumerate(segs):
        out["segments"].append({"id": i, "start": s.start, "end": s.end, "text": s.text,
            "words": [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability} for w in s.words]})
        print(f"[{s.start:7.2f} --> {s.end:7.2f}]{s.text}", flush=True)
    out["language"] = info.language
out["text"] = "".join(s["text"] for s in out["segments"])
os.makedirs(a.output_dir, exist_ok=True)
dst = os.path.join(a.output_dir, os.path.splitext(os.path.basename(a.input))[0] + ".json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
print(f"Detected language: {out['language']}\nWrote {dst}")
