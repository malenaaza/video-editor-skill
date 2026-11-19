"""Follows the script in the edit: lines up what was said with script.md, keeps the last good take of every line,
and turns the script's markers into the chapters and the Shorts.

  python -I scriptcut.py script.md <transcript.json> [--cuts cuts.json] [--drop-unscripted]

script.md is the script Claude wrote (references/script.md): one paragraph per spoken line, and markers on their own
lines, in English or Spanish:
  ## [CHAPTER] Title      (or [CAPÍTULO])  the next line starts a chapter
  [SHORT "Title"] ... [/SHORT]            the lines between make a Short (also [SHORT: Title])
  [SCREEN] what to record (or [PANTALLA]), [GRAPHIC] what to show (or [GRÁFICO])   notes for the edit
Lines starting with "#" (the title), ">" (directions to the speaker) and empty lines are not spoken.

For each spoken line it finds every take in the transcript (words compared without accents, case or punctuation,
with a little slack for Whisper's misspellings and a word said differently), and keeps:
  - the last take that says at least 80% of the line (creators repeat a line until it's right);
  - or, when no take gets there, the most complete one, flagged as incomplete.
It writes:
  cuts.json           "remove" ranges for the other takes and for false starts (a few words of a line, then a
                      restart), added to what's already there; its own earlier entries (labelled "script: ...")
                      are replaced, so it can run again after changes. Then build the cut with cutplan.py as usual.
  script-report.md    every line with the take kept, the other takes, lines never said (to record again), lines
                      said out of order, and talk that isn't in the script. That talk is kept unless
                      --drop-unscripted is given: ask the user about it (an ad-lib can be the best moment).
  chapters.json       for chapters.py: each chapter starts at the first words of its first line as said, so the
                      times come from captions.json after the cut. An "Intro" chapter is added when the first
                      chapter doesn't start at the first line.
  shorts.json         for shorts.py: each Short's title, first words and last words as said.
  edit-notes.json     the [SCREEN] and [GRAPHIC] notes, each with the first words of the line it comes before.
Standard library only.
"""
import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding="utf-8")

KEEP_SHARE = 0.8      # a take that says this much of the line counts as complete
MIN_SHARE = 0.6       # less than this is not a take of the line
PHRASE_WORDS = 4      # words used to find a line again in captions.json

MARKERS = {"chapter": ("chapter", "capítulo", "capitulo"), "screen": ("screen", "pantalla"),
           "graphic": ("graphic", "gráfico", "grafico")}


def norm(word):
    word = unicodedata.normalize("NFKD", word)
    word = "".join(c for c in word if not unicodedata.combining(c)).lower()
    return "".join(c for c in word if c.isalnum())


def words_of(text):
    return [w for w in (norm(t) for t in text.split()) if w]


def parse(text):
    """Spoken lines, chapters, Shorts and notes from script.md."""
    lines, chapters, shorts, notes = [], [], [], []
    open_short, para = None, []

    def flush():
        if para:
            spoken = " ".join(para).strip()
            if words_of(spoken):
                lines.append(spoken)
            para.clear()

    for raw in text.splitlines():
        s = raw.strip()
        tag = re.match(r"^(?:#+\s*)?\[\s*(/?)([^\]\s:\"]+)\s*:?\s*\"?([^\]\"]*)\"?\s*\](.*)$", s)
        if tag:
            flush()
            closing, name, inner, rest = tag.group(1), norm(tag.group(2)), tag.group(3).strip(), tag.group(4).strip()
            title = inner if inner else rest              # [SHORT "Title"] or [SCREEN] text after the tag
            if name == "short":
                if closing:
                    if open_short is not None:
                        shorts.append({"title": open_short[0], "first": open_short[1], "last": len(lines) - 1})
                        open_short = None
                else:
                    open_short = (title or f"Short {len(shorts) + 1}", len(lines))
            elif name in MARKERS["chapter"]:
                chapters.append({"title": title, "line": len(lines)})
            elif name in MARKERS["screen"] or name in MARKERS["graphic"]:
                kind = "screen" if name in MARKERS["screen"] else "graphic"
                notes.append({"kind": kind, "text": title, "line": len(lines)})
            continue
        if not s or s.startswith("#") or s.startswith(">"):
            flush()
            continue
        para.append(s.lstrip("-* ").strip())
    flush()
    if open_short is not None:
        shorts.append({"title": open_short[0], "first": open_short[1], "last": len(lines) - 1})
    return lines, chapters, shorts, notes


def flat_transcript(data):
    """[(start, end, normalized word, word as said)] from a Whisper-style JSON."""
    out = []
    for seg in data.get("segments", []):
        for w in seg.get("words", []):
            for piece in w["word"].split():
                n = norm(piece)
                if n:
                    out.append((float(w["start"]), float(w["end"]), n, piece))
    return out


def same(a, b):
    if a == b:
        return True
    return min(len(a), len(b)) >= 3 and SequenceMatcher(None, a, b).ratio() >= 0.8


def match_at(line, words, i, max_skip=2):
    """Greedy match of a line's words from transcript position i: (matched script words, last transcript index)."""
    j, matched, last = i, 0, None
    for k, sw in enumerate(line):
        found = None
        for d in range(max_skip + 1):
            if j + d < len(words) and same(sw, words[j + d][2]):
                found = j + d
                break
        if found is None:
            if k == 0:
                return 0, None
            continue                                      # the speaker left a word out or Whisper missed it
        matched += 1
        last, j = found, found + 1
    return matched, last


def takes_of(line, words):
    """Every take of a line: (first index, last index, share of the line said). Overlapping candidates keep the best."""
    found = []
    for i in range(len(words)):
        if not (same(line[0], words[i][2]) or (len(line) > 1 and same(line[1], words[i][2]))):
            continue
        start = i if same(line[0], words[i][2]) else None
        matched, last = match_at(line if start is not None else line[1:], words, i)
        if last is None:
            continue
        share = matched / len(line)
        found.append((i, last, share))
    found.sort(key=lambda t: (t[0], -t[2]))
    best = []
    for t in found:
        if best and t[0] <= best[-1][1]:
            # the more complete one wins; at equal share the tighter one (a line starting with "y" or "and" can
            # also match from the same word at the end of the line before, a couple of words early)
            if (t[2], -(t[1] - t[0])) > (best[-1][2], -(best[-1][1] - best[-1][0])):
                best[-1] = t
            continue
        best.append(t)
    return best


def align(lines, words):
    """For each line: the take kept (or None), the other takes, and false starts."""
    used = set()
    results = []
    for n, text in enumerate(lines):
        line = words_of(text)
        takes = [t for t in takes_of(line, words) if not used.intersection(range(t[0], t[1] + 1))]
        good = [t for t in takes if t[2] >= MIN_SHARE]
        complete = [t for t in good if t[2] >= KEEP_SHARE]
        kept = complete[-1] if complete else (max(good, key=lambda t: (t[2], t[0])) if good else None)
        if kept:
            used.update(range(kept[0], kept[1] + 1))
        others = [t for t in good if t is not kept]
        # a false start: two or more words of the line, then a restart of it within 15 s
        starts = [t for t in takes if t[2] < MIN_SHARE and t[1] - t[0] >= 1 and kept and t[1] < kept[0]
                  and words[kept[0]][0] - words[t[1]][1] <= 15]
        results.append({"line": n, "text": text, "kept": kept, "others": others, "false_starts": starts})
    for r in results:                                   # other takes and false starts never cover a kept take
        r["others"] = [t for t in r["others"] if not used.intersection(range(t[0], t[1] + 1))]
        r["false_starts"] = [t for t in r["false_starts"] if not used.intersection(range(t[0], t[1] + 1))]
    return results


def unscripted(words, results, min_words=2):
    """Runs of words that belong to no take, kept take or false start: [(first index, last index)]."""
    covered = set()
    for r in results:
        for t in ([r["kept"]] if r["kept"] else []) + r["others"] + r["false_starts"]:
            covered.update(range(t[0], t[1] + 1))
    runs, start = [], None
    for i in range(len(words) + 1):
        inside = i < len(words) and i not in covered
        if inside and start is None:
            start = i
        elif not inside and start is not None:
            if i - start >= min_words:
                runs.append((start, i - 1))
            start = None
    return runs


def span(words, t, kept_spans, pad=0.05):
    """A remove range for words t[0]..t[1], never reaching into a kept take."""
    s, e = words[t[0]][0] - pad, words[t[1]][1] + pad
    for ks, ke in kept_spans:
        if ke <= words[t[0]][0] + 1e-6:
            s = max(s, ke + 0.02)
        if ks >= words[t[1]][1] - 1e-6:
            e = min(e, ks - 0.02)
    return round(max(s, 0.0), 3), round(e, 3)


def phrase(words, t, from_end=False):
    piece = words[t[0]:t[1] + 1]
    piece = piece[-PHRASE_WORDS:] if from_end else piece[:PHRASE_WORDS]
    return " ".join(w[3] for w in piece)


def stamp(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("transcript")
    ap.add_argument("--cuts", default="cuts.json")
    ap.add_argument("--drop-unscripted", action="store_true", help="also remove talk that isn't in the script")
    a = ap.parse_args()

    lines, chapters, shorts, notes = parse(open(a.script, encoding="utf-8").read())
    if not lines:
        sys.exit(f"No spoken lines found in {a.script}.")
    words = flat_transcript(json.load(open(a.transcript, encoding="utf-8")))
    if not words:
        sys.exit(f"No words in {a.transcript}.")
    results = align(lines, words)
    extra = unscripted(words, results)
    kept_spans = [(words[r["kept"][0]][0], words[r["kept"][1]][1]) for r in results if r["kept"]]

    remove = []
    for r in results:
        for t in r["others"]:
            remove.append([*span(words, t, kept_spans), f"script: other take of line {r['line'] + 1}"])
        for t in r["false_starts"]:
            remove.append([*span(words, t, kept_spans), f"script: false start of line {r['line'] + 1}"])
    if a.drop_unscripted:
        for t in extra:
            remove.append([*span(words, t, kept_spans), "script: not in the script"])
    try:
        cuts = json.load(open(a.cuts, encoding="utf-8"))
    except FileNotFoundError:
        cuts = {}
    cuts["remove"] = [r for r in cuts.get("remove", []) if not (len(r) > 2 and str(r[2]).startswith("script:"))]
    cuts["remove"] += sorted(r for r in remove if r[1] > r[0])
    json.dump(cuts, open(a.cuts, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    by_line = {r["line"]: r for r in results}

    def first_said(n):
        k = by_line[n]["kept"] if n < len(lines) else None
        return phrase(words, k) if k else None

    ch_out = []
    if chapters and chapters[0]["line"] > 0:
        ch_out.append({"title": "Intro", "at": 0})
    missing_marks = []
    for c in chapters:
        p = first_said(c["line"]) if c["line"] < len(lines) else None
        if p:
            ch_out.append({"title": c["title"], "say": p})
        else:
            missing_marks.append(f'chapter "{c["title"]}"')
    if ch_out:
        json.dump(ch_out, open("chapters.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sh_out = []
    for s in shorts:
        k_first = by_line[s["first"]]["kept"] if s["first"] < len(lines) else None
        k_last = by_line[s["last"]]["kept"] if 0 <= s["last"] < len(lines) else None
        if k_first and k_last:
            sh_out.append({"title": s["title"], "say": phrase(words, k_first), "until": phrase(words, k_last, True)})
        else:
            missing_marks.append(f'Short "{s["title"]}"')
    if sh_out:
        json.dump(sh_out, open("shorts.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    note_out = [{"kind": n["kind"], "text": n["text"], "before": first_said(n["line"])} for n in notes
                if n["line"] < len(lines)]
    if note_out:
        json.dump(note_out, open("edit-notes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # the report
    order = [words[r["kept"][0]][0] for r in results if r["kept"]]
    out_of_order = sum(1 for x, y in zip(order, order[1:]) if y < x)
    missing = [r for r in results if not r["kept"]]
    rep = [f"# Script check: {a.script}", ""]
    rep.append(f"{len(lines)} lines: {len(lines) - len(missing)} found, {len(missing)} not said."
               + (f" {out_of_order} said out of order." if out_of_order else ""))
    rep.append("")
    for r in results:
        k = r["kept"]
        if k:
            state = "" if k[2] >= KEEP_SHARE else f" (incomplete: {k[2]:.0%} of the line)"
            rep.append(f"{r['line'] + 1}. kept {stamp(words[k[0]][0])}-{stamp(words[k[1]][1])}{state}: {r['text']}")
        else:
            rep.append(f"{r['line'] + 1}. NOT SAID: {r['text']}")
        for t in r["others"]:
            rep.append(f"    other take {stamp(words[t[0]][0])} ({t[2]:.0%}), removed")
        for t in r["false_starts"]:
            rep.append(f"    false start {stamp(words[t[0]][0])}: \"{phrase(words, t)}...\", removed")
    if extra:
        rep += ["", "Not in the script" + (" (removed):" if a.drop_unscripted else " (kept; ask the user):")]
        for t in extra:
            rep.append(f"  {stamp(words[t[0]][0])}-{stamp(words[t[1]][1])}: "
                       + " ".join(w[3] for w in words[t[0]:t[1] + 1]))
    if missing_marks:
        rep += ["", "Markers whose line wasn't said (no time for them): " + ", ".join(missing_marks)]
    open("script-report.md", "w", encoding="utf-8").write("\n".join(rep) + "\n")

    print(rep[2])
    print(f"Removed {len(remove)} range(s): other takes and false starts"
          + (", and talk not in the script." if a.drop_unscripted else "."))
    if missing:
        print("Not said (record again or rewrite):", "; ".join(f"line {r['line'] + 1}" for r in missing))
    if extra and not a.drop_unscripted:
        print(f"{len(extra)} stretch(es) of talk not in the script were kept: see script-report.md and ask the user.")
    print(f"Wrote {a.cuts}, script-report.md" + (", chapters.json" if ch_out else "") + (", shorts.json" if sh_out else "")
          + (", edit-notes.json" if note_out else "") + ". Next: cutplan.py build with --cuts " + a.cuts + ".")


if __name__ == "__main__":
    main()
