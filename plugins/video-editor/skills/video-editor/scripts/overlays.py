"""Three more graphics for educational videos (about AI or anything else), timed to what the speaker says:

  python -I overlays.py browser     page.json  --captions captions.json --size 1920x1080 --fps 25 [style] [--out ...]
  python -I overlays.py stats       stats.json --captions captions.json ...
  python -I overlays.py beforeafter ba.json    --captions captions.json ...

Every spec has "start_say"/"end_say" (phrases; or "start"/"end" in seconds, or "seconds" for the length), and each
timed part has "say" (it happens 0.2 s before that phrase) or "at" (seconds after the graphic starts). Style options:
--accent, --font, --font-file, --background (or "transparent" to lay it over the speaker), --background2.

browser: a real web page in a browser window, scrolling, with boxes that highlight what's mentioned.
  {"image": "pages/news.png",         a full-page screenshot inside the Remotion project's public folder (see
                                      references/graphics.md, Web page, for taking one); a public page only
   "url": "anthropic.com/news",       shown in the address bar
   "start_say": "...", "end_say": "...",
   "scroll": [{"to": 0.4, "say": "más abajo"}],                  to: how far down the page, 0 (top) to 1 (bottom)
   "highlight": [{"box": [120, 640, 900, 160], "say": "este titular"}]}   box in the screenshot's own pixels
  A highlight that would be out of view scrolls the page to it first, so "scroll" is only needed for moving
  around without highlighting; look at the screenshot to find each box.
stats: two to four numbers that belong together, each counting up as it's said.
  {"title": "Con IA", "start_say": "...", "end_say": "...",
   "tiles": [{"value": 40, "suffix": " %", "label": "más rápido", "say": "un cuarenta"},
             {"value": 3, "suffix": " h", "label": "ahorradas a la semana", "say": "tres horas"},
             {"value": 2.5, "decimals": 1, "prefix": "x", "label": "más ideas", "say": "el doble y medio"}]}
beforeafter: a before and an after, the after revealed by a sweep as it's said. Each side is an image or a text
(a weak prompt and a good one, a draft and the AI's version).
  {"start_say": "...", "end_say": "...", "reveal_say": "y así queda",
   "before": {"label": "Antes", "text": "Escribe un post"},
   "after": {"label": "Después", "image": "img/after.png"}}

Writes <kind>-props.json for scripts/remotion/BrowserPage.tsx, StatTiles.tsx or BeforeAfter.tsx and prints the
timeline and how to render and place it. These graphics make no sound: nothing on screen would. Standard library only.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chapters import find_phrase, flat_words  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

LEAD = 0.2
GAP = 0.8
TAIL = 2.0
TEMPLATES = {"browser": "BrowserPage", "stats": "StatTiles", "beforeafter": "BeforeAfter"}


def stamp(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def png_size(path):
    """(width, height) of a PNG, read from its header."""
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG: save the screenshot as PNG.")
    return struct.unpack(">II", head[16:24])


class Timer:
    """Resolves a spec's start, end and the "say"/"at" of each part to seconds."""

    def __init__(self, spec, captions):
        self.flat = flat_words(captions) if captions else []
        self.problems = []
        if "start" in spec:
            self.start = float(spec["start"])
        elif "start_say" in spec:
            t = find_phrase(self.flat, spec["start_say"]) if self.flat else None
            if t is None:
                raise ValueError(f'"{spec["start_say"]}" (start_say) is not said in captions.json.')
            self.start = max(0.0, t - LEAD)
        else:
            raise ValueError('The spec needs "start" (seconds) or "start_say" (a phrase).')
        self.previous = 0.0

    def part(self, item, name, first=0.4):
        """Seconds after the start for one timed part; parts without a time follow the one before."""
        t = None
        if "at" in item:
            t = float(item["at"])
        elif "say" in item:
            found = find_phrase(self.flat, item["say"], after=self.start - 0.05) if self.flat else None
            if found is None:
                self.problems.append(f'"{item["say"]}" ({name}) is not said after the graphic starts: timed after the one before.')
            else:
                t = found - self.start - LEAD
        if t is None:
            t = self.previous + GAP if self.previous else first
        t = max(t, 0.0)
        self.previous = t
        return t

    def length(self, spec, last):
        if "end" in spec:
            length = float(spec["end"]) - self.start
        elif "end_say" in spec:
            t = find_phrase(self.flat, spec["end_say"], after=self.start) if self.flat else None
            if t is None:
                raise ValueError(f'"{spec["end_say"]}" (end_say) is not said after the graphic starts.')
            length = t - self.start
        elif "seconds" in spec:
            length = float(spec["seconds"])
        else:
            length = last + TAIL
        if length < last + 1.0:
            self.problems.append(f"It would end {max(0, last + 1.0 - length):.1f} s too soon after its last part: made longer.")
            length = last + 1.5
        return round(length, 3)


def browser_view(width, height):
    """(window width, visible page height) of BrowserPage.tsx's window, for this video size: keep in step with it."""
    vertical = height > width
    font = round(min(width, height) / 20)
    win_w = width * (0.9 if vertical else 0.8)
    win_h = height * (0.7 if vertical else 0.84)
    return win_w, win_h - font * 1.4


def browser_props(spec, timer, fps, public=".", width=1920, height=1080):
    if not spec.get("image"):
        raise ValueError('browser needs "image": a full-page screenshot in the Remotion project\'s public folder.')
    image_path = os.path.join(public, spec["image"])
    page_w, page_h = png_size(image_path) if os.path.exists(image_path) else (spec.get("imageWidth"), spec.get("imageHeight"))
    if not page_w:
        raise ValueError(f"{image_path} not found: run from the Remotion project's folder, or give --public, or "
                         '"imageWidth" and "imageHeight".')
    frame = lambda s: int(round(s * fps))
    timeline, scroll, boxes = [], [{"frame": frame(0.3), "to": 0.0}], []
    for i, s in enumerate(spec.get("scroll", [])):
        t = timer.part(s, f"scroll {i + 1}")
        scroll.append({"frame": frame(t), "to": min(1.0, max(0.0, float(s["to"])))})
        timeline.append((t, f"scrolls to {round(float(s['to']) * 100)} % of the page"))
    win_w, view_h = browser_view(width, height)
    scale = win_w / page_w
    max_scroll = max(0.0, page_h * scale - view_h)
    for i, h in enumerate(spec.get("highlight", [])):
        x, y, w, hh = (float(v) for v in h["box"])
        if not (0 <= x < page_w and 0 <= y < page_h):
            timer.problems.append(f"highlight {i + 1} is outside the {page_w}x{page_h} screenshot.")
        t = timer.part(h, f"highlight {i + 1}")
        f = frame(t)
        current = max((st for st in scroll if st["frame"] <= f), key=lambda st: st["frame"])["to"]
        top, bottom = y * scale, (y + hh) * scale
        seen = current * max_scroll
        if max_scroll and (top < seen + view_h * 0.05 or bottom > seen + view_h * 0.95):
            to = min(1.0, max(0.0, ((top + bottom) / 2 - view_h / 2) / max_scroll))
            scroll.append({"frame": f, "to": round(to, 4)})
            timeline.append((t, f"scrolls to the box ({round(to * 100)} % of the page)"))
        boxes.append({"frame": f, "x": x, "y": y, "w": w, "h": hh})
        timeline.append((t, f"highlights the box at {int(x)},{int(y)}"))
    last = max([s["frame"] for s in scroll] + [b["frame"] for b in boxes]) / fps
    return {"image": spec["image"], "url": spec.get("url", ""), "pageWidth": page_w, "pageHeight": page_h,
            "scroll": sorted(scroll, key=lambda s: s["frame"]), "boxes": boxes}, last, timeline


def number_text(value, decimals=0, prefix="", suffix=""):
    """Spanish-style number: thousands with a dot, decimals with a comma."""
    text = f"{value:,.{decimals}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefix}{text}{suffix}"


def stats_props(spec, timer, fps):
    tiles = spec.get("tiles", [])
    if not 2 <= len(tiles) <= 4:
        raise ValueError("stats needs 2 to 4 tiles: one number is a title, five don't read in time.")
    frame = lambda s: int(round(s * fps))
    out, timeline = [], []
    for i, tile in enumerate(tiles):
        t = timer.part(tile, f"tile {i + 1}")
        decimals = int(tile.get("decimals", 0))
        final = number_text(float(tile["value"]), decimals, tile.get("prefix", ""), tile.get("suffix", ""))
        out.append({"value": float(tile["value"]), "decimals": decimals, "prefix": tile.get("prefix", ""),
                    "suffix": tile.get("suffix", ""), "label": tile.get("label", ""), "frame": frame(t)})
        timeline.append((t, f'{final} {tile.get("label", "")}'))
    return {"title": spec.get("title", ""), "tiles": out}, max(o["frame"] for o in out) / fps + 0.8, timeline


def beforeafter_props(spec, timer, fps):
    for side in ("before", "after"):
        s = spec.get(side, {})
        if not (s.get("text") or s.get("image")):
            raise ValueError(f'beforeafter needs "{side}" with a "text" or an "image".')
    t = timer.part({k: v for k, v in (("say", spec.get("reveal_say")), ("at", spec.get("reveal_at"))) if v is not None},
                   "the reveal", first=1.2)
    side = lambda s: {"label": s.get("label", ""), "text": s.get("text", ""), "image": s.get("image", "")}
    return ({"before": side(spec["before"]), "after": side(spec["after"]), "reveal": int(round(t * fps)),
             "revealFrames": int(round(0.6 * fps))}, t + 0.6, [(t, "the after sweeps in")])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=sorted(TEMPLATES))
    ap.add_argument("spec")
    ap.add_argument("--captions", help="captions.json of the finished cut (needed for phrases)")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=float, default=25)
    ap.add_argument("--public", default="public", help="the Remotion project's public folder (to read a screenshot's size)")
    ap.add_argument("--accent", default="#FF4F8B")
    ap.add_argument("--font", default="sans-serif")
    ap.add_argument("--font-file", default="")
    ap.add_argument("--background", default="#1B1033", help='"transparent" to lay it over the speaker')
    ap.add_argument("--background2", default="#0E2A47")
    ap.add_argument("--out")
    a = ap.parse_args()
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    captions = []
    if a.captions:
        with open(a.captions, encoding="utf-8") as f:
            captions = json.load(f)
    width, height = (int(v) for v in a.size.lower().split("x"))
    fps = int(a.fps) if float(a.fps).is_integer() else a.fps
    try:
        timer = Timer(spec, captions)
        if a.kind == "browser":
            body, last, timeline = browser_props(spec, timer, fps, a.public, width, height)
        elif a.kind == "stats":
            body, last, timeline = stats_props(spec, timer, fps)
        else:
            body, last, timeline = beforeafter_props(spec, timer, fps)
        seconds = timer.length(spec, last)
    except ValueError as error:
        sys.exit(str(error))
    props = {"fps": fps, "width": width, "height": height, "seconds": seconds,
             "fontSize": round(min(width, height) / 20), "accentColor": a.accent, "font": a.font,
             "fontFile": a.font_file, "background": a.background, "background2": a.background2, **body}
    out = a.out or f"{a.kind}-props.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(props, f, indent=2, ensure_ascii=False)
    start = timer.start
    print(f"{a.kind} from {stamp(start)} to {stamp(start + seconds)} in the video ({seconds:.1f} s):")
    for t, what in sorted(timeline):
        print(f"  {stamp(start + t)}  {what}")
    for p in timer.problems:
        print("  NOTE: " + p)
    template = TEMPLATES[a.kind]
    print(f"Wrote {out}. Render: npx remotion render src/index.ts {template} out/{a.kind}.mov --props={out}"
          + (" --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png"
             if a.background == "transparent" else ""))
    print(f"Then place it from {start:.2f} s: -itsoffset {start:.3f} and overlay=enable='between(t,{start:.3f},"
          f"{start + seconds:.3f})':eof_action=pass")


if __name__ == "__main__":
    main()
