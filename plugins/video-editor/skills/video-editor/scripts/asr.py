"""Shared speech-to-text helper: one interface for openai-whisper, faster-whisper and NVIDIA Parakeet.

The scripts that listen to short pieces of audio (hear.py, checkcuts.py, hunt_fillers.py) take
--engine and --model. Findings from real edits:
- openai-whisper `small` caught a filler that faster-whisper `small` missed (fillers.py keeps it).
- `small` mishears slurred words; `medium` with faster-whisper (int8 on CPU) settles them.

Parakeet (engine "parakeet": NVIDIA's parakeet-tdt-0.6b-v3 through onnx-asr, `pip install "onnx-asr[cpu,hub]"`;
its 640 MB int8 model downloads on first use) understands 25 European languages and finds the language itself, so
--language and prompts are ignored. On a 16 s Spanish test (a synthetic voice, CPU only) it took 1.4 s against
6.7 s for faster-whisper medium, with the same text but for one word each. It wrote "MMM" but dropped an "eh",
as Whisper did, and its word starts were within 0.03 s at three sentence starts but 0.25 s early at three others
(Whisper: 0.02 to 0.13 s late at all six). Try it on the user's own voice with asrcompare.py before relying on it.
"""
import os

import numpy as np


def load_audio(path):
    """Any audio or video file -> float32 mono at 16 kHz (decoded by FFmpeg)."""
    import subprocess

    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768


PARAKEET = "nemo-parakeet-tdt-0.6b-v3"


def load(model, engine):
    if engine == "parakeet":
        try:
            import onnx_asr
        except ImportError:
            raise SystemExit('Parakeet needs onnx-asr in this Python: pip install "onnx-asr[cpu,hub]"')
        try:
            import onnxruntime
            gpu = "CUDAExecutionProvider" in onnxruntime.get_available_providers()
        except Exception:
            gpu = False
        return onnx_asr.load_model(PARAKEET, quantization=None if gpu else "int8").with_timestamps()
    if engine == "faster":
        from faster_whisper import WhisperModel

        try:
            import ctranslate2
            cuda = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            cuda = False
        if cuda:
            return WhisperModel(model, device="cuda", compute_type="float16")
        return WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    import whisper

    return whisper.load_model(model)


def parakeet_words(tokens, times, offset=0.0, end=None):
    """Parakeet's pieces of words (a piece starting with a space starts a word) and their start times ->
    [(start, end, word)]. A word ends where the next one starts, but at most 0.6 s after its last piece, so a pause
    is never counted as part of the word before it."""
    found = []
    for token, t in zip(tokens, times):
        if token.startswith(" ") or not found:
            found.append([float(t), float(t), token.strip()])
        else:
            found[-1][2] += token
            found[-1][1] = float(t)
    out = []
    for i, (start, last, word) in enumerate(found):
        following = found[i + 1][0] if i + 1 < len(found) else (end if end is not None else last + 0.3)
        stop = max(min(following, last + 0.6), last + 0.08)
        out.append((round(start + offset, 3), round(stop + offset, 3), word))
    return [w for w in out if w[2]]


def quiet_splits(audio, rate=16000, longest=60.0):
    """[(first sample, end sample)] pieces of at most `longest` seconds, each cut at the quietest fifth of a second
    in its last quarter, so a word is never cut in two (Parakeet is given one piece at a time)."""
    n, size, start, pieces = len(audio), int(longest * rate), 0, []
    while n - start > size:
        lo, hi = start + int(size * 0.75), start + size
        frame = rate // 100
        seg = audio[lo:hi]
        m = len(seg) // frame
        loudness = np.sqrt((seg[:m * frame].reshape(m, frame) ** 2).mean(axis=1))
        smooth = np.convolve(loudness, np.ones(20) / 20, mode="same")
        cut = lo + int(np.argmin(smooth)) * frame
        pieces.append((start, cut))
        start = cut
    pieces.append((start, n))
    return pieces


def transcribe(model, engine, audio, language, prompt=None, words=False, context=False):
    """audio: float32 mono at 16 kHz. Returns (text, [(start, end, word), ...])."""
    audio = np.ascontiguousarray(audio, dtype=np.float32)
    if engine == "parakeet":
        texts, found = [], []
        for a, b in quiet_splits(audio):
            r = model.recognize(audio[a:b], sample_rate=16000)
            texts.append(r.text.strip())
            found += parakeet_words(r.tokens, r.timestamps, offset=a / 16000, end=(b - a) / 16000)
        return " ".join(t for t in texts if t), (found if words else [])
    if engine == "faster":
        segments, _ = model.transcribe(audio, language=language, initial_prompt=prompt, word_timestamps=words,
                                       condition_on_previous_text=context, beam_size=1)
        segments = list(segments)
        text = " ".join(s.text.strip() for s in segments).strip()
        found = [(w.start, w.end, w.word.strip()) for s in segments for w in (s.words or [])] if words else []
        return text, found
    result = model.transcribe(audio, language=language, fp16=False, word_timestamps=words, initial_prompt=prompt,
                              condition_on_previous_text=context)
    found = [(w["start"], w["end"], w["word"].strip()) for s in result["segments"] for w in s["words"]] if words else []
    return result["text"].strip(), found
