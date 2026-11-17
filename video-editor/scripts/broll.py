"""Finds the right B-roll photo or clip for each product the speaker names, and when it is named.

  python -I broll.py index <B-roll folder> [--out broll-index.json] [--sheet broll-sheet.png]
  python -I broll.py match --index broll-index.json --captions captions.json --product "Glow Serum" [--product ...]

index: lists every photo (.jpg .jpeg .png .webp) and clip (.mp4 .mov .m4v .mkv .webm) in the folder and its
subfolders, turns each file name and folder name into search words (lowercase, accents removed, camera names like
IMG_2041 ignored), reads each clip's length, and writes broll-index.json plus a numbered contact sheet with one
thumbnail per file (the middle frame of a clip). Look at the sheet: the numbers match the index.

match: for each product, finds every time it is said in the cut (captions.json from captions.py: times in the
finished video, accents and case ignored, "serum"/"serums" and "labial"/"labiales" count as the same word), and
ranks the B-roll files by how well their names match. It writes broll-matches.json (first mention, all mentions,
best files) and prints the candidates. A file name only suggests: when it doesn't settle it (no match, a tie, a
camera name), compare the contact sheet with a frame of the video where the product is shown, and show the user
the choice before rendering anything. Name B-roll files after the product to make this automatic.
Needs Python and FFmpeg; Pillow for the contact sheet (skipped with a message without it).
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

PHOTOS = {".jpg", ".jpeg", ".png", ".webp"}
CLIPS = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
NOISE = {"img", "image", "photo", "foto", "dsc", "pxl", "mvimg", "vid", "video", "clip", "copy", "copia", "final",
         "edit", "broll", "b", "roll", "kit", "the", "el", "la", "los", "las", "de", "del", "and", "y"}

sys.stdout.reconfigure(encoding="utf-8")


def words_of(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    out = []
    for w in re.split(r"[^a-z0-9]+", text):
        if not w or w in NOISE or (w.isdigit() and len(w) > 2):
            continue
        out.append(w)
    return out


def same_word(a, b):
    if a == b:
        return True
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True  # serum / serums, labial / labiales
    return min(len(a), len(b)) >= 5 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def clip_seconds(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return round(float(out), 2)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def thumbnail(path, kind, seconds, size):
    from PIL import Image

    if kind == "photo":
        img = Image.open(path)
        img = img.convert("RGB")
    else:
        at = (seconds or 0) / 2
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{at:.2f}", "-i", str(path), "-frames:v", "1", "-f", "image2pipe",
                              "-vcodec", "png", "-"], capture_output=True, timeout=120).stdout
        import io
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    img.thumbnail((size, size))
    return img


def contact_sheet(entries, root, out, size=240):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow is not installed: no contact sheet (pip install pillow in the face environment).")
        return False
    columns = 5
    rows = (len(entries) + columns - 1) // columns
    label_h = 34
    sheet = Image.new("RGB", (columns * size, rows * (size + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    font, plain = None, False
    for name in ("DejaVuSans.ttf", "arial.ttf", "Arial.ttf", "segoeui.ttf", "Helvetica.ttc"):
        try:
            font = ImageFont.truetype(name, 14)
            break
        except OSError:
            continue
    if font is None:  # the built-in font has no accents
        font, plain = ImageFont.load_default(), True
    for i, e in enumerate(entries):
        x, y = (i % columns) * size, (i // columns) * (size + label_h)
        try:
            img = thumbnail(root / e["file"], e["kind"], e.get("seconds"), size - 8)
            sheet.paste(img, (x + (size - img.width) // 2, y + (size - img.height) // 2))
        except Exception as error:  # an unreadable file still gets its number
            draw.text((x + 10, y + size // 2), f"can't read: {type(error).__name__}", fill="red", font=font)
        name = Path(e["file"]).name
        if plain:
            name = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
        tag = "clip " if e["kind"] == "clip" else ""
        draw.text((x + 6, y + size + 4), f"{e['n']}. {tag}{name[:30]}", fill="black", font=font)
    sheet.save(out)
    return True


def index(a):
    root = Path(a.folder)
    if not root.is_dir():
        sys.exit(f"{root} is not a folder.")
    entries = []
    for path in sorted(root.rglob("*")):
        ext = path.suffix.lower()
        if not path.is_file() or path.name.startswith(".") or ext not in PHOTOS | CLIPS:
            continue
        rel = path.relative_to(root)
        kind = "photo" if ext in PHOTOS else "clip"
        words = []
        for part in list(rel.parent.parts) + [path.stem]:
            words += [w for w in words_of(part) if w not in words]
        entries.append({"n": len(entries) + 1, "file": rel.as_posix(), "kind": kind, "words": words,
                        "seconds": clip_seconds(path) if kind == "clip" else None})
    if not entries:
        sys.exit(f"No photos or clips found in {root}.")
    json.dump({"folder": str(root.resolve()), "files": entries}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    made = contact_sheet(entries, root, a.sheet)
    photos = sum(e["kind"] == "photo" for e in entries)
    print(f"Indexed {len(entries)} files ({photos} photos, {len(entries) - photos} clips) in {a.out}"
          + (f"; contact sheet {a.sheet}." if made else "."))
    unnamed = [e for e in entries if not e["words"]]
    if unnamed:
        print(f"{len(unnamed)} files have only camera names (e.g. {unnamed[0]['file']}): match those by looking at the sheet.")


def mentions(captions, product):
    said = []
    for cap in captions:
        for start, end, text in cap.get("words", []):
            for w in words_of(text):
                said.append((start, end, w))
    want = words_of(product)
    if not want:
        return [], "empty"
    found = []
    for i in range(len(said)):  # all words of the name, in order, in a window of a few words
        j, k = i, 0
        while j < len(said) and k < len(want) and j - i < len(want) + 2:
            if same_word(said[j][2], want[k]):
                k += 1
            elif k == 0:
                break
            j += 1
        if k == len(want) and (not found or said[i][0] > found[-1] + 1.0):
            found.append(round(said[i][0], 2))
    if found:
        return found, "full"
    key = max(want, key=len)  # the most distinctive word alone, e.g. the brand
    loose = []
    for start, _, w in said:
        if len(key) >= 4 and same_word(w, key) and (not loose or start > loose[-1] + 1.0):
            loose.append(round(start, 2))
    return loose, "partial" if loose else "not said"


def score(product_words, file_words):
    if not product_words or not file_words:
        return 0.0
    hits = sum(any(same_word(p, f) for f in file_words) for p in product_words)
    return round(hits / len(product_words), 2)


def match(a):
    data = json.load(open(a.index, encoding="utf-8"))
    captions = json.load(open(a.captions, encoding="utf-8"))
    result = []
    for product in a.product:
        times, how = mentions(captions, product)
        want = words_of(product)
        ranked = sorted(({"n": e["n"], "file": e["file"], "kind": e["kind"], "score": score(want, e["words"])}
                         for e in data["files"]), key=lambda r: (-r["score"], r["kind"] != "photo", r["n"]))
        best = [r for r in ranked if r["score"] > 0][:5]
        tie = len(best) > 1 and best[0]["score"] == best[1]["score"]
        result.append({"product": product, "first_mention": times[0] if times else None, "mentions": times,
                       "mention_match": how, "candidates": best, "tie": tie})
        when = f"first said at {times[0]:.2f} s" if times else "not found in the captions"
        print(f"\n{product}: {when}" + (f" (matched by '{max(want, key=len)}' only)" if how == "partial" else "")
              + (f"; said {len(times)} times" if len(times) > 1 else ""))
        if not best:
            print("  No file name matches: look at the contact sheet and compare with a frame where it is shown.")
        for r in best:
            print(f"  {r['score']:.2f}  #{r['n']} {r['kind']:5} {r['file']}")
        if tie:
            print("  Tie: decide by looking at the contact sheet.")
    json.dump(result, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nWrote {a.out}. Show the user each product, the chosen file and when it appears before rendering.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index")
    i.add_argument("folder")
    i.add_argument("--out", default="broll-index.json")
    i.add_argument("--sheet", default="broll-sheet.png")
    m = sub.add_parser("match")
    m.add_argument("--index", default="broll-index.json")
    m.add_argument("--captions", default="captions.json")
    m.add_argument("--product", action="append", required=True, help="a product name as it is said; repeat for each")
    m.add_argument("--out", default="broll-matches.json")
    a = ap.parse_args()
    index(a) if a.cmd == "index" else match(a)


if __name__ == "__main__":
    main()
