"""Tool cards for videos about AI: when the speaker names a tool (Claude, Gmail, Notion...), a card with its logo and
name slides in a beat before the word and leaves on its own. Tools named one after another stack into one group.

  python -I toolcards.py tools.json --captions captions.json --size 1080x1920 --fps 25
         [--side left|right] [--top 0.55] [--hold 2.5] [--accent "#FF4F8B"] [--font ... --font-file ...]
         [--out toolcards]

tools.json lists the video's tools, written by Claude from the transcript:
  [{"name": "Claude", "logo": "logos/claude.png"},          logo: inside the Remotion project's public folder, from
   {"name": "Gmail", "logo": "logos/gmail.png"},             the brand's own press kit; without one, a badge with
   {"name": "Notion", "say": ["notion", "noción"]}]          the initial. "say": other ways the transcript spells it
Every time a tool's name (or a "say") is said, a card is due 0.2 s before it. A tool already shown in the last
--repeat seconds (20) is not shown again: a logo every time it's said wears thin. Cards due within --stack seconds
(1.5) of the card before join its group, one under the other, each appearing on its own word; a group stays --hold
seconds (2.5) after its last card. Groups never overlap.

Writes <out>/card-N.json, the props of each group for scripts/remotion/ToolCard.tsx, and <out>/toolcards-sfx.wav: a
soft pop as each logo lands (a logo appearing is one of the few things that earns a sound), the length of the video
up to the last card. Prints each group's time and the commands to render and place it. Standard library only.
"""
import argparse
import array
import json
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chapters import flat_words, words_of  # noqa: E402
from explainer import peak_offset, read_sound  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

LEAD = 0.2       # seconds a card appears before its word
EXIT = 0.35      # seconds a group takes to leave


def stamp(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def mentions(tools, flat):
    """[(time the name starts, tool index)] for every time a tool's name or one of its "say" spellings is said."""
    found = []
    for i, tool in enumerate(tools):
        spellings = [tool["name"]] + list(tool.get("say", []))
        for spelling in spellings:
            want = words_of(spelling)
            if not want:
                continue
            for k in range(len(flat) - len(want) + 1):
                if [w for _, w in flat[k:k + len(want)]] == want:
                    found.append((flat[k][0], i))
    found = sorted(set(found))
    return found


def plan_groups(tools, flat, repeat=20.0, stack=1.5, hold=2.5):
    """Groups [{"start", "end", "cards": [(time, tool index)]}] in video seconds."""
    last_shown = {}
    due = []
    for t, i in mentions(tools, flat):
        if i in last_shown and t - last_shown[i] < repeat:
            continue
        last_shown[i] = t
        due.append((max(0.0, t - LEAD), i))
    groups = []
    for t, i in due:
        if groups and t - groups[-1]["cards"][-1][0] <= stack and i not in [c[1] for c in groups[-1]["cards"]]:
            groups[-1]["cards"].append((t, i))
            groups[-1]["end"] = t + hold
        elif groups and t < groups[-1]["end"] + EXIT:
            # Due while the group before is still on screen: it waits for that group to leave.
            start = groups[-1]["end"] + EXIT
            groups.append({"start": start, "end": start + hold, "cards": [(start, i)]})
        else:
            groups.append({"start": t, "end": t + hold, "cards": [(t, i)]})
    return groups


def group_props(group, tools, width, height, fps, style, side="left", top=None):
    frame = lambda seconds: int(round(seconds * fps))
    vertical = height > width
    size = round(min(width, height) / (16 if vertical else 20))
    return {"fps": fps, "width": width, "height": height, "seconds": round(group["end"] - group["start"] + EXIT, 3),
            "side": side, "top": round(height * (top if top is not None else (0.55 if vertical else 0.62))),
            "fontSize": size, **style,
            "cards": [{"name": tools[i]["name"], "logo": tools[i].get("logo", ""), "frame": frame(t - group["start"])}
                      for t, i in group["cards"]]}


def write_pops(times, seconds, path, gain=0.5, rate=48000):
    """A stereo wav `seconds` long with a soft pop at each time (its loudest moment on the time)."""
    pop = read_sound("pop")
    lead_in = peak_offset(pop)
    mix = [0.0] * (int(round(seconds * rate)) * 2)
    for t in times:
        start = max(0, int(round(t * rate)) - lead_in) * 2
        for k in range(min(len(pop), len(mix) - start)):
            mix[start + k] += pop[k] * gain
    peak = max((abs(v) for v in mix), default=0)
    scale = min(1.0, 32000 / peak) if peak else 1.0
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(array.array("h", (int(v * scale) for v in mix)).tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tools", help="tools.json")
    ap.add_argument("--captions", required=True, help="captions.json of the finished cut")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=float, default=25)
    ap.add_argument("--side", choices=("left", "right"), default="left", help="the side away from the face")
    ap.add_argument("--top", type=float, help="the first card's top, as a share of the height (0.55 vertical, 0.62 wide)")
    ap.add_argument("--hold", type=float, default=2.5)
    ap.add_argument("--repeat", type=float, default=20.0, help="seconds before the same tool can show again")
    ap.add_argument("--stack", type=float, default=1.5, help="seconds within which cards join one group")
    ap.add_argument("--accent", default="#FF4F8B", help="the badge of a tool without a logo")
    ap.add_argument("--font", default="sans-serif")
    ap.add_argument("--font-file", default="")
    ap.add_argument("--out", default="toolcards")
    a = ap.parse_args()
    with open(a.tools, encoding="utf-8") as f:
        tools = json.load(f)
    with open(a.captions, encoding="utf-8") as f:
        flat = flat_words(json.load(f))
    width, height = (int(v) for v in a.size.lower().split("x"))
    fps = int(a.fps) if float(a.fps).is_integer() else a.fps
    style = {"accentColor": a.accent, "font": a.font, "fontFile": a.font_file}
    groups = plan_groups(tools, flat, a.repeat, a.stack, a.hold)
    if not groups:
        sys.exit("None of the tools is said in the captions: check the names, or add how the transcript spells them "
                 'as "say".')
    os.makedirs(a.out, exist_ok=True)
    said = {i for g in groups for _, i in g["cards"]}
    for i, tool in enumerate(tools):
        if i not in said:
            print(f'NOTE: "{tool["name"]}" is never said: add how the transcript spells it as "say".')
        if not tool.get("logo"):
            print(f'NOTE: "{tool["name"]}" has no logo: it shows a badge with its initial (logos from the brand\'s press kit).')
    print(f"{len(groups)} card group(s):")
    for n, g in enumerate(groups, start=1):
        props = group_props(g, tools, width, height, fps, style, a.side, a.top)
        path = os.path.join(a.out, f"card-{n}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(props, f, indent=2, ensure_ascii=False)
        names = ", ".join(tools[i]["name"] for _, i in g["cards"])
        print(f"  {stamp(g['start'])} to {stamp(g['end'])}: {names}  ({path})")
        print(f"    npx remotion render src/index.ts ToolCard out/card-{n}.mov --props={path} --codec=prores "
              "--prores-profile=4444 --pixel-format=yuva444p10le --image-format=png")
        print(f"    then overlay out/card-{n}.mov from {g['start']:.3f} s (-itsoffset {g['start']:.3f}, "
              f"overlay=format=auto:eof_action=pass)")
    pops = [t for g in groups for t, _ in g["cards"]]
    sfx = os.path.join(a.out, "toolcards-sfx.wav")
    write_pops(pops, groups[-1]["end"] + 1.0, sfx)
    print(f"Wrote {sfx}: a soft pop as each logo lands. Mix it under the voice from 0 s, at about 0.4.")


if __name__ == "__main__":
    main()
