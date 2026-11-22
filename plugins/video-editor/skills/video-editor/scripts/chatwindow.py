"""An AI chat window for a video about AI: the prompt types into the box, it is sent, the assistant "thinks" and its
answer appears word by word, each turn starting as the speaker says it. Cleaner than a screen recording of a real
chat, and the same every time.

  python -I chatwindow.py chat.json --captions captions.json --size 1920x1080 --fps 25
         [--font "Montserrat" --font-file fonts/Montserrat-Bold.ttf] [--accent "#FF4F8B"] [--theme light|dark]
         [--background "#1B1033" --background2 "#0E2A47" | --background transparent] [--out chat-props.json]

chat.json is written by Claude from the script or the transcript:
  {"app": "Claude",                       the name in the window's top bar (any assistant or app)
   "logo": "logos/claude.png",            optional, inside the Remotion project's public folder, from the brand's
                                          own press kit; without it, a circle with the app's initial
   "start_say": "le pido a Claude",       where the window appears (or "start": seconds)
   "end_say": "y así de rápido",          where it goes (or "end": seconds, or "seconds": length)
   "placeholder": "Escribe un mensaje…",  the empty box's text, in the video's language
   "messages": [
     {"role": "user", "text": "Resume este correo en tres puntos", "say": "le pido que me lo resuma"},
     {"role": "assistant", "text": "- Reunión el lunes\n- Presupuesto aprobado\n- Falta tu firma", "say": "y me dice"}]}
A user message types into the box (a letter every 1/--lps seconds, with soft key clicks), is sent, and shows as a
bubble; the assistant's answer shows three dots for --think seconds, then its words appear at --wps words a second.
Lines starting with "- " show as a list. Each message starts at its "say" phrase (0.2 s before it, as the animated
explanations do), or "at" seconds after the window appears, or right after the message before. An answer never starts
before the prompt it answers is sent.

The window is a clean, generic chat design in the brand's colours with the app's name, not a copy of any company's
real interface: say what it shows ("I asked Claude…") and use the app's logo only from its press kit, as its
guidelines allow. Writes the props for scripts/remotion/ChatWindow.tsx and chat-sfx.wav (key clicks while the prompt
types, nothing for the answer: it makes no sound on screen). Standard library only.
"""
import argparse
import importlib.util
import json
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chapters import find_phrase, flat_words  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

LEAD = 0.2       # seconds a message starts before the phrase that names it
GAP = 0.4        # seconds after the message before, for one with no time of its own
TAIL = 2.0       # seconds the window stays after the last answer when no end is given
SEND = 0.25      # seconds between the last letter and the bubble (pressing enter)


def stamp(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def load_typing():
    """scripts/sfx/typing.py, loaded by path (its name would clash with Python's own typing module)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx", "typing.py")
    spec = importlib.util.spec_from_file_location("sfx_typing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_props(spec, captions, width, height, fps, style, lps=22.0, wps=12.0, think=0.8):
    """(props, start in the video, timeline [(seconds from start, text)], problems)."""
    flat = flat_words(captions) if captions else []
    problems = []
    messages = spec.get("messages", [])
    if not messages:
        raise ValueError("chat.json needs at least one message.")
    for m in messages:
        if m.get("role") not in ("user", "assistant") or not str(m.get("text", "")).strip():
            raise ValueError('Each message needs "role" ("user" or "assistant") and some "text".')
    if "start" in spec:
        start = float(spec["start"])
    elif "start_say" in spec:
        start = find_phrase(flat, spec["start_say"]) if flat else None
        if start is None:
            raise ValueError(f'"{spec["start_say"]}" (start_say) is not said in captions.json.')
        start = max(0.0, start - LEAD)
    else:
        raise ValueError('chat.json needs "start" (seconds) or "start_say" (a phrase).')

    frame = lambda seconds: int(round(seconds * fps))
    out, timeline, previous_end, last_sent = [], [], 0.4, 0.0
    for i, m in enumerate(messages):
        begin = None
        if "at" in m:
            begin = float(m["at"])
        elif "say" in m:
            t = find_phrase(flat, m["say"], after=start - 0.05) if flat else None
            if t is None:
                problems.append(f'"{m["say"]}" (message {i + 1}) is not said after the window appears: it follows the one before.')
            else:
                begin = t - start - LEAD
        if begin is None:
            begin = previous_end + GAP
        begin = max(begin, 0.3 if i == 0 else previous_end + 0.1)
        text = m["text"].strip()
        if m["role"] == "user":
            typed = len(text) / lps
            entry = {"role": "user", "text": text, "typeFrom": frame(begin), "typeTo": frame(begin + typed),
                     "sent": frame(begin + typed + SEND)}
            last_sent = begin + typed + SEND
            previous_end = last_sent
            timeline.append((begin, f'types: "{text[:50]}{"…" if len(text) > 50 else ""}"'))
        else:
            begin = max(begin, last_sent + 0.2)
            words = len(text.split())
            answer = begin + think
            entry = {"role": "assistant", "text": text, "from": frame(begin), "answer": frame(answer),
                     "framesPerWord": max(1, round(fps / wps))}
            previous_end = answer + words / wps
            timeline.append((begin, f'answers ({words} words, done at {stamp(start + previous_end)})'))
        out.append(entry)

    if "end" in spec:
        length = float(spec["end"]) - start
    elif "end_say" in spec:
        end = find_phrase(flat, spec["end_say"], after=start) if flat else None
        if end is None:
            raise ValueError(f'"{spec["end_say"]}" (end_say) is not said after the window appears.')
        length = end - start
    elif "seconds" in spec:
        length = float(spec["seconds"])
    else:
        length = previous_end + TAIL
    if length < previous_end + 0.5:
        problems.append(f"The window goes at {length:.1f} s but the last answer finishes at {previous_end:.1f} s: "
                        "made longer so it can be read.")
        length = previous_end + 1.0

    props = {"fps": fps, "width": width, "height": height, "seconds": round(length, 3),
             "app": spec.get("app", "Assistant"), "logo": spec.get("logo", ""),
             "placeholder": spec.get("placeholder", "Escribe un mensaje…"),
             # a thirtieth of the frame left the text small in a mostly empty window, too small for a phone
             "fontSize": round(min(width, height) / 20), **style, "messages": out}
    return props, start, timeline, problems


def click_times(props):
    """Seconds (from the window's start) of a key click every second letter while each prompt types, and the
    'enter' click when it is sent."""
    fps, times = props["fps"], []
    for m in props["messages"]:
        if m["role"] != "user":
            continue
        letters = [i for i, ch in enumerate(m["text"]) if ch != " "]
        span = (m["typeTo"] - m["typeFrom"]) / fps
        for k, i in enumerate(letters):
            if k % 2 == 0:
                times.append(m["typeFrom"] / fps + span * i / max(1, len(m["text"])))
        times.append(m["sent"] / fps)
    return sorted(times)


def write_clicks(props, path, volume=0.45, rate=48000):
    samples = load_typing().render_clicks(click_times(props), props["seconds"], volume, rate)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767)) for v in samples))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="chat.json")
    ap.add_argument("--captions", help="captions.json of the finished cut (needed for phrases)")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=float, default=25)
    ap.add_argument("--lps", type=float, default=22.0, help="letters a second while a prompt types")
    ap.add_argument("--wps", type=float, default=12.0, help="words a second as an answer appears")
    ap.add_argument("--think", type=float, default=0.8, help="seconds of 'thinking' dots before an answer")
    ap.add_argument("--theme", choices=("light", "dark"), default="light", help="the window's own colours")
    ap.add_argument("--font", default="sans-serif")
    ap.add_argument("--font-file", default="")
    ap.add_argument("--accent", default="#FF4F8B", help="the user's bubbles and the send button (the brand's colour)")
    ap.add_argument("--background", default="#1B1033", help='"transparent" to lay the window over the speaker')
    ap.add_argument("--background2", default="#0E2A47")
    ap.add_argument("--out", default="chat-props.json")
    ap.add_argument("--sounds", default="chat-sfx.wav")
    ap.add_argument("--no-sounds", action="store_true")
    a = ap.parse_args()
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    captions = []
    if a.captions:
        with open(a.captions, encoding="utf-8") as f:
            captions = json.load(f)
    width, height = (int(v) for v in a.size.lower().split("x"))
    fps = int(a.fps) if float(a.fps).is_integer() else a.fps
    style = {"theme": a.theme, "font": a.font, "fontFile": a.font_file, "accentColor": a.accent,
             "background": a.background, "background2": a.background2}
    try:
        props, start, timeline, problems = build_props(spec, captions, width, height, fps, style, a.lps, a.wps, a.think)
    except ValueError as error:
        sys.exit(str(error))
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(props, f, indent=2, ensure_ascii=False)
    print(f"Chat window from {stamp(start)} to {stamp(start + props['seconds'])} in the video ({props['seconds']:.1f} s):")
    for t, what in timeline:
        print(f"  {stamp(start + t)}  {what}")
    for p in problems:
        print("  NOTE: " + p)
    print(f"Wrote {a.out}.")
    if not a.no_sounds:
        write_clicks(props, a.sounds)
        print(f"Wrote {a.sounds}: key clicks while the prompts type. Mix it under the voice from {start:.2f} s "
              f"(adelay={int(round(start * 1000))}), at about 0.3 like the other effects.")
    print("Render it (from the Remotion project):")
    print(f"  npx remotion render src/index.ts ChatWindow out/chat.mov --props={os.path.basename(a.out)}"
          + (" --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png"
             if a.background == "transparent" else ""))
    print(f'Then place it from {start:.2f} s: ffmpeg -i <video> -itsoffset {start:.3f} -i out/chat.mov -filter_complex '
          f'"[0:v][1:v]overlay=enable=\'between(t,{start:.3f},{start + props["seconds"]:.3f})\':eof_action=pass[v]" '
          '-map "[v]" -map 0:a -c:a copy <in-between encoder> with-chat.mp4')


if __name__ == "__main__":
    main()
