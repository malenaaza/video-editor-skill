"""An animated explanation for part of an educational video: boxes, arrows and a moving dot that show how
something works (how an MCP connects Claude to Gmail, how a request travels...), each piece appearing as the
speaker names it.

  python -I explainer.py explainer.json --captions captions.json --size 1920x1080 --fps 25
         [--font "Montserrat" --font-file fonts/Montserrat-Bold.ttf] [--palette "#FF4F8B,#7C5CFF,#22C3A6"
         --background "#1B1033" --background2 "#0E2A47" --accent "#FF4F8B" --line "#FFFFFF"] [--out explainer-props.json]

explainer.json is written by Claude from the script's [GRAPHIC] note and the transcript:
  {"title": "Cómo funciona un MCP",
   "start_say": "os enseño cómo funciona",          where the graphic starts (or "start": seconds)
   "end_say": "y así de fácil",                     where it ends (or "end": seconds, or "seconds": length)
   "nodes": [{"id": "claude", "label": "Claude", "icon": "🤖", "say": "Claude"},   (optional "color" per box)
             {"id": "mcp", "label": "Servidor MCP", "say": "un servidor MCP"},
             {"id": "gmail", "label": "Gmail", "icon": "📧", "say": "tu Gmail"}],
   "links": [{"from": "claude", "to": "mcp", "label": "pide", "say": "le pide"},
             {"from": "mcp", "to": "gmail", "say": "y este habla con"}],
   "flows": [{"path": ["claude", "mcp", "gmail", "mcp", "claude"], "say": "y vuelve con la respuesta"}],
   "layout": "auto"}
Each node, link and flow appears when the speaker says its "say" phrase (looked up in captions.json, accents and
case ignored, after the graphic starts), or "at" seconds after the graphic starts. One with neither appears 0.6 s
after the one before it. A link never appears before its two boxes, nor a flow before its path. A phrase that isn't
found is said, and that piece is timed like one with neither. layout: "row" (left to right), "column" (top to
bottom) or "auto" (a row in a wide video, a column in a vertical one). Up to 6 boxes.

It also writes explainer-sfx.wav (unless --no-sounds), the graphic's sound effects timed to its frames, from the free
sounds in scripts/sfx/: a pop as each box appears, a soft whoosh as each arrow draws, a whoosh as the dot sets off, a
light tick each time it reaches a box and a sparkle when it arrives. It is as long as the graphic: mix it under the
voice from the graphic's start, like the other sound effects (references/sound.md).

Writes the props for scripts/remotion/Explainer.tsx: every position in pixels and every time in frames from the
graphic's start, so the template only draws. Each box takes the next colour of --palette (the brand's colours, or a
lively default), with white or dark text, whichever reads better on it. Prints when each piece appears, the render
command and how to put it on the video. Standard library only.
"""
import argparse
import array
import json
import math
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chapters import find_phrase, flat_words  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

GAP = 0.6         # seconds between pieces with no time of their own
TAIL = 2.5        # seconds the finished diagram stays when no end is given
DRAW = 0.5        # seconds an arrow takes to draw
FLOW = 1.8        # seconds the dot takes along a flow's whole path
MAX_NODES = 6
PALETTE = "#FF4F8B,#7C5CFF,#22C3A6,#FFB020,#3BA9FF,#FF7A45"  # pink, violet, teal, amber, blue, orange


def readable_text(colour):
    """White when it reads well on the colour, otherwise near-black. The labels are large and bold, so WCAG's 3:1
    for large text is enough; white on the brand's pink or violet looks livelier than black, which plain "most
    contrast" would pick."""
    c = colour.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return "#FFFFFF"
    lin = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    luminance = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return "#FFFFFF" if 1.05 / (luminance + 0.05) >= 3.0 else "#1A1A1A"


def stamp(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def layout(nodes, width, height, mode="auto", title=True, link_label=0):
    """Box positions and sizes: {id: (cx, cy, w, h)}, the font size and the layout used. Boxes are spread evenly,
    never overlap and stay inside the frame, with room between them for the arrows and their labels (link_label is
    the longest arrow label, in characters); the font shrinks when it doesn't all fit."""
    if mode == "auto":
        mode = "row" if width >= height else "column"
    n = len(nodes)
    font = round(min(width, height) / 17)
    top = height * (0.22 if title else 0.08)
    while True:
        h = font * 2.3
        sizes = [max(font * 4.2, min(len(node["label"]) * font * 0.62 + font * 1.6
                                     + (font * 1.3 if node.get("icon") else 0), width * 0.8)) for node in nodes]
        if mode == "row":
            gap = max(font * 2.6, link_label * font * 0.55 * 0.62 + font * 1.4)  # an arrow, and its label above it
            room = width * 0.92
            if sum(sizes) + gap * (n - 1) <= room or font <= 18:
                break
        else:
            gap = font * 2.2
            room = height - top - height * 0.08
            if n * h + gap * (n - 1) <= room or font <= 18:
                break
        font = round(font * 0.9)
    boxes = {}
    if mode == "row":
        total = sum(sizes) + gap * (n - 1)
        x = (width - total) / 2
        cy = top + (height - top) * 0.42
        for node, w in zip(nodes, sizes):
            boxes[node["id"]] = (round(x + w / 2), round(cy), round(w), round(h))
            x += w + gap
    else:
        step = (room - h) / max(1, n - 1) if n > 1 else 0
        step = min(step, h + gap * 2.2)
        total = h + step * (n - 1)
        y = top + (room - total) / 2 + h / 2
        for node, w in zip(nodes, sizes):
            boxes[node["id"]] = (round(width / 2), round(y), round(w), round(h))
            y += step
    return boxes, font, mode


def edge_point(box, toward):
    """Where the line from the box's centre toward a point leaves the box, a little outside its edge."""
    cx, cy, w, h = box
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    scale = min((w / 2 + 10) / abs(dx) if dx else float("inf"), (h / 2 + 10) / abs(dy) if dy else float("inf"))
    return round(cx + dx * scale), round(cy + dy * scale)


def resolve_time(item, flat, start, problems, name):
    """Seconds from the graphic's start, or None when the piece has no time of its own."""
    if "at" in item:
        return float(item["at"])
    if "say" in item:
        t = find_phrase(flat, item["say"], after=start - 0.05) if flat else None
        if t is None:
            problems.append(f'"{item["say"]}" ({name}) is not said after the graphic starts: timed after the piece before.')
            return None
        return t - start
    return None


SFX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx")
# (sound, volume): loud enough to notice, well under the voice (the mix scales them all again)
SOUNDS = {"box": ("pop", 0.8), "arrow": ("whoosh", 0.45), "flow": ("whoosh", 0.6), "reach": ("pop", 0.35),
          "arrive": ("sparkle", 0.6)}


def ease_inverse(y):
    """The time (0 to 1) at which the template's ease-in-out reaches progress y."""
    y = min(max(y, 0.0), 1.0)
    return math.sqrt(y / 2) if y <= 0.5 else 1 - math.sqrt(2 * (1 - y)) / 2


def sound_events(props):
    """[(seconds from the graphic's start, kind)] for every box, arrow and trip of the dot, matching the template:
    the dot moves at an even speed along its path with an ease-in-out, so it reaches each box at ease_inverse of
    the share of the path behind it."""
    fps = props["fps"]
    events = [(n["frame"] / fps, "box") for n in props["nodes"]]
    events += [(l["frame"] / fps, "arrow") for l in props["links"]]
    for f in props["flows"]:
        pts = f["points"]
        lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
        total = sum(lengths) or 1.0
        events.append((f["frame"] / fps, "flow"))
        done = 0.0
        for i, length in enumerate(lengths):
            done += length
            t = (f["frame"] + f["frames"] * ease_inverse(done / total)) / fps
            events.append((t, "arrive" if i == len(lengths) - 1 else "reach"))
    return sorted(events)


def read_sound(name):
    with wave.open(os.path.join(SFX_DIR, name + ".wav"), "rb") as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (2, 2, 48000):
            raise ValueError(f"{name}.wav must be 48 kHz 16-bit stereo.")
        return array.array("h", w.readframes(w.getnframes()))


def write_sounds(events, seconds, path, rate=48000):
    """Mixes the events into one stereo wav as long as the graphic, with a limiter so pops on top of each other
    never clip."""
    total = int(round(seconds * rate)) * 2
    mix = [0.0] * total
    cache = {}
    for t, kind in events:
        name, gain = SOUNDS[kind]
        sound = cache.setdefault(name, read_sound(name))
        start = int(round(t * rate)) * 2
        for i in range(min(len(sound), total - start)):
            mix[start + i] += sound[i] * gain
    peak = max((abs(v) for v in mix), default=0)
    scale = min(1.0, 32000 / peak) if peak else 1.0
    out = array.array("h", (int(v * scale) for v in mix))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(out.tobytes())


def build_props(spec, captions, width, height, fps, style, palette=PALETTE.split(",")):
    flat = flat_words(captions) if captions else []
    problems = []
    nodes, links, flows = spec.get("nodes", []), spec.get("links", []), spec.get("flows", [])
    if not nodes:
        raise ValueError("explainer.json needs at least one node.")
    if len(nodes) > MAX_NODES:
        raise ValueError(f"{len(nodes)} boxes: at most {MAX_NODES} fit and read well. Split it into two graphics.")
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        raise ValueError("Two nodes have the same id.")
    for link in links:
        for end in (link["from"], link["to"]):
            if end not in ids:
                raise ValueError(f'A link names "{end}", which is not a node id.')
    for flow in flows:
        for step in flow["path"]:
            if step not in ids:
                raise ValueError(f'A flow names "{step}", which is not a node id.')

    if "start" in spec:
        start = float(spec["start"])
    elif "start_say" in spec:
        start = find_phrase(flat, spec["start_say"]) if flat else None
        if start is None:
            raise ValueError(f'"{spec["start_say"]}" (start_say) is not said in captions.json.')
    else:
        raise ValueError('explainer.json needs "start" (seconds) or "start_say" (a phrase).')

    # Times in order: nodes, links, flows; a piece with no time follows the one before it.
    timed, previous = {}, 0.0
    for kind, items in (("node", nodes), ("link", links), ("flow", flows)):
        for i, item in enumerate(items):
            name = item.get("label") or item.get("id") or f"{kind} {i + 1}"
            t = resolve_time(item, flat, start, problems, f"{kind} {name}")
            if kind == "link":
                t = max(t if t is not None else previous + GAP, timed[("node", ids.index(item["from"]))],
                        timed[("node", ids.index(item["to"]))])
            elif kind == "flow":
                needs = [timed[("node", ids.index(s))] for s in item["path"]]
                t = max([t if t is not None else previous + GAP] + needs)
            elif t is None:
                t = previous + GAP if (kind, i) != ("node", 0) else 0.0
            t = max(0.0, t)
            timed[(kind, i)] = t
            previous = t

    last = max(timed.values())
    flow_end = max([timed[("flow", i)] + float(f.get("seconds", FLOW)) for i, f in enumerate(flows)], default=0)
    if "end" in spec:
        length = float(spec["end"]) - start
    elif "end_say" in spec:
        end = find_phrase(flat, spec["end_say"], after=start) if flat else None
        if end is None:
            raise ValueError(f'"{spec["end_say"]}" (end_say) is not said after the graphic starts.')
        length = end - start
    elif "seconds" in spec:
        length = float(spec["seconds"])
    else:
        length = max(last, flow_end) + TAIL
    if length <= last:
        problems.append(f"The graphic ends at {length:.1f} s, before its last piece at {last:.1f} s: it was made longer.")
        length = max(last, flow_end) + 1.0

    longest = max((len(link.get("label", "")) for link in links), default=0)
    boxes, font, mode = layout(nodes, width, height, spec.get("layout", "auto"), bool(spec.get("title")), longest)
    frame = lambda seconds: int(round(seconds * fps))
    props = {"fps": fps, "width": width, "height": height, "seconds": round(length, 3),
             "title": spec.get("title", ""), "fontSize": font, "labelSide": "above" if mode == "row" else "right",
             **style, "nodes": [], "links": [], "flows": []}
    for i, node in enumerate(nodes):
        cx, cy, w, h = boxes[node["id"]]
        colour = node.get("color") or palette[i % len(palette)]
        props["nodes"].append({"id": node["id"], "label": node["label"], "icon": node.get("icon", ""),
                               "color": colour, "textColor": readable_text(colour),
                               "x": cx, "y": cy, "w": w, "h": h, "frame": frame(timed[("node", i)])})
    for i, link in enumerate(links):
        a, b = boxes[link["from"]], boxes[link["to"]]
        x1, y1 = edge_point(a, b[:2])
        x2, y2 = edge_point(b, a[:2])
        props["links"].append({"from": link["from"], "to": link["to"], "label": link.get("label", ""),
                               "both": bool(link.get("both")), "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                               "frame": frame(timed[("link", i)]), "frames": frame(DRAW)})
    for i, flow in enumerate(flows):
        props["flows"].append({"points": [list(boxes[s][:2]) for s in flow["path"]],
                               "frame": frame(timed[("flow", i)]), "frames": max(1, frame(float(flow.get("seconds", FLOW))))})
    timeline = sorted([(timed[(k, i)], k, i) for (k, i) in timed])
    return props, start, timeline, problems, mode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="explainer.json")
    ap.add_argument("--captions", help="captions.json of the finished cut (needed for phrases)")
    ap.add_argument("--size", default="1920x1080", help="the video's size, e.g. 1080x1920 for vertical")
    ap.add_argument("--fps", type=float, default=25)
    ap.add_argument("--font", default="sans-serif")
    ap.add_argument("--font-file", default="", help="inside the Remotion project's public folder")
    ap.add_argument("--palette", default=PALETTE, help="box colours, comma-separated, used in turn (the brand's colours)")
    ap.add_argument("--background", default="#1B1033", help='"transparent" to lay it over the speaker')
    ap.add_argument("--background2", default="#0E2A47", help="the other end of the background gradient")
    ap.add_argument("--accent", default="#FF4F8B", help="the travelling dot, the moving dashes and the title's line")
    ap.add_argument("--line", default="#FFFFFF")
    ap.add_argument("--out", default="explainer-props.json")
    ap.add_argument("--sounds", default="explainer-sfx.wav", help="the sound effects track to write")
    ap.add_argument("--no-sounds", action="store_true", help="don't write the sound effects")
    a = ap.parse_args()
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    captions = []
    if a.captions:
        with open(a.captions, encoding="utf-8") as f:
            captions = json.load(f)
    width, height = (int(v) for v in a.size.lower().split("x"))
    fps = int(a.fps) if float(a.fps).is_integer() else a.fps
    style = {"font": a.font, "fontFile": a.font_file, "background": a.background, "background2": a.background2,
             "accentColor": a.accent, "lineColor": a.line}
    palette = [c.strip() for c in a.palette.split(",") if c.strip()]
    try:
        props, start, timeline, problems, mode = build_props(spec, captions, width, height, fps, style, palette)
    except ValueError as error:
        sys.exit(str(error))
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(props, f, indent=2, ensure_ascii=False)
    print(f"Graphic from {stamp(start)} to {stamp(start + props['seconds'])} in the video ({props['seconds']:.1f} s), "
          f"boxes in a {mode}:")
    names = {"node": spec.get("nodes", []), "link": spec.get("links", []), "flow": spec.get("flows", [])}
    for t, kind, i in timeline:
        item = names[kind][i]
        what = {"node": lambda x: f'box "{x["label"]}"',
                "link": lambda x: f'arrow {x["from"]} -> {x["to"]}' + (f' "{x["label"]}"' if x.get("label") else ""),
                "flow": lambda x: "dot along " + " -> ".join(x["path"])}[kind](item)
        print(f"  {stamp(start + t)}  {what}")
    for p in problems:
        print("  NOTE: " + p)
    print(f"Wrote {a.out}.")
    if not a.no_sounds:
        events = sound_events(props)
        write_sounds(events, props["seconds"], a.sounds)
        print(f"Wrote {a.sounds}: {len(events)} sound effects (pops, whooshes, a sparkle), {props['seconds']:.1f} s. Mix it "
              f"under the voice from {start:.2f} s (adelay={int(round(start * 1000))}|{int(round(start * 1000))}), at about "
              "0.4 to 0.5 like the other effects (references/sound.md); quieter if the explanation is long.")
    print("Render it (from the Remotion project):")
    print(f"  npx remotion render src/index.ts Explainer out/explainer.mov --props={os.path.basename(a.out)}"
          + (" --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png"
             if a.background == "transparent" else ""))
    print(f"Then put it on the video from {start:.2f} s, the voice going on underneath:")
    print(f'  ffmpeg -i <video> -itsoffset {start:.3f} -i out/explainer.mov -filter_complex '
          f'"[0:v][1:v]overlay=enable=\'between(t,{start:.3f},{start + props["seconds"]:.3f})\':eof_action=pass[v]" '
          '-map "[v]" -map 0:a -c:a copy <in-between encoder> with-explainer.mp4')


if __name__ == "__main__":
    main()
