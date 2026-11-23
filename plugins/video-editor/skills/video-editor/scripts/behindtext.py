"""Puts big letters behind the speaker (the "text behind subject" effect): the words sit in the background and the
speaker stays in front of them, using the background-blur mask (bgmask.mkv) to know where the speaker is.

  python -I behindtext.py "IA" --say "inteligencia artificial" [--until "y ahora"] --font <brand font .ttf/.otf>
  python -I behindtext.py "3 TRUCOS" --at 0.4 --until-at 3.2 --font <font> [--color "#FFFFFF"] [--top 0.06]
  options: --video retouched.mp4, --mask bgmask.mkv, --captions captions.json, --width 0.88, --size <px>,
           --fade 0.35, --rise 0.04, --edge 2.0, --encoder "<in-between encoder from my-setup.md>", --out behind.mp4

Times are seconds in the video, like captions.json (mono.py works the same way). --say finds a phrase in
captions.json (accents and case ignored): the letters appear at its first word and stay to the end of that caption,
or to the end of the --until phrase. It prints what it found: check it with the user. "|" in the text starts a new
line ("NO USES|CHATGPT ASÍ").

The letters are drawn as large as fit --width of the frame (or at --size px), centred, with their top at --top of
the frame height: in a talking-head shot that puts them behind the head and shoulders, where they show around the
speaker. They fade in over --fade seconds while rising by --rise of the frame height, and fade out at the end.

bgmask.mkv is white where the background is and black where the speaker (and anything kept sharp: held products,
clothing) is. It is built for the blur on clean.mp4, so it has the same frames as retouched.mp4. Its edges are soft
for the blur; --edge makes them firmer here (2 by default; 1 keeps them as they are), so the letters don't show
through the speaker's outline.

It writes behindtext.png (the letters on a transparent frame) and behindtext.txt (the FFmpeg filter), and prints the
command that renders <out>: the video with the letters behind the speaker, sound copied. Run the rest of step 6
(push in, black and white, titles, captions, end card) on that file. Needs FFmpeg and Pillow.
"""
import argparse
import json
import subprocess
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mono import find, words_of  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"Can't read {path}: {out.stderr.strip()}")
    info = json.loads(out.stdout)
    s = info["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(num) / float(den), float(info["format"].get("duration", 0))


def times_from_captions(path, say, until):
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
    print(f'Found "{say}" at {start:.2f} s; letters behind the speaker from {start:.2f} to {end:.2f} s.')
    return start, end


def draw_text(text, font_path, width, height, fit_width, size, top, color):
    """The letters on a transparent frame; returns the PIL image and the font size used."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        sys.exit("Needs Pillow: pip install pillow (in the Python you run this with).")
    lines = [line.strip() for line in text.split("|") if line.strip()]
    if not lines:
        sys.exit("No text to draw.")

    def measure(px):
        font = ImageFont.truetype(str(font_path), px)
        boxes = [font.getbbox(line) for line in lines]
        return font, boxes

    if not size:
        size, target = 40, width * fit_width
        while size < height:  # the largest size whose widest line fits
            _, boxes = measure(size + 4)
            if max(b[2] - b[0] for b in boxes) > target:
                break
            size += 4
    font, boxes = measure(size)
    gap = int(size * 0.08)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = int(height * top)
    for line, b in zip(lines, boxes):
        x = (width - (b[2] - b[0])) // 2 - b[0]
        d.text((x, y - b[1]), line, font=font, fill=color)
        y += (b[3] - b[1]) + gap
    if y > height * 0.75:
        print("Warning: the letters reach below three quarters of the frame; they may sit over the captions. "
              "Use fewer words, a smaller --width or a smaller --top.")
    return img, size


def build_filter(width, height, start, end, fade, rise, edge):
    fade = max(0.0, min(fade, (end - start) / 2))
    lift = int(round(height * rise))
    # the letters: fade in and out, and rise into place while fading in
    txt = "[2:v]format=rgba"
    if fade > 0:
        txt += f",fade=t=in:st={start:.3f}:d={fade:.3f}:alpha=1,fade=t=out:st={end - fade:.3f}:d={fade:.3f}:alpha=1"
    txt += "[txt]"
    if fade > 0 and lift:
        y = f"'{lift}*(1-min(1,max(0,(t-{start:.3f})/{fade:.3f})))'"
    else:
        y = "0"
    # the speaker: white in the mask is background, so the speaker's alpha is the mask turned over
    alpha = "[1:v]format=gray,scale=" + f"{width}:{height},negate"
    if edge and abs(edge - 1) > 1e-6:
        alpha += f",lut=y='clip((val-128)*{edge:g}+128,0,255)'"
    alpha += "[a]"
    return ";\n".join([
        "[0:v]split[base][top]",
        txt,
        alpha,
        "[top][a]alphamerge[speaker]",
        f"[base][txt]overlay=x=0:y={y}:shortest=1:enable='between(t,{start:.3f},{end:.3f})'[back]",
        "[back][speaker]overlay=x=0:y=0:shortest=1,format=yuv420p[v]",
    ]) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", help='the words; "|" starts a new line')
    ap.add_argument("--font", required=True, help="the brand font file (.ttf or .otf)")
    ap.add_argument("--say", help="a phrase from captions.json where the letters appear")
    ap.add_argument("--until", help="with --say: the phrase where they go (default: the end of that caption)")
    ap.add_argument("--at", type=float, help="seconds where the letters appear (instead of --say)")
    ap.add_argument("--until-at", type=float, help="with --at: seconds where they go")
    ap.add_argument("--captions", default="captions.json")
    ap.add_argument("--video", default="retouched.mp4")
    ap.add_argument("--mask", default="bgmask.mkv")
    ap.add_argument("--color", default="#FFFFFF", help="the letters' colour (the brand's accent, or white)")
    ap.add_argument("--width", type=float, default=0.88, help="share of the frame width the widest line fills")
    ap.add_argument("--size", type=int, help="font size in px (instead of fitting --width)")
    ap.add_argument("--top", type=float, default=0.06, help="top of the letters, as a share of the frame height")
    ap.add_argument("--fade", type=float, default=0.35, help="seconds to fade in and out (0: appear at once)")
    ap.add_argument("--rise", type=float, default=0.04, help="how far the letters rise while fading in (0: none)")
    ap.add_argument("--edge", type=float, default=2.0, help="how much firmer the mask's edge is made (1: as built)")
    ap.add_argument("--encoder", default="-c:v libx264 -preset medium -crf 10 -pix_fmt yuv420p",
                    help="the in-between encoder line from my-setup.md")
    ap.add_argument("--out", default="behind.mp4")
    a = ap.parse_args()

    if a.say:
        start, end = times_from_captions(a.captions, a.say, a.until)
    elif a.at is not None and a.until_at is not None:
        start, end = a.at, a.until_at
    else:
        sys.exit("Give --say (and optionally --until), or --at and --until-at.")
    if end - start < 0.5:
        sys.exit(f"The letters would show for only {end - start:.2f} s; give a longer stretch.")
    if not Path(a.font).is_file():
        sys.exit(f"Font file not found: {a.font}")
    for f in (a.video, a.mask):
        if not Path(f).is_file():
            sys.exit(f"Not found: {f}" + (" (build it with the background-blur step, references/retouch.md)"
                                          if f == a.mask else ""))

    width, height, fps, length = probe(a.video)
    mw, mh, _, mlength = probe(a.mask)
    if length and mlength and abs(length - mlength) > 0.2:
        print(f"Warning: {a.mask} lasts {mlength:.2f} s and {a.video} {length:.2f} s. The mask must be built on the "
              "same cut (clean.mp4 of this version), or the speaker and the mask drift apart.")
    if length and end > length + 0.05:
        sys.exit(f"The letters end at {end:.2f} s, after the video ({length:.2f} s).")
    if (mw, mh) != (width, height):
        print(f"The mask is {mw}x{mh}; it is scaled to {width}x{height}.")

    img, size = draw_text(a.text, a.font, width, height, a.width, a.size, a.top, a.color)
    img.save("behindtext.png")
    Path("behindtext.txt").write_text(build_filter(width, height, start, end, a.fade, a.rise, a.edge), "utf-8")
    print(f'Wrote behindtext.png ("{a.text}", {size} px) and behindtext.txt: letters from {start:.2f} to '
          f"{end:.2f} s.")
    print("Render with (FFmpeg 6 or older: -filter_complex_script instead of -/filter_complex):")
    print(f'  ffmpeg -i "{a.video}" -i "{a.mask}" -loop 1 -framerate {fps:g} -i behindtext.png '
          f'-/filter_complex behindtext.txt -map "[v]" -map 0:a? {a.encoder} -c:a copy "{a.out}"')
    print("Then look at a frame in the middle of it: the speaker in front, the letters showing around them.")


if __name__ == "__main__":
    main()
