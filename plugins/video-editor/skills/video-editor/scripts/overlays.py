"""Fourteen more graphics for educational videos (about AI or anything else), timed to what the speaker says:

  python -I overlays.py browser     page.json  --captions captions.json --size 1920x1080 --fps 25 [style] [--out ...]
  python -I overlays.py stats       stats.json --captions captions.json ...
  python -I overlays.py beforeafter ba.json    --captions captions.json ...
  python -I overlays.py checklist   list.json  --captions captions.json ...
  python -I overlays.py steps       steps.json --captions captions.json ...
  python -I overlays.py lowerthird  who.json   --captions captions.json ...
  python -I overlays.py quote       quote.json --captions captions.json ...
  python -I overlays.py countdown   count.json --captions captions.json ...
  python -I overlays.py ring        ring.json  --captions captions.json ...
  python -I overlays.py barchart    bars.json  --captions captions.json ...
  python -I overlays.py highlight   phrase.json --captions captions.json ...
  python -I overlays.py subscribe   sub.json   --captions captions.json ...
  python -I overlays.py chapter     chapter.json --captions captions.json ...
  python -I overlays.py notify      toasts.json --captions captions.json ...

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
  around without highlighting; look at the screenshot to find each box. A rough box is enough: it is fitted to the
  text or picture inside it (what differs from the page's background there), so the outline sits evenly around the
  words, not across the whole column ("fit": false keeps a box as given). Fitting needs Pillow (the cutout Python
  has it); without it the boxes stay as given and it says so.
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

checklist: two to five items that appear one by one as they're said, each with a number that turns into a tick
(the speaker says "three things" and then names or counts them). An item without a "text" is just its number:
1, 2, 3.
  {"title": "3 cosas", "start_say": "...", "end_say": "...",
   "items": [{"text": "Planifica", "say": "primero"}, {"text": "Empieza", "say": "segundo"}, {"say": "y tercero"}],
   "done": "HECHO", "done_say": "y listo"}
  The title is big, with its number in the accent colour. "done" (true for "DONE", or the word you want) slams a
  stamp onto the checklist at "done_say" (or "done_at"); without a time it comes after the last item.

steps: a row of 3 to 6 steps of a process ("step 1 of 4"). Each step lights up as it's said (the one before turns
into a tick), and a line fills between them.
  {"title": "El proceso", "start_say": "...", "end_say": "...",
   "steps": [{"label": "Investiga", "say": "primero"}, {"label": "Diseña", "say": "luego"}, {"label": "Lanza", "say": "por último"}]}

lowerthird: a name and a role on a bar that slides in from the left, for when someone is introduced.
  {"name": "Ana Pérez", "role": "Directora de IA", "start_say": "mi invitada", "seconds": 4}
quote: a quotation with its author, the words fading in as the speaker reads them out.
  {"quote": "La mejor manera de predecir el futuro es crearlo", "author": "Peter Drucker", "start_say": "como dijo",
   "author_say": "Drucker"}   (author_say or author_at: when the author appears; without it, after the quote)

countdown: big numbers counting down, each slamming in with a ring that empties, then an optional word.
  {"from": 3, "every": 1.0, "go": "¡YA!", "start_say": "en tres"}   (every: seconds per number, 1.0 if left out;
   go: the word after the last number, left out for none; say the numbers' own phrase in start_say so the 3 lands on it)
ring: one percentage (or any number out of a maximum) as a ring that fills and a number that counts up.
  {"value": 80, "max": 100, "suffix": " %", "label": "de acierto", "start_say": "...", "say": "un ochenta"}

barchart: two to five bars to compare, each growing as its value is said, the number counting up on it.
  {"title": "Tiempo ahorrado", "suffix": " h", "start_say": "...", "end_say": "...",
   "bars": [{"label": "Antes", "value": 10, "say": "diez horas"}, {"label": "Con IA", "value": 3, "say": "tres horas"}]}
  ("max" sets the full length of a bar, the biggest value if left out; "decimals", "prefix", "suffix" as for stats)
highlight: a short phrase the speaker stresses, big on a marker sweep ("esto es clave").
  {"text": "Esto es clave", "start_say": "esto es clave", "seconds": 2.5, "top": 0.4}   (top: 0 to 1 of the height)
subscribe: a subscribe button that gets pressed, then turns into "subscribed".
  {"text": "Suscríbete", "sub": "para más vídeos de IA", "done_text": "Suscrito", "start_say": "suscríbete", "seconds": 4}

chapter: the title of a section on screen, with its number and lines that grow out from it.
  {"number": 2, "label": "Capítulo", "title": "Tres ejemplos reales", "start_say": "vamos con los ejemplos",
   "seconds": 3}   (label and number are both optional; the titles can be the ones of chapters.json)
notify: message notifications stacking in a corner, each appearing as it's said (a phone filling with messages, emails
  arriving, an automation reporting back). Up to four at a time; a fifth pushes the first out.
  {"start_say": "...", "end_say": "...",
   "notifications": [{"app": "WhatsApp", "text": "Nuevo pedido de Ana", "say": "un pedido"},
                     {"app": "Gmail", "text": "Factura recibida", "say": "una factura"}]}

Writes <kind>-props.json for scripts/remotion/BrowserPage.tsx, StatTiles.tsx, BeforeAfter.tsx, Checklist.tsx, ProgressSteps.tsx, LowerThird.tsx, QuoteCard.tsx, Countdown.tsx, ProgressRing.tsx, BarChart.tsx, KeyPhrase.tsx or SubscribeReminder.tsx, ChapterTitle.tsx or Notifications.tsx and prints the
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
TEMPLATES = {"browser": "BrowserPage", "stats": "StatTiles", "beforeafter": "BeforeAfter",
             "checklist": "Checklist", "steps": "ProgressSteps",
             "lowerthird": "LowerThird", "quote": "QuoteCard",
             "countdown": "Countdown", "ring": "ProgressRing",
             "barchart": "BarChart", "highlight": "KeyPhrase", "subscribe": "SubscribeReminder",
             "chapter": "ChapterTitle", "notify": "Notifications"}


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


def fit_box(image_path, box, threshold=40):
    """The box shrunk to what's inside it: the pixels that differ from its own background (the most common colour
    on its edge) by more than `threshold` in brightness. None when there is nothing inside, or Pillow is missing."""
    try:
        from PIL import Image
    except ImportError:
        return None
    x, y, w, h = (int(round(v)) for v in box)
    with Image.open(image_path) as im:
        region = im.convert("L").crop((x, y, x + w, y + h))
    px = region.load()
    rw, rh = region.size
    edge = [px[i, 0] for i in range(rw)] + [px[i, rh - 1] for i in range(rw)] + \
           [px[0, j] for j in range(rh)] + [px[rw - 1, j] for j in range(rh)]
    background = max(set(edge), key=edge.count)
    xs, ys = [], []
    for j in range(rh):
        for i in range(rw):
            if abs(px[i, j] - background) > threshold:
                xs.append(i)
                ys.append(j)
    if not xs:
        return None
    return [x + min(xs), y + min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1]


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
    fitted_any = missing_pillow = False
    for i, h in enumerate(spec.get("highlight", [])):
        x, y, w, hh = (float(v) for v in h["box"])
        if h.get("fit", True) and os.path.exists(image_path):
            fitted = fit_box(image_path, [x, y, w, hh])
            if fitted:
                x, y, w, hh = (float(v) for v in fitted)
                fitted_any = True
            else:
                try:
                    import PIL  # noqa: F401
                except ImportError:
                    missing_pillow = True
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
    if missing_pillow:
        timer.problems.append("Pillow isn't installed in this Python: the highlight boxes are as given, not fitted to "
                              "the text (run it with the cutout Python, or pip install pillow).")
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


def checklist_props(spec, timer, fps):
    items = spec.get("items", [])
    if not 2 <= len(items) <= 5:
        raise ValueError("checklist needs 2 to 5 items: one is a title, more than five don't read in time.")
    frame = lambda s: int(round(s * fps))
    out, timeline = [], []
    for i, item in enumerate(items):
        t = timer.part(item, f"item {i + 1}")
        text = str(item.get("text", "")).strip()
        out.append({"text": text, "frame": frame(t)})
        timeline.append((t, f"{i + 1}. {text}" if text else f"{i + 1}"))
    body = {"title": spec.get("title", ""), "items": out, "doneText": "", "doneFrame": 0}
    last = max(o["frame"] for o in out) / fps + 0.8
    if spec.get("done"):
        t = timer.part({k: v for k, v in (("say", spec.get("done_say")), ("at", spec.get("done_at"))) if v is not None},
                       "the stamp")
        body["doneText"] = "DONE" if spec["done"] is True else str(spec["done"])
        body["doneFrame"] = frame(t)
        timeline.append((t, f'stamp "{body["doneText"]}"'))
        last = t + 1.0
    return body, last, timeline


def steps_props(spec, timer, fps):
    steps = spec.get("steps", [])
    if not 3 <= len(steps) <= 6:
        raise ValueError("steps needs 3 to 6 steps: two is a before and after, more than six don't fit on screen.")
    frame = lambda s: int(round(s * fps))
    out, timeline = [], []
    for i, step in enumerate(steps):
        t = timer.part(step, f"step {i + 1}")
        label = str(step.get("label", "")).strip()
        out.append({"label": label, "frame": frame(t)})
        timeline.append((t, f"step {i + 1}: {label}" if label else f"step {i + 1}"))
    return {"title": spec.get("title", ""), "steps": out}, max(o["frame"] for o in out) / fps + 1.0, timeline


def lowerthird_props(spec, timer, fps):
    name = str(spec.get("name", "")).strip()
    if not name:
        raise ValueError('lowerthird needs a "name".')
    role = str(spec.get("role", "")).strip()
    return ({"name": name, "role": role, "top": float(spec.get("top", 0))}, 2.0,
            [(0.0, f"{name}" + (f", {role}" if role else ""))])


def quote_props(spec, timer, fps):
    text = str(spec.get("quote", "")).strip()
    if not text:
        raise ValueError('quote needs a "quote".')
    frame = lambda s: int(round(s * fps))
    reading = 0.5 + 0.3 * len(text.split())             # the words appear over about this long
    t = timer.part({k: v for k, v in (("say", spec.get("author_say")), ("at", spec.get("author_at"))) if v is not None},
                   "the author", first=reading + 0.3)
    return ({"quote": text, "author": str(spec.get("author", "")).strip(), "authorFrame": frame(t),
             "wordFrames": frame(reading)}, t + 1.0,
            [(0.4, "the quote starts to appear"), (t, f'author: {spec.get("author", "")}')])


def countdown_props(spec, timer, fps):
    start = int(spec.get("from", 3))
    if not 2 <= start <= 10:
        raise ValueError('countdown "from" must be 2 to 10: one number is not a countdown, more than ten drags.')
    every = float(spec.get("every", 1.0))
    if not 0.4 <= every <= 2.0:
        raise ValueError('countdown "every" is the seconds per number: 0.4 to 2.')
    frame = lambda s: int(round(s * fps))
    first, step = frame(0.3), frame(every)               # whole frames per number, so the pace never wobbles
    numbers = [{"text": str(start - i), "frame": first + i * step} for i in range(start)]
    go = str(spec.get("go", "")).strip()
    if go:
        numbers.append({"text": go, "frame": first + start * step})
    last = 0.3 + (start + (1 if go else 0)) * every
    timeline = [(n["frame"] / fps, n["text"]) for n in numbers]
    return {"numbers": numbers, "everyFrames": frame(every)}, last, timeline


def ring_props(spec, timer, fps):
    if "value" not in spec:
        raise ValueError('ring needs a "value".')
    value, maximum = float(spec["value"]), float(spec.get("max", 100))
    if maximum <= 0 or not 0 <= value <= maximum:
        raise ValueError('ring: "value" must be between 0 and "max" (100 if left out).')
    t = timer.part({k: v for k, v in (("say", spec.get("say")), ("at", spec.get("at"))) if v is not None}, "the number")
    decimals = int(spec.get("decimals", 0))
    final = number_text(value, decimals, spec.get("prefix", ""), spec.get("suffix", ""))
    return ({"value": value, "max": maximum, "decimals": decimals, "prefix": spec.get("prefix", ""),
             "suffix": spec.get("suffix", ""), "label": spec.get("label", ""), "frame": int(round(t * fps))},
            t + 1.6, [(t, f'{final} {spec.get("label", "")}'.strip())])


def barchart_props(spec, timer, fps):
    bars = spec.get("bars", [])
    if not 2 <= len(bars) <= 5:
        raise ValueError("barchart needs 2 to 5 bars: one bar is a number (use ring or stats), more than five are hard to read.")
    frame = lambda s: int(round(s * fps))
    values = []
    for i, b in enumerate(bars):
        if "value" not in b:
            raise ValueError(f"bar {i + 1} needs a value.")
        values.append(float(b["value"]))
        if values[-1] < 0:
            raise ValueError(f"bar {i + 1}: a negative value can't be drawn as a bar.")
    maximum = float(spec["max"]) if "max" in spec else max(values)
    if maximum <= 0 or max(values) > maximum:
        raise ValueError('barchart: "max" must be above zero and not below the biggest value.')
    decimals, prefix, suffix = int(spec.get("decimals", 0)), spec.get("prefix", ""), spec.get("suffix", "")
    out, timeline = [], []
    for i, b in enumerate(bars):
        t = timer.part(b, f"bar {i + 1}")
        out.append({"label": b.get("label", ""), "value": values[i], "frame": frame(t)})
        timeline.append((t, f'{b.get("label", "")}: {number_text(values[i], decimals, prefix, suffix)}'))
    body = {"title": spec.get("title", ""), "bars": out, "max": maximum, "decimals": decimals, "prefix": prefix,
            "suffix": suffix}
    return body, max(o["frame"] for o in out) / fps + 1.2, timeline


def highlight_props(spec, timer, fps):
    text = str(spec.get("text", "")).strip()
    if not text:
        raise ValueError('highlight needs a "text".')
    top = float(spec.get("top", 0))
    if not 0 <= top < 1:
        raise ValueError('highlight "top" is a fraction of the height: 0 (the default place) or between 0 and 1.')
    return {"text": text, "top": top}, 1.0, [(0.0, f'"{text}"')]


def subscribe_props(spec, timer, fps):
    text = str(spec.get("text", "")).strip() or "Suscríbete"
    done = str(spec.get("done_text", "")).strip()
    press = int(round(1.2 * fps))
    return ({"text": text, "sub": str(spec.get("sub", "")).strip(), "doneText": done, "pressFrame": press},
            3.0, [(0.0, f"button: {text}")] + ([(1.2, f"pressed: {done}")] if done else []))


def chapter_props(spec, timer, fps):
    title = str(spec.get("title", "")).strip()
    if not title:
        raise ValueError('chapter needs a "title".')
    if len(title) > 60:
        timer.problems.append(f"The title is {len(title)} characters: it wraps onto several lines; a short one reads better.")
    number = spec.get("number")
    label = str(spec.get("label", "")).strip()
    return ({"title": title, "number": "" if number is None else str(number), "label": label}, 1.0,
            [(0.0, " ".join(x for x in (label, "" if number is None else str(number), title) if x))])


def notify_props(spec, timer, fps):
    toasts = spec.get("notifications", [])
    if not 2 <= len(toasts) <= 8:
        raise ValueError("notify needs 2 to 8 notifications: one is a pop-up, more than eight don't read in time.")
    frame = lambda s: int(round(s * fps))
    out, timeline = [], []
    for i, n in enumerate(toasts):
        text = str(n.get("text", "")).strip()
        if not text:
            raise ValueError(f"notification {i + 1} needs a text.")
        t = timer.part(n, f"notification {i + 1}")
        out.append({"app": str(n.get("app", "")).strip(), "text": text, "frame": frame(t)})
        timeline.append((t, f'{n.get("app", "")}: {text}'.strip(": ")))
    return {"notifications": out}, max(o["frame"] for o in out) / fps + 1.5, timeline


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
        elif a.kind == "chapter":
            body, last, timeline = chapter_props(spec, timer, fps)
        elif a.kind == "notify":
            body, last, timeline = notify_props(spec, timer, fps)
        elif a.kind == "barchart":
            body, last, timeline = barchart_props(spec, timer, fps)
        elif a.kind == "highlight":
            body, last, timeline = highlight_props(spec, timer, fps)
        elif a.kind == "subscribe":
            body, last, timeline = subscribe_props(spec, timer, fps)
        elif a.kind == "countdown":
            body, last, timeline = countdown_props(spec, timer, fps)
        elif a.kind == "ring":
            body, last, timeline = ring_props(spec, timer, fps)
        elif a.kind == "lowerthird":
            body, last, timeline = lowerthird_props(spec, timer, fps)
        elif a.kind == "quote":
            body, last, timeline = quote_props(spec, timer, fps)
        elif a.kind == "steps":
            body, last, timeline = steps_props(spec, timer, fps)
        elif a.kind == "checklist":
            body, last, timeline = checklist_props(spec, timer, fps)
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
