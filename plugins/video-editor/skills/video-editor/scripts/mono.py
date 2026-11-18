"""Turns one or more parts of the video black and white, then back to colour, with a short fade.

  python -I mono.py --part 12.4 18.0 [--part 40 44.5] [--fade 0.3] [--contrast 1.08] [--length 63.4]
  python -I mono.py --say "antes" [--until "y ahora"] [--captions captions.json]

Times are seconds in the finished video, like captions.json (after the speed-up and any drops.py pass).
--say finds a phrase in captions.json (accents and case ignored): the grey part starts at its first word and lasts to
the end of that caption, or to the end of the --until phrase. It prints what it found: check it with the user.

It writes mono.txt, one line to add to the picture chain:
  hue=s='...',eq=contrast='...':eval=frame
Put it after retouch, blur and the colour look, and before titles, graphics, captions, logo and end card, so all the
text and graphics stay in colour. Inside each part the colour fades out over --fade seconds from its start, stays
grey, and fades back in over the last --fade seconds (--fade 0 switches at once). --contrast adds a little
contrast while grey, so the picture doesn't look flat (1 for none). Parts that overlap or touch are joined.
Standard library only.
"""
import argparse
import json
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")


def words_of(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return ["".join(c for c in w if c.isalnum()) for w in text.split() if any(c.isalnum() for c in w)]


def find(caption_words, phrase, after=-1.0):
    """First place after `after` where the phrase is said: (index of first word, index of last word)."""
    want = words_of(phrase)
    if not want:
        return None
    for i in range(len(caption_words) - len(want) + 1):
        if caption_words[i][0] > after and [w[2] for w in caption_words[i:i + len(want)]] == want:
            return i, i + len(want) - 1
    return None


def parts_from_captions(path, say, until):
    caps = json.load(open(path, encoding="utf-8"))
    flat = []  # (start, end, word, caption end)
    for c in caps:
        for s, e, text in c["words"]:
            for w in words_of(text):
                flat.append((s, e, w, c["end"]))
    hit = find(flat, say)
    if not hit:
        sys.exit(f'"{say}" is not in {path}.')
    start = flat[hit[0]][0]
    if until:
        end_hit = find(flat, until, after=start)
        if not end_hit:
            sys.exit(f'"{until}" is not said after "{say}" in {path}.')
        end = flat[end_hit[1]][1]
    else:
        end = flat[hit[1]][3]
    print(f'Found "{say}" at {start:.2f} s; black and white from {start:.2f} to {end:.2f} s.')
    return [(start, end)]


def merge(parts):
    out = []
    for s, e in sorted(parts):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def grey_expression(parts, fade):
    """0 in colour, 1 fully grey, as an FFmpeg expression of t."""
    terms = []
    for s, e in parts:
        if fade <= 0:
            terms.append(f"gte(t,{s:.3f})*lt(t,{e:.3f})")
        else:
            f = min(fade, (e - s) / 2)
            terms.append(f"clip(min((t-{s:.3f})/{f:.3f},({e:.3f}-t)/{f:.3f}),0,1)")
    return "+".join(terms)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", nargs=2, type=float, action="append", metavar=("START", "END"), default=[])
    ap.add_argument("--say", help="a phrase from captions.json where the grey part starts")
    ap.add_argument("--until", help="with --say: the phrase where it ends (default: the end of that caption)")
    ap.add_argument("--captions", default="captions.json")
    ap.add_argument("--fade", type=float, default=0.3, help="seconds to fade to grey and back (0: switch at once)")
    ap.add_argument("--contrast", type=float, default=1.08, help="contrast while grey (1: unchanged)")
    ap.add_argument("--length", type=float, help="length of the video in seconds, to refuse parts past the end")
    ap.add_argument("--out", default="mono.txt")
    a = ap.parse_args()

    parts = [tuple(p) for p in a.part]
    if a.say:
        parts += parts_from_captions(a.captions, a.say, a.until)
    if not parts:
        sys.exit("Give at least one --part START END, or --say.")
    for s, e in parts:
        if not 0 <= s < e:
            sys.exit(f"A part must start at 0 s or later and end after it starts: {s} to {e}.")
        if a.length and e > a.length + 0.001:
            sys.exit(f"The part {s} to {e} s goes past the end of the video ({a.length} s).")
    parts = merge(parts)
    g = grey_expression(parts, a.fade)
    line = f"hue=s='1-({g})'"
    if abs(a.contrast - 1) > 1e-6:
        line += f",eq=contrast='1+{a.contrast - 1:.3f}*({g})':eval=frame"
    open(a.out, "w", encoding="utf-8").write(line + "\n")
    for s, e in parts:
        print(f"Black and white from {s:.2f} to {e:.2f} s" + (f", fading over {min(a.fade, (e - s) / 2):.2f} s." if a.fade > 0 else "."))
    print(f"Wrote {a.out}. Add its line to the picture chain after the colour look, before any text or graphics.")


if __name__ == "__main__":
    main()
