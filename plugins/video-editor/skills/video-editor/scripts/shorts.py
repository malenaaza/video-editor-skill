"""Cuts the Shorts out of the finished long video: one folder per Short with its times, its words for vertical
captions, its title, and the commands to make it.

  python -I shorts.py shorts.json --video <wide video without captions> [--captions captions.json]
                      [--pad 0.25] [--out-dir shorts]

shorts.json comes from scriptcut.py (the [SHORT] markers of the script), or Claude writes it after reading the
transcript of the finished video, choosing moments that stand alone:
  [{"title": "La IA que me ahorra dos horas", "say": "le pido a claude", "until": "tengo el vídeo listo"}]
"say" and "until" are phrases (accents, case and punctuation ignored) found in captions.json, the captions of the
finished long video, so the times follow every cut; "at" and "end" in seconds work too. Each Short runs from the
first word of "say" to the last word of "until", with --pad seconds of room on each side (never into the words before
or after).

For each Short it writes <out-dir>/short-N/:
  range.json   start, end and length in the long video, and the title
  words.json   the Short's words, moved to start at 0, in Whisper's format: captions.py --on-cut reads it to make
               captions sized for the vertical video
  steps.txt    the commands, in order: cut the piece from the long video (the version without captions or titles),
               reframe it to vertical (reframe.py), captions, the hook title (the Short's title, TitleCard) and a
               closing line pointing to the full video, then the final export (Rule 6)
It warns when a Short is shorter than 15 s (too short to make its point) or longer than 60 s (platforms allow longer
vertical videos now, but a clip cut from a longer video usually works best under a minute). Standard library only.
"""
import argparse
import json
import os
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")


def norm(word):
    word = unicodedata.normalize("NFKD", word)
    word = "".join(c for c in word if not unicodedata.combining(c)).lower()
    return "".join(c for c in word if c.isalnum())


def flat_words(captions):
    """[(start, end, normalized, as shown)] for every word of captions.json."""
    out = []
    for c in captions:
        for s, e, text in c["words"]:
            for piece in text.split():
                if norm(piece):
                    out.append((float(s), float(e), norm(piece), piece))
    return out


def find(flat, phrase, after=-1.0):
    """(index of the first word, index of the last word) where the phrase is first said after `after`, or None."""
    want = [w for w in (norm(t) for t in phrase.split()) if w]
    for i in range(len(flat) - len(want) + 1):
        if want and flat[i][0] > after and [w[2] for w in flat[i:i + len(want)]] == want:
            return i, i + len(want) - 1
    return None


def resolve(entry, flat, pad=0.25):
    """(start, end, first word index, last word index) of a Short in the long video. Raises ValueError."""
    title = entry.get("title", "Short")
    if "say" in entry:
        hit = find(flat, entry["say"])
        if not hit:
            raise ValueError(f'"{entry["say"]}" ({title}) is not in the captions.')
        i = hit[0]
    else:
        t = float(entry["at"])
        i = min(range(len(flat)), key=lambda k: abs(flat[k][0] - t))
    if "until" in entry:
        hit = find(flat, entry["until"], after=flat[i][0] - 1e-6)
        if not hit:
            raise ValueError(f'"{entry["until"]}" ({title}) is not said after "{entry.get("say", entry.get("at"))}".')
        j = hit[1]
    else:
        t = float(entry["end"])
        j = max(k for k in range(len(flat)) if flat[k][1] <= t + 1e-6)
    start = max(flat[i][0] - pad, flat[i - 1][1] if i > 0 else 0.0, 0.0)
    end = flat[j][1] + pad
    if j + 1 < len(flat):
        end = min(end, flat[j + 1][0])
    return round(start, 3), round(end, 3), i, j


def whisper_words(flat, i, j, start):
    return {"segments": [{"words": [{"word": " " + w[3], "start": round(w[0] - start, 3), "end": round(w[1] - start, 3)}
                                    for w in flat[i:j + 1]]}]}


def steps(n, video, start, end, title):
    length = end - start
    return f"""Short {n}: "{title}" ({length:.1f} s, from {start:.2f} to {end:.2f} s of the long video)

1. Cut the piece from the long video (the version without captions or titles), with the in-between encoder:
   ffmpeg -ss {start:.3f} -to {end:.3f} -i "{video}" <in-between encoder from my-setup.md> -c:a pcm_s16le piece.mov
2. Vertical, following the face (look at reframe.png; parts with no face, such as a screen recording, get
   screen.py stack instead):
   <face python> -I <skill>/scripts/reframe.py piece.mov <face_landmarker.task> --check reframe.png
   ffmpeg -i piece.mov -/filter_complex reframe.txt <in-between encoder> -c:a copy vertical.mov
3. Captions sized for vertical, in the brand's style (Rule 5), from this folder's words:
   python -I <skill>/scripts/captions.py words.json --on-cut --length {length:.2f} --width 1080 --height 1920 ...
4. The hook: the title "{title}" as a TitleCard in the first seconds (it must make sense with no context), and a
   closing line pointing to the full video ("Vídeo completo en mi canal", in the video's language) in the last 2 s.
5. Final export (Rule 6), then check a frame at the start, the middle and the end.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shorts")
    ap.add_argument("--video", required=True, help="the finished long video without captions or titles")
    ap.add_argument("--captions", default="captions.json")
    ap.add_argument("--pad", type=float, default=0.25)
    ap.add_argument("--out-dir", default="shorts")
    a = ap.parse_args()

    entries = json.load(open(a.shorts, encoding="utf-8"))
    flat = flat_words(json.load(open(a.captions, encoding="utf-8")))
    if not flat:
        sys.exit(f"No words in {a.captions}.")
    os.makedirs(a.out_dir, exist_ok=True)
    for n, entry in enumerate(entries, 1):
        title = entry.get("title", f"Short {n}")
        try:
            start, end, i, j = resolve(entry, flat, a.pad)
        except ValueError as err:
            print(f"Short {n} skipped: {err}")
            continue
        folder = os.path.join(a.out_dir, f"short-{n}")
        os.makedirs(folder, exist_ok=True)
        length = end - start
        json.dump({"title": title, "start": start, "end": end, "length": round(length, 3)},
                  open(os.path.join(folder, "range.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(whisper_words(flat, i, j, start), open(os.path.join(folder, "words.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        open(os.path.join(folder, "steps.txt"), "w", encoding="utf-8").write(steps(n, a.video, start, end, title))
        note = ""
        if length < 15:
            note = " Note: under 15 s, probably too short to make its point; add a line before or after."
        elif length > 60:
            note = " Note: over 60 s; clips like this usually work best under a minute: tighten it if you can."
        print(f'Short {n}: "{title}", {start:.2f}-{end:.2f} s ({length:.1f} s).{note} Wrote {folder}/.')


if __name__ == "__main__":
    main()
