"""The words for the puppet video's captions: exactly the script's words, timed to the voice.

  python -I captionwords.py puppet/puppet-props.json [--transcript voice-tr.json] [--out puppet/words.json]

Whisper is good at timing but rewrites what it hears ("Hmm... a croissant" came out as "I'm a croissant", "four
pounds fifty" as "£4 .50"), and a video that teaches a language has to show the text as written. So the words come
from the turns in puppet-props.json, and the times from:
  --transcript   a Whisper transcript of voice.wav (word times): each script word takes the time of the matching
                 word (compared without accents, case or punctuation); words in between are spread evenly;
  otherwise      each turn's length, shared out by the length of each word (rougher, but fine for a synthetic voice,
                 which speaks evenly).
Writes words.json in Whisper's format, for the video editor's captions.py with --on-cut. Standard library only.
"""
import argparse
import json
import sys
import unicodedata
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding="utf-8")


def norm(word):
    word = unicodedata.normalize("NFKD", word)
    word = "".join(c for c in word if not unicodedata.combining(c)).lower()
    return "".join(c for c in word if c.isalnum())


def spread(words, start, end):
    """Times for words over [start, end], by their length (letters + 1 for the gap)."""
    weights = [len(w) + 1 for w in words]
    total = sum(weights) or 1
    out, t = [], start
    for w, k in zip(words, weights):
        d = (end - start) * k / total
        out.append((w, round(t, 3), round(t + d * 0.9, 3)))
        t += d
    return out


def timed_from_transcript(words, start, end, heard):
    """Times for the script words of one turn from the transcript's words inside [start, end]."""
    inside = [h for h in heard if h[0] >= start - 0.15 and h[1] <= end + 0.15]
    a = [norm(w) for w in words]
    b = [norm(h[2]) for h in inside]
    times = [None] * len(words)
    for block in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            times[block.a + k] = (inside[block.b + k][0], inside[block.b + k][1])
    # fill the gaps evenly between the known times
    out, i = [], 0
    while i < len(words):
        if times[i]:
            out.append((words[i], round(times[i][0], 3), round(times[i][1], 3)))
            i += 1
            continue
        j = i
        while j < len(words) and not times[j]:
            j += 1
        left = out[-1][2] if out else start
        right = times[j][0] if j < len(words) else end
        out += spread(words[i:j], left, max(right, left + 0.05 * (j - i)))
        i = j
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("props")
    ap.add_argument("--transcript")
    ap.add_argument("--out", default="words.json")
    a = ap.parse_args()

    props = json.load(open(a.props, encoding="utf-8"))
    heard = []
    if a.transcript:
        for seg in json.load(open(a.transcript, encoding="utf-8")).get("segments", []):
            for w in seg.get("words", []):
                heard.append((float(w["start"]), float(w["end"]), w["word"]))
    out, matched, total = [], 0, 0
    for turn in props["turns"]:
        words = turn["text"].split()
        timed = timed_from_transcript(words, turn["start"], turn["end"], heard) if heard else \
            spread(words, turn["start"], turn["end"])
        if heard:
            inside = {norm(h[2]) for h in heard if turn["start"] - 0.15 <= h[0] and h[1] <= turn["end"] + 0.15}
            matched += sum(1 for w in words if norm(w) in inside)
        total += len(words)
        out += [{"word": " " + w, "start": s, "end": max(e, s + 0.05)} for w, s, e in timed]
    json.dump({"segments": [{"words": out}]}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    how = f"times from the transcript ({matched} of {total} words matched)" if heard else "times shared out by word length"
    print(f"Wrote {a.out}: {len(out)} words, as written in the script, {how}.")


if __name__ == "__main__":
    main()
