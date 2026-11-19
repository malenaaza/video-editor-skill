"""YouTube chapters for the description, from where each topic starts in the finished video.

  python -I chapters.py chapters.json [--captions captions.json] [--length 612.4] [--out chapters.txt]
                        [--ffmetadata chapters.ffmeta]

chapters.json is written by Claude after reading the transcript of the finished video: one entry per topic, in
order, each starting either at a phrase the speaker says or at a time in seconds:
  [{"title": "Qué es un prompt", "say": "vale, empecemos"},
   {"title": "Tres ejemplos reales", "at": 95.2}]
A phrase is looked up in captions.json (accents and case ignored) and the chapter starts at its first word, so the
times follow the finished video even after cuts. The first chapter always starts at 0:00 (YouTube requires it): if the
first entry starts later, it is moved to 0:00 when it starts in the first 10 seconds, and otherwise an opening chapter
is needed (the script says so).

YouTube's rules, checked here (support.google.com/youtube/answer/9884579): the first chapter at 0:00, at least three
chapters, in order, each at least 10 seconds long. A chapter shorter than that stops the script with its name, so
the titles can be merged by hand. Titles: short (it warns above 40 characters, where they get cut off on phones),
in the video's language.

Writes chapters.txt, the lines to paste into the description ("0:00 Intro", "1:02:03 ..." past an hour), and with
--ffmetadata a chapters file FFmpeg can embed in the MP4 too (-i chapters.ffmeta -map_metadata 1), for players
that show chapters from the file. Standard library only.
"""
import argparse
import json
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

MIN_LENGTH = 10.0
TITLE_WARN = 40


def words_of(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return ["".join(c for c in w if c.isalnum()) for w in text.split() if any(c.isalnum() for c in w)]


def flat_words(captions):
    return [(s, w) for c in captions for s, e, text in c["words"] for w in words_of(text)]


def find_phrase(flat, phrase, after=-1.0):
    want = words_of(phrase)
    for i in range(len(flat) - len(want) + 1):
        if want and flat[i][0] > after and [w for _, w in flat[i:i + len(want)]] == want:
            return flat[i][0]
    return None


def stamp(seconds):
    s = int(seconds)
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def resolve(entries, flat, length=None):
    """[(start seconds, title)], checked against YouTube's rules. Raises ValueError with the reason."""
    out, after = [], -1.0
    for e in entries:
        title = str(e.get("title", "")).strip()
        if not title:
            raise ValueError(f"A chapter has no title: {e}")
        if "say" in e:
            t = find_phrase(flat, e["say"], after)
            if t is None:
                raise ValueError(f'"{e["say"]}" ({title}) is not said after the previous chapter.')
        elif "at" in e:
            t = float(e["at"])
        else:
            raise ValueError(f'"{title}" needs "say" (a phrase) or "at" (seconds).')
        if out and t <= out[-1][0]:
            raise ValueError(f'"{title}" starts at {stamp(t)}, before the chapter it follows: keep them in order.')
        out.append((t, title))
        after = t
    if not out:
        raise ValueError("No chapters.")
    if out[0][0] > 0:
        if out[0][0] < MIN_LENGTH:
            out[0] = (0.0, out[0][1])
        else:
            raise ValueError(f'The first chapter, "{out[0][1]}", starts at {stamp(out[0][0])}: YouTube needs one at '
                             '0:00. Add an opening chapter (for example "Intro") or start this one at 0.')
    if len(out) < 3:
        raise ValueError(f"YouTube shows chapters only when there are at least 3; there are {len(out)}.")
    ends = [t for t, _ in out[1:]] + ([length] if length else [])
    for (t, title), end in zip(out, ends):
        if end - t < MIN_LENGTH:
            raise ValueError(f'"{title}" lasts {end - t:.1f} s; YouTube needs at least {MIN_LENGTH:.0f} s per '
                             "chapter. Merge it with the one before or after.")
    return out


def ffmetadata(chapters, length):
    lines = [";FFMETADATA1"]
    ends = [t for t, _ in chapters[1:]] + [length]
    for (t, title), end in zip(chapters, ends):
        safe = title.replace("\\", "\\\\").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(t * 1000)}", f"END={int(end * 1000)}", f"title={safe}"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapters")
    ap.add_argument("--captions", default="captions.json")
    ap.add_argument("--length", type=float, help="length of the finished video in seconds (checks the last chapter)")
    ap.add_argument("--out", default="chapters.txt")
    ap.add_argument("--ffmetadata", help="also write chapters FFmpeg can embed in the video file")
    a = ap.parse_args()

    entries = json.load(open(a.chapters, encoding="utf-8"))
    flat = []
    if any("say" in e for e in entries):
        flat = flat_words(json.load(open(a.captions, encoding="utf-8")))
    try:
        chapters = resolve(entries, flat, a.length)
    except ValueError as err:
        sys.exit(str(err))
    text = "\n".join(f"{stamp(t)} {title}" for t, title in chapters)
    open(a.out, "w", encoding="utf-8").write(text + "\n")
    print(text)
    for _, title in chapters:
        if len(title) > TITLE_WARN:
            print(f'Note: "{title}" is {len(title)} characters; on phones titles over about {TITLE_WARN} get cut off.')
    if a.ffmetadata:
        if not a.length:
            sys.exit("--ffmetadata needs --length (the end of the last chapter).")
        open(a.ffmetadata, "w", encoding="utf-8").write(ffmetadata(chapters, a.length))
        print(f"Wrote {a.ffmetadata}.")
    print(f"Wrote {a.out}: paste these lines into the YouTube description.")


if __name__ == "__main__":
    main()
