"""Writes burned-in captions (captions.ass) for a cut, from the source transcript and plan.json.

Run from the project's build folder. Needs only Python.

  python -I captions.py <transcript.json> --font "Montserrat" --size 64 --margin-v 520 [options]

It moves every kept word to its time in the cut (through plan.json, including the speed-up),
drops words that were cut, groups the rest into short captions, and writes:
  captions.ass    for FFmpeg:  -vf ass=captions.ass:fontsdir=fonts
  captions.json   the same captions as a list (start, end, text, words), for timing emojis,
                  product tags and sound effects, and for comparing with the re-check transcript.

Take the look from the brand's `Captions:` line in my-setup.md:
  --style outline   coloured text with an outline (default)
  --style box       text on a coloured box
Colours are hex (#RRGGBB). --margin-v is the distance from the bottom of the frame to the
bottom of the caption, in pixels of the output video (--width x --height).

Fixing words: Whisper misspells names. --fix fixes.json takes {"glo serum": "Glow Serum",
"sefora": "Sephora"}; matching ignores case and punctuation and can span several words.
--skip skip.json takes a list of [start, end] source ranges (transcript clock) whose words stay
in the audio but out of the captions (for example a word in the speaker's other language).

A word that crosses a cut is kept when at least half of it is in the cut. After a repeat is
removed, check captions.json around that cut: the kept take's word must appear once.

Timings from a transcript of the cut voice (--on-cut): Whisper's word times on a long source
recording were up to 1 s off around pauses, so the captions drifted. A transcript of the cut voice
has no pauses to confuse it, and its times are already times in the cut. Transcribe the cut voice
(the same transcript Rule 3's check needs), then:

  python -I captions.py cut-voice.json --on-cut --font ... [--length 63.4]
  python -I captions.py clip1.json clip2.json --on-cut --durations 41.2 22.2 --font ...

--durations gives each clip's length in seconds when several clips are joined (the clips' times
are shifted by the lengths before them). --length is the length of the finished video (default:
the sum of --durations, or plan.json's length, or the last word plus 0.5 s). No plan.json needed.

After the second pass (drops.py): --drops drops.json moves every word to its time in the video the
drops were cut from, and leaves out the fillers that were removed. Run it on either kind of input.

Caption breaking: --two-lines 30 puts captions longer than 30 characters on two lines. A caption
that has to break because it is long won't end on a small word like "de" or "the" (--dangling es,
en, or a file with one word per line). A | at the end of a word, written in fixes.json
("para cubrir un poco": "para cubrir un poco|"), forces a break after it; a fix whose text ends
in . adds a sentence end where the transcript has no punctuation.
"""
import argparse
import json
import os
import re
import sys
from fractions import Fraction

sys.stdout.reconfigure(encoding="utf-8")


def ass_color(hex_color, alpha=0):
    h = hex_color.lstrip("#")
    if len(h) != 6:
        sys.exit(f"Colour {hex_color!r} must look like #RRGGBB.")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def stamp(t):
    cs = max(int(round(t * 100)), 0)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def norm(text):
    return re.sub(r"[^\w]+", "", text, flags=re.UNICODE).lower()


DANGLING = {
    "es": "de del los las el la un una en que y o con a al es mi mis no ni por para como se me lo pero muy más este esta",
    "en": "the a an of to in on at and or but with for from by as is are my your that this",
}


def dangling_words(spec):
    if not spec:
        return set()
    if spec in DANGLING:
        return set(DANGLING[spec].split())
    return {line.strip().lower() for line in open(spec, encoding="utf-8") if line.strip()}


def remap_drops(words, drops):
    """Words in times of the video the drops were cut from -> times after the drops."""
    cuts = [(d["start"], d["len"], d["kind"]) for d in drops["drops"]]
    kept = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        if any(kind == "F" and s <= mid < s + length for s, length, kind in cuts):
            continue  # a filler that was cut
        out = dict(w)
        for key in ("start", "end"):
            t, removed = w[key], 0.0
            for s, length, _ in cuts:
                if t >= s + length:
                    removed += length
                elif t > s:
                    removed += t - s
                else:
                    break
            out[key] = t - removed
        kept.append(out)
    return kept


def kept_span(plan, fps, s, e):
    """The part of source range s..e that is in the cut, as cut times; None if under half is kept."""
    start = end = None
    kept = 0.0
    for (f0, f1), o in zip(plan["frames"], plan["offsets"]):
        a, b = max(s, f0 / fps), min(e, f1 / fps)
        if b > a:
            kept += b - a
            t0, t1 = o / fps + a - f0 / fps, o / fps + b - f0 / fps
            start = t0 if start is None else start
            end = t1
    if start is None or kept < 0.5 * max(e - s, 1e-6):
        return None
    return start, end


def apply_fixes(words, fixes):
    """Replace runs of words that match a key in fixes. The replacement takes the run's times."""
    keys = sorted(((norm(k), v) for k, v in fixes.items()), key=lambda kv: -len(kv[0]))
    out, i = [], 0
    while i < len(words):
        for key, value in keys:
            joined, j = "", i
            while j < len(words) and len(joined) < len(key):
                joined += norm(words[j]["text"])
                j += 1
            if joined == key and key:
                tail = re.search(r"[.,;:!?…]+$", words[j - 1]["text"])
                out.append({"start": words[i]["start"], "end": words[j - 1]["end"],
                            "text": value + (tail.group(0) if tail else "")})
                i = j
                break
        else:
            out.append(words[i])
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcripts", nargs="+", help="Whisper json, or several with --on-cut")
    ap.add_argument("--plan", default="plan.json")
    ap.add_argument("--on-cut", action="store_true", help="the transcript is of the cut voice: times are cut times")
    ap.add_argument("--durations", type=float, nargs="+", help="with --on-cut: each clip's length in seconds")
    ap.add_argument("--length", type=float, help="length of the finished video in seconds")
    ap.add_argument("--drops", help="drops.json from drops.py")
    ap.add_argument("--two-lines", type=int, default=0, help="captions longer than this many characters get two lines")
    ap.add_argument("--dangling", help="es, en or a file: small words a forced break must not end on")
    ap.add_argument("--out", default="captions.ass")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--font", required=True, help="the font's family name, as FFmpeg's fontselect reports it")
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--bold", action="store_true")
    ap.add_argument("--style", choices=["outline", "box"], default="outline")
    ap.add_argument("--text-color", default="#FFFFFF")
    ap.add_argument("--outline-color", default="#000000", help="outline colour, or the box colour with --style box")
    ap.add_argument("--outline", type=float, default=4, help="outline width, or box padding with --style box")
    ap.add_argument("--shadow", type=float, default=0)
    ap.add_argument("--margin-v", type=int, default=520, help="pixels from the bottom of the frame")
    ap.add_argument("--margin-h", type=int, default=90)
    ap.add_argument("--max-chars", type=int, default=22, help="longest caption, in characters")
    ap.add_argument("--max-words", type=int, default=4)
    ap.add_argument("--gap", type=float, default=0.35, help="a pause this long starts a new caption")
    ap.add_argument("--hold", type=float, default=0.12, help="how long a caption stays after its last word")
    ap.add_argument("--upper", action="store_true", help="ALL CAPS")
    ap.add_argument("--no-punctuation", action="store_true", help="drop commas and full stops (keeps ? and !)")
    ap.add_argument("--fix", help="json with corrections, see above")
    ap.add_argument("--skip", help="json with source ranges to leave out of the captions")
    a = ap.parse_args()

    skip = json.load(open(a.skip, encoding="utf-8")) if a.skip else []
    plan = None
    if os.path.exists(a.plan):
        plan = json.load(open(a.plan, encoding="utf-8"))
    elif not a.on_cut:
        sys.exit(f"{a.plan} not found. Run cutplan.py build first, or use --on-cut with a transcript of the cut voice.")
    if not a.on_cut and len(a.transcripts) > 1:
        sys.exit("Several transcripts only work with --on-cut.")
    if plan:
        fps = float(Fraction(plan["fps"]))
        speed = plan.get("speed", 1) or 1
        offset = plan.get("audio_offset", 0)

    words, dropped, shift = [], 0, 0.0
    for index, path in enumerate(a.transcripts):
        data = json.load(open(path, encoding="utf-8"))
        for seg in data.get("segments", []):
            for w in seg.get("words", []):
                text = w["word"].strip()
                if not text:
                    continue
                mid = (w["start"] + w["end"]) / 2 + shift
                if any(s <= mid < e for s, e in (r[:2] for r in skip)):
                    continue
                if a.on_cut:
                    words.append({"start": w["start"] + shift, "end": w["end"] + shift, "text": text})
                    continue
                span = kept_span(plan, fps, w["start"] + offset, w["end"] + offset)
                if span is None:
                    dropped += 1
                    continue
                words.append({"start": span[0] / speed, "end": span[1] / speed, "text": text})
        if a.on_cut and a.durations and index < len(a.durations):
            shift += a.durations[index]
    if not words:
        sys.exit("No words left in the cut.")
    words.sort(key=lambda w: w["start"])
    if a.fix:
        words = apply_fixes(words, json.load(open(a.fix, encoding="utf-8")))
    if a.drops:
        drops = json.load(open(a.drops, encoding="utf-8"))
        words = remap_drops(words, drops)
        length = drops["new_frames"] * drops["frame"]
    elif a.length:
        length = a.length
    elif a.on_cut and a.durations:
        length = sum(a.durations)
    elif plan:
        length = plan["total_frames"] / fps / speed
    else:
        length = words[-1]["end"] + 0.5
    avoid = dangling_words(a.dangling)

    def show(text):
        text = text.replace("|", "")
        if a.no_punctuation:
            text = re.sub(r"[.,;:…]+$", "", text)
        return text.upper() if a.upper else text

    # Group words into captions: break at sentence ends, long pauses, and the size limits.
    caps, cur = [], []
    for w in words:
        line = " ".join(show(x["text"]) for x in cur + [w])
        natural = bool(cur) and (w["start"] - cur[-1]["end"] > a.gap or re.search(r"[.!?…|]$", cur[-1]["text"]))
        forced = bool(cur) and (len(line) > a.max_chars or len(cur) >= a.max_words)
        if natural or forced:
            moved = []
            while forced and not natural and len(cur) > 2 and len(moved) < 2 and avoid \
                    and norm(cur[-1]["text"]) in avoid and not cur[-1]["text"].endswith(","):
                moved.insert(0, cur.pop())  # don't end a caption on "de", "the"...
            caps.append(cur)
            cur = moved
        cur.append(w)
    if cur:
        caps.append(cur)
    total = length
    out = []
    for i, cap in enumerate(caps):
        start = cap[0]["start"]
        nxt = caps[i + 1][0]["start"] if i + 1 < len(caps) else total
        end = min(cap[-1]["end"] + a.hold, nxt)
        if i + 1 < len(caps) and nxt - end < a.gap:  # no flicker between captions that follow each other
            end = nxt
        out.append({"start": round(start, 3), "end": round(max(end, start + 0.1), 3),
                    "text": " ".join(show(x["text"]) for x in cap),
                    "words": [[round(x["start"], 3), round(x["end"], 3), x["text"]] for x in cap]})

    box = a.style == "box"
    style = ",".join(str(x) for x in [
        "Cap", a.font, a.size, ass_color(a.text_color), ass_color(a.text_color), ass_color(a.outline_color),
        ass_color(a.outline_color if box else "#000000", 0 if box else 0x80), -1 if a.bold else 0, 0, 0, 0,
        100, 100, 0, 0, 3 if box else 1, a.outline, a.shadow, 2, a.margin_h, a.margin_h, a.margin_v, 1])
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {a.width}", f"PlayResY: {a.height}",
             "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
             "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
             "Alignment, MarginL, MarginR, MarginV, Encoding",
             "Style: " + style, "",
             "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    def two_lines(text):
        if not a.two_lines or len(text) <= a.two_lines:
            return text
        middle = len(text) / 2
        spaces = [m.start() for m in re.finditer(" ", text)]
        if not spaces:
            return text
        cut = min(spaces, key=lambda i: abs(i - middle))
        return text[:cut] + "\\N" + text[cut + 1:]

    for c in out:
        text = two_lines(c["text"].replace("{", "(").replace("}", ")"))
        lines.append(f"Dialogue: 0,{stamp(c['start'])},{stamp(c['end'])},Cap,,0,0,0,,{text}")
    open(a.out, "w", encoding="utf-8-sig").write("\n".join(lines) + "\n")
    json_out = re.sub(r"\.ass$", "", a.out) + ".json"
    json.dump(out, open(json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Wrote {a.out} and {json_out}: {len(out)} captions, {len(words)} words"
          + (f" ({dropped} words were in removed parts)." if not a.on_cut else " (times from the cut voice's own transcript)."))
    longest = max(out, key=lambda c: len(c["text"]))
    print(f"Longest caption ({len(longest['text'])} characters): {longest['text']!r}. "
          "Look at that frame to check it fits the width.")


if __name__ == "__main__":
    main()
