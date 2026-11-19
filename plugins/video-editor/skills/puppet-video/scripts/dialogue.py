"""Turns a dialogue script into the voice track and the timing for the puppet animation.

  python -I dialogue.py dialogue.md [--voices-dir ~/.video-editor/voices] [--piper-python <python with piper-tts>]
                        [--rhubarb <path to rhubarb>] [--audio-dir recordings] [--gap 0.35] [--speed 1.0]
                        [--loudness -14] [--size 1080x1920] [--out-dir puppet]

dialogue.md (references/puppet.md has the full format):
  [Lola] voice=en_GB-cori-medium look=lola
  [Max] voice=es_ES-sharvard-medium speaker=M look=max
  Lola: Hi! Could I have a flat white, please? | ¡Hola! ¿Me pones un café con leche?
  > Max: happy
  Max: Of course. Anything else?
  > pause 0.8
The [Name] lines set each character's voice (a Piper voice name; speaker= picks one voice of a multi-speaker model,
by name or number) and look (lola, max or pixel, the characters drawn in Puppet.tsx; colour=#RRGGBB recolours it).
"Name: text" is one turn; text after " | " is a translation shown under the captions (for students). "> Name:
happy|surprised|thinking|sad|neutral" changes that character's expression from the next turn; "> pause 0.8" adds
seconds of silence. Lines starting with "#" are comments.

For each turn it makes the audio with Piper (or takes <audio-dir>/01.wav, 02.wav... when the lines were recorded),
then the mouth shapes: Rhubarb Lip Sync when it's installed (with the turn's text for English, its phonetic
recognizer for other languages), otherwise from the loudness, so it always works (rougher: open and closed, not the
shape of each sound). The turns are joined with --gap seconds between them, levelled to --loudness LUFS.

Writes to --out-dir: voice.wav, puppet-props.json (the props for the Puppet composition: characters, turns with their
times, mouth shapes and expressions, length) and credits.txt (each voice's license, and the credit line to put in
the video's description when the license asks for one). Then transcribe voice.wav for captions, and render
(SKILL.md). Standard library and FFmpeg; Piper and Rhubarb when available.
"""
import argparse
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

sys.stdout.reconfigure(encoding="utf-8")

RATE = 48000
FPS = 30
LOOKS = ("lola", "max", "pixel")
EXPRESSIONS = ("neutral", "happy", "surprised", "thinking", "sad")

# Licenses read from each voice's MODEL_CARD (huggingface.co/rhasspy/piper-voices), November 2026.
VOICE_LICENSES = {
    "es_ES-davefx-medium": ("CC0 (public domain)", None),
    "es_ES-carlfm-x_low": ("public domain", None),
    "es_ES-sharvard-medium": ("CC BY 3.0", "Voz sintética de Piper (modelo sharvard, corpus Sharvard, CC BY 3.0)"),
    "en_GB-alba-medium": ("CC BY 4.0", "Synthetic voice: Piper, alba model (CSTR, University of Edinburgh, CC BY 4.0)"),
    "en_GB-cori-medium": ("CC BY 4.0", "Synthetic voice: Piper, cori model (Hi-Fi Multi-Speaker English TTS "
                          "dataset, NVIDIA, CC BY 4.0)"),
    "en_GB-northern_english_male-medium": ("CC BY-SA 4.0", "Synthetic voice: Piper, northern_english_male model "
                                           "(OpenSLR 83, CC BY-SA 4.0)"),
    "en_GB-southern_english_female-low": ("CC BY-SA 4.0", "Synthetic voice: Piper, southern_english_female model "
                                          "(OpenSLR 83, CC BY-SA 4.0)"),
}


# ---- the script ----------------------------------------------------------------------------------------------------

def parse(text):
    """(characters, turns). characters: {name: {voice, speaker, look, colour}}; turns: [{speaker, text, translation,
    expression, pause_before}]. Raises ValueError with the line number."""
    characters, turns, expressions = {}, [], {}
    pause = 0.0
    for n, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        head = re.match(r"^\[([^\]]+)\]\s*(.*)$", s)
        if head:
            name = head.group(1).strip()
            opts = dict(re.findall(r"(\w+)=(\S+)", head.group(2)))
            look = opts.get("look", LOOKS[len(characters) % len(LOOKS)]).lower()
            if look not in LOOKS:
                raise ValueError(f"line {n}: look={look} isn't one of {', '.join(LOOKS)}.")
            if "voice" not in opts:
                raise ValueError(f"line {n}: [{name}] needs voice=<Piper voice name>.")
            characters[name] = {"voice": opts["voice"], "speaker": opts.get("speaker"), "look": look,
                                "colour": opts.get("colour") or opts.get("color")}
            continue
        if s.startswith(">"):
            d = s[1:].strip()
            p = re.match(r"^(?:pause|pausa)\s+([\d.]+)", d, re.I)
            if p:
                pause += float(p.group(1))
                continue
            e = re.match(r"^([^:]+):\s*(\w+)", d)
            if e and e.group(1).strip() in characters:
                expr = e.group(2).lower()
                expr = {"feliz": "happy", "sorprendido": "surprised", "sorprendida": "surprised",
                        "pensando": "thinking", "triste": "sad", "normal": "neutral"}.get(expr, expr)
                if expr not in EXPRESSIONS:
                    raise ValueError(f"line {n}: expression {expr} isn't one of {', '.join(EXPRESSIONS)}.")
                expressions[e.group(1).strip()] = expr
            continue                                            # other directions are notes for Claude
        t = re.match(r"^([^:]+):\s*(.+)$", s)
        if not t:
            raise ValueError(f"line {n}: not a turn (Name: text), a [Name] line or a > direction: {s}")
        name = t.group(1).strip()
        if name not in characters:
            raise ValueError(f"line {n}: {name} speaks but has no [{name}] line with a voice.")
        said, _, translation = t.group(2).partition(" | ")
        turns.append({"speaker": name, "text": said.strip(), "translation": translation.strip() or None,
                      "expression": expressions.get(name, "neutral"), "pause_before": pause})
        pause = 0.0
    if not turns:
        raise ValueError("No turns: write lines like 'Lola: Hello!'.")
    return characters, turns


# ---- audio -----------------------------------------------------------------------------------------------------------

def to_wav(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", str(RATE), "-sample_fmt", "s16", dst],
                   check=True)


def read_pcm(path):
    with wave.open(path) as w:
        frames = w.readframes(w.getnframes())
    return list(struct.unpack(f"<{len(frames) // 2}h", frames))


def trim_silence(samples, threshold=300, keep=0.04):
    """Piper and recordings start and end with silence; keep only a short margin."""
    loud = [i for i, v in enumerate(samples) if abs(v) > threshold]
    if not loud:
        return samples
    margin = int(keep * RATE)
    return samples[max(0, loud[0] - margin):loud[-1] + margin]


def synth(text, voice, speaker, voices_dir, piper_python, out, speed):
    model = os.path.join(voices_dir, voice + ".onnx")
    if not os.path.exists(model):
        sys.exit(f"Voice {voice} isn't in {voices_dir}. Download it (references/puppet.md, Voices).")
    cmd = [piper_python, "-m", "piper", "-m", model, "-f", out, "--length-scale", f"{1 / speed:.3f}"]
    if speaker is not None:
        ids = json.load(open(model + ".json", encoding="utf-8")).get("speaker_id_map") or {}
        cmd += ["-s", str(ids.get(speaker, speaker))]
    r = subprocess.run(cmd + ["--", text], capture_output=True, text=True)
    if r.returncode or not os.path.exists(out):
        sys.exit(f"Piper failed on \"{text}\": {r.stderr.strip()[-400:]}")


# ---- mouth shapes ----------------------------------------------------------------------------------------------------

def loudness_cues(samples, rate=RATE, step=1 / FPS):
    """Mouth shapes from loudness alone: X closed in silence, then B, C, D as the voice gets louder."""
    n = max(1, int(rate * step))
    levels = []
    for i in range(0, len(samples), n):
        chunk = samples[i:i + n]
        levels.append(math.sqrt(sum(v * v for v in chunk) / max(1, len(chunk))))
    peak = max(levels) if levels else 0
    cues = []
    for k, lv in enumerate(levels):
        r = lv / peak if peak else 0
        shape = "X" if r < 0.12 else "B" if r < 0.35 else "C" if r < 0.65 else "D"
        if cues and cues[-1]["value"] == shape:
            cues[-1]["end"] = round((k + 1) * step, 3)
        else:
            cues.append({"start": round(k * step, 3), "end": round((k + 1) * step, 3), "value": shape})
    merged = []                                         # a one-frame shape is a flicker: join it to the one before
    for c in cues:
        if merged and c["end"] - c["start"] < step * 1.5:
            merged[-1]["end"] = c["end"]
        else:
            merged.append(c)
    return merged


def rhubarb_cues(rhubarb, wav, text, english):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
    cmd = [rhubarb, "-f", "json", "--extendedShapes", "GHX", "-q"]
    cmd += ["-d", f.name] if english else ["--recognizer", "phonetic"]
    r = subprocess.run(cmd + [wav], capture_output=True, text=True)
    os.unlink(f.name)
    if r.returncode:
        return None
    return [{"start": c["start"], "end": c["end"], "value": c["value"]} for c in json.loads(r.stdout)["mouthCues"]]


def find_rhubarb(given):
    if given:
        return given
    found = shutil.which("rhubarb")
    if found:
        return found
    base = os.path.join(os.path.expanduser("~"), ".video-editor", "tools")
    for root, _, files in os.walk(base) if os.path.isdir(base) else []:
        for name in ("rhubarb", "rhubarb.exe"):
            if name in files:
                return os.path.join(root, name)
    return None


# ---- main ------------------------------------------------------------------------------------------------------------

def credits(characters):
    lines, needed = [], []
    for name, c in characters.items():
        lic = VOICE_LICENSES.get(c["voice"])
        if lic:
            lines.append(f"{name}: {c['voice']}, license {lic[0]}")
            if lic[1]:
                needed.append(lic[1])
        else:
            lines.append(f"{name}: {c['voice']}, license NOT CHECKED: read its MODEL_CARD on "
                         "huggingface.co/rhasspy/piper-voices before publishing")
    out = "Voices:\n" + "\n".join("  " + l for l in lines)
    if needed:
        out += "\n\nPut this in the video's description (the voices' licenses ask for it):\n" + "\n".join(
            sorted(set(needed)))
    return out + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dialogue")
    ap.add_argument("--voices-dir", default=os.path.join(os.path.expanduser("~"), ".video-editor", "voices"))
    ap.add_argument("--piper-python", default=sys.executable, help="the Python that has piper-tts installed")
    ap.add_argument("--rhubarb", help="path to Rhubarb Lip Sync (default: on the PATH or in ~/.video-editor/tools)")
    ap.add_argument("--no-rhubarb", action="store_true", help="mouth shapes from the loudness even if Rhubarb is there")
    ap.add_argument("--audio-dir", help="recorded turns, 01.wav, 02.wav... in order, instead of Piper")
    ap.add_argument("--gap", type=float, default=0.35, help="seconds between turns")
    ap.add_argument("--speed", type=float, default=1.0, help="speech speed (0.9 slower for beginners)")
    ap.add_argument("--loudness", type=float, default=-14.0)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--out-dir", default="puppet")
    a = ap.parse_args()

    try:
        characters, turns = parse(open(a.dialogue, encoding="utf-8").read())
    except ValueError as err:
        sys.exit(f"{a.dialogue}: {err}")
    os.makedirs(a.out_dir, exist_ok=True)
    rhubarb = None if a.no_rhubarb else find_rhubarb(a.rhubarb)
    print("Mouth shapes:", f"Rhubarb ({rhubarb})" if rhubarb else "from loudness (install Rhubarb for real mouth "
          "shapes: references/puppet.md)")
    width, height = (int(v) for v in a.size.lower().split("x"))

    track, t = [], 0.4                                  # a short breath before the first turn
    out_turns = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, turn in enumerate(turns, 1):
            c = characters[turn["speaker"]]
            raw = os.path.join(tmp, f"raw{i:02d}.wav")
            if a.audio_dir:
                src = next((os.path.join(a.audio_dir, f"{i:02d}.{ext}") for ext in ("wav", "mp3", "m4a", "flac")
                            if os.path.exists(os.path.join(a.audio_dir, f"{i:02d}.{ext}"))), None)
                if not src:
                    sys.exit(f"{a.audio_dir} has no recording for turn {i} ({i:02d}.wav).")
                shutil.copy(src, raw)
            else:
                synth(turn["text"], c["voice"], c["speaker"], a.voices_dir, a.piper_python, raw, a.speed)
            clean = os.path.join(tmp, f"turn{i:02d}.wav")
            to_wav(raw, clean)
            samples = trim_silence(read_pcm(clean))
            with wave.open(clean, "w") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(RATE)
                w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            cues = None
            if rhubarb:
                cues = rhubarb_cues(rhubarb, clean, turn["text"], c["voice"].lower().startswith("en"))
            if cues is None:
                cues = loudness_cues(samples)
            t += turn["pause_before"]
            start = t
            track.append((int(start * RATE), samples))
            length = len(samples) / RATE
            out_turns.append({"speaker": turn["speaker"], "text": turn["text"], "translation": turn["translation"],
                              "expression": turn["expression"], "start": round(start, 3),
                              "end": round(start + length, 3),
                              "mouth": [[round(start + q["start"], 3), q["value"]] for q in cues]})
            t = start + length + a.gap
        total = t - a.gap + 0.8
        pcm = [0] * int(total * RATE)
        for at, samples in track:
            pcm[at:at + len(samples)] = samples
        joined = os.path.join(tmp, "joined.wav")
        with wave.open(joined, "w") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(RATE)
            w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
        voice = os.path.join(a.out_dir, "voice.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-af",
                        f"loudnorm=I={a.loudness}:TP=-1.5:LRA=11", "-ar", str(RATE), "-ac", "2", voice], check=True)

    props = {"characters": [{"name": n, "look": c["look"], "colour": c["colour"]} for n, c in characters.items()],
             "turns": out_turns, "length": round(total, 3), "fps": FPS, "width": width, "height": height}
    json.dump(props, open(os.path.join(a.out_dir, "puppet-props.json"), "w", encoding="utf-8"), ensure_ascii=False,
              indent=1)
    open(os.path.join(a.out_dir, "credits.txt"), "w", encoding="utf-8").write(
        credits(characters) if not a.audio_dir else "Recorded voices: credit the speakers if they want it.\n")
    print(f"{len(out_turns)} turns, {total:.1f} s. Wrote {a.out_dir}/voice.wav, puppet-props.json, credits.txt.")
    if any(c["voice"] not in VOICE_LICENSES for c in characters.values()) and not a.audio_dir:
        print("Note: a voice's license isn't checked yet: see credits.txt before publishing.")


if __name__ == "__main__":
    main()
