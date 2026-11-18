# Word-level transcription with faster-whisper. Drop-in replacement for:
#   whisper <file> --model medium --word_timestamps True --output_format json --output_dir <dir>
# Writes <dir>/<file stem>.json in the same shape as openai-whisper (text, language, segments[].words[]).
#
# Usage: python -I transcribe.py <audio-or-video> <output_dir> [--model medium] [--language es]
#                                [--initial_prompt "..."] [--device auto|cpu|cuda]
#
# On the CPU it was about 2.5x faster than openai-whisper medium, with the same words and
# word times within 20 ms. With an NVIDIA GPU (--device auto finds it) it is much faster again.
import argparse, json, os, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

sys.stdout.reconfigure(encoding="utf-8")
p = argparse.ArgumentParser()
p.add_argument("input"); p.add_argument("output_dir")
p.add_argument("--model", default="medium"); p.add_argument("--language", default=None)
p.add_argument("--initial_prompt", default=None)
p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
a = p.parse_args()

# Decode with ffmpeg like openai-whisper does (some PyAV versions break faster-whisper's own decoder).
pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", a.input, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0

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
out = {"text": "", "segments": [], "language": info.language}
for i, s in enumerate(segs):
    out["segments"].append({"id": i, "start": s.start, "end": s.end, "text": s.text,
        "words": [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability} for w in s.words]})
    print(f"[{s.start:7.2f} --> {s.end:7.2f}]{s.text}", flush=True)
out["text"] = "".join(s["text"] for s in out["segments"])
os.makedirs(a.output_dir, exist_ok=True)
dst = os.path.join(a.output_dir, os.path.splitext(os.path.basename(a.input))[0] + ".json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
print(f"Detected language: {info.language}\nWrote {dst}")
