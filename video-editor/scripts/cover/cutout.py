"""Cut a product out of a photo or a video frame, for the cover.

Usage:
  python -I cutout.py <image> <out.png> [--crop x,y,w,h] [--white] [--pad 24]

  --crop   cut out only this box (pixels), e.g. the product in a video frame,
           so the speaker and the room aren't picked up.
  --white  for shop photos on a plain white background: remove the white that
           touches the edges. No model needed, and the edges stay crisp. Don't use it
           for white or clear packaging, which touches that white and would vanish.
  --pad    transparent margin around the trimmed product, in pixels.

Without --white it uses rembg (isnet-general-use model, downloaded on first use).
The output is a transparent PNG trimmed to the product. It prints how much of the
image is kept: a very small or very large share usually means the cutout failed,
so look at it before using it.
"""
import argparse
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def white_cutout(img: Image.Image, tolerance: int = 18) -> Image.Image:
    """Make the near-white area connected to the image edges transparent."""
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    near_white = (255 - rgb).max(axis=2) <= tolerance
    mask = Image.fromarray(np.where(near_white, 255, 0).astype(np.uint8)).copy()  # a copy: the array-backed image can't be filled
    w, h = mask.size
    border = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    for point in border:
        if mask.getpixel(point) == 255:
            ImageDraw.floodfill(mask, point, 128)
    background = np.asarray(mask) == 128
    alpha = np.where(background, 0, 255).astype(np.uint8)
    # Soften the edge by one pixel so it doesn't look jagged on a colored background.
    alpha_img = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(0.8))
    out = img.convert("RGBA")
    out.putalpha(alpha_img)
    return out


def model_cutout(img: Image.Image) -> Image.Image:
    from rembg import new_session, remove

    session = new_session("isnet-general-use")
    return remove(img.convert("RGB"), session=session)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--crop", help="x,y,w,h in pixels")
    ap.add_argument("--white", action="store_true")
    ap.add_argument("--pad", type=int, default=24)
    args = ap.parse_args()

    img = Image.open(args.image)
    img.load()
    if args.crop:
        x, y, w, h = (int(v) for v in args.crop.split(","))
        img = img.crop((x, y, x + w, y + h))

    out = white_cutout(img) if args.white else model_cutout(img)

    alpha = np.asarray(out.getchannel("A"))
    kept = float((alpha > 128).mean())
    box = out.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if box is None:
        print("Nothing was kept: the cutout failed. Try the other mode or a tighter --crop.")
        return 1
    out = out.crop(box)
    padded = Image.new("RGBA", (out.width + 2 * args.pad, out.height + 2 * args.pad), (0, 0, 0, 0))
    padded.paste(out, (args.pad, args.pad))
    padded.save(args.out)

    print(f"Saved {args.out} ({padded.width}x{padded.height}), kept {kept:.0%} of the image.")
    if kept < 0.03 or kept > 0.9:
        print("That share looks wrong for a product: check the cutout before using it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
