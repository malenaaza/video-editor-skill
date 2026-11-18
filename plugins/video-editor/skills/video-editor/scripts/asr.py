"""Shared speech-to-text helper: one interface for openai-whisper and faster-whisper.

The scripts that listen to short pieces of audio (hear.py, checkcuts.py, hunt_fillers.py) take
--engine and --model. Findings from real edits:
- openai-whisper `small` caught a filler that faster-whisper `small` missed (fillers.py keeps it).
- `small` mishears slurred words; `medium` with faster-whisper (int8 on CPU) settles them.
"""
import os

import numpy as np


def load_audio(path):
    """Any audio or video file -> float32 mono at 16 kHz (decoded by FFmpeg)."""
    import subprocess

    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768


def load(model, engine):
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


def transcribe(model, engine, audio, language, prompt=None, words=False, context=False):
    """audio: float32 mono at 16 kHz. Returns (text, [(start, end, word), ...])."""
    audio = np.ascontiguousarray(audio, dtype=np.float32)
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
