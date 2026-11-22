"""A reusable list of word fixes, saved once and applied to every video.

  python -I wordfixes.py add "cupillon" "goupillon"      remember that "cupillon" is really "goupillon"
  python -I wordfixes.py list                            show the list
  python -I wordfixes.py remove "cupillon"
  options: --file <path>   a different file (default ~/.video-editor/word-fixes.json)

Transcribers misspell brand names, product names and foreign words ("sefora" for Sephora, "cupillon" for the French
"goupillon"), and they do it the same way in every video. Correcting it per video (captions.py --fix fixes.json)
means correcting the same word again and again, so the corrections are kept in the user's own settings file, outside
the skill, where an update never touches them. captions.py applies the list to every video by default (a video's own
--fix file wins when both fix the same word; --no-personal-fixes turns the list off).

The list is also a vocabulary: with Whisper, transcribe.py hands the right spellings to the model as a hint
(--initial_prompt), so it often writes them correctly the first time. Parakeet ignores hints, so there the list only
corrects afterwards. Matching ignores case, accents and punctuation and can span several words, as --fix does.
Standard library only.
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

PATH = os.path.join(os.path.expanduser("~"), ".video-editor", "word-fixes.json")


def read(path=PATH):
    """The saved list, or {} if there is none. A file that isn't a JSON object stops with a clear message."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as error:
        sys.exit(f"{path} isn't valid JSON ({error}). Fix it or delete it; the list is only a convenience.")
    if not isinstance(data, dict):
        sys.exit(f'{path} must be an object like {{"cupillon": "goupillon"}}.')
    return {str(k): str(v) for k, v in data.items()}


def write(fixes, path=PATH):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(fixes.items(), key=lambda kv: kv[0].lower())), f, ensure_ascii=False, indent=1)
        f.write("\n")


def load(video_fixes=None, personal=PATH):
    """The personal list with a video's own fixes on top (the video's wins). video_fixes: a path, a dict or None."""
    merged = dict(read(personal))
    if isinstance(video_fixes, str):
        with open(video_fixes, encoding="utf-8") as f:
            video_fixes = json.load(f)
    merged.update(video_fixes or {})
    return merged


def add(heard, right, path=PATH):
    """Saves heard -> right. Returns the pair it replaced, or None."""
    heard, right = heard.strip(), right.strip()
    if not heard or not right:
        raise ValueError("Both the word as written and the right word are needed.")
    if heard.lower() == right.lower():
        raise ValueError(f'"{heard}" and "{right}" are the same word, apart from the case.')
    fixes = read(path)
    existing = next((k for k in fixes if k.lower() == heard.lower()), None)
    old = fixes.pop(existing) if existing else None
    fixes[heard] = right
    write(fixes, path)
    return old


def remove(heard, path=PATH):
    fixes = read(path)
    key = next((k for k in fixes if k.lower() == heard.strip().lower()), None)
    if key is None:
        return False
    del fixes[key]
    write(fixes, path)
    return True


def vocabulary(fixes, limit=40):
    """The right spellings, each once, as a short text for Whisper's initial prompt. Longer phrases first would only
    crowd out names, so the order is the list's own; capped, because a prompt is only a hint."""
    seen, words = set(), []
    for right in fixes.values():
        text = right.rstrip("|").strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            words.append(text)
    return ", ".join(words[:limit])


def hint_for(engine, given, fixes):
    """The Whisper initial prompt: the one the caller gave, else the list's right spellings, else None. Parakeet
    takes no prompt, so it gets None."""
    if engine != "whisper":
        return None
    return given or vocabulary(fixes) or None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("add", "list", "remove"))
    ap.add_argument("words", nargs="*", help='add: "<as written>" "<right>"; remove: "<as written>"')
    ap.add_argument("--file", default=PATH)
    a = ap.parse_args()
    if a.action == "list":
        fixes = read(a.file)
        if not fixes:
            print(f"No word fixes saved yet ({a.file}).")
        for heard, right in fixes.items():
            print(f'  "{heard}" -> "{right}"')
        return
    if a.action == "add":
        if len(a.words) != 2:
            sys.exit('add needs two words: wordfixes.py add "cupillon" "goupillon"')
        try:
            old = add(a.words[0], a.words[1], a.file)
        except ValueError as error:
            sys.exit(str(error))
        print(f'Saved: "{a.words[0]}" -> "{a.words[1]}"' + (f' (it was "{old}")' if old else "") + f" in {a.file}")
        return
    if len(a.words) != 1:
        sys.exit('remove needs one word: wordfixes.py remove "cupillon"')
    print("Removed." if remove(a.words[0], a.file) else f'"{a.words[0]}" wasn\'t in the list.')


if __name__ == "__main__":
    main()
