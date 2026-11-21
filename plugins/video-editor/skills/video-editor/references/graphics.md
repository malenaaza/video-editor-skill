# Animated graphics: Remotion templates and emojis

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

HyperFrames skills (`hyperframes`, `hyperframes-cli`) make animated graphics if they're installed. Remotion, run through `npx`, also does; use it when the user asks for it or when HyperFrames isn't available. If neither works, build graphics with FFmpeg and say so.

Remotion builds motion graphics from React code: intros, outros, lower thirds, animated titles and charts, not cutting footage. Cuts, captions and export stay in FFmpeg. Add each graphic as a new composition in `src/Root.tsx`, and don't change or remove existing ones unless asked. Copy logos and images into its `public` folder first.

Licensing: Remotion is free for individuals, non-profits, and for-profit organizations with up to 3 employees. Larger for-profit organizations need a paid Company License. Ask the user once, if a video is for a business, and save the answer in `my-setup.md`.

Use the brand's colors, font and logos (Rule 5), and match the resolution and frame rate of the video the graphic goes into. Render overlays with a transparent background, and full-screen pieces (intro, outro) as normal video:

```
npx remotion render src/index.ts <composition-id> out/overlay.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
npx remotion render src/index.ts <composition-id> out/intro.mp4 --codec=h264 --crf=16
```

Then bring the result into FFmpeg and do the final export as in Rule 6. Look at a few rendered frames before using it.

## Ready-made templates

Use these before writing a new graphic from scratch. Each renders one short transparent clip; register its composition in `src/Root.tsx` once (the import line is at the top of each file). Write the props to a JSON file and pass `--props=<file>.json`, so quotes, emoji and currency symbols survive on Windows. Fill the brand's colors from `my-setup.md`, and the font by its name plus `fontFile`, a path inside the project's `public` folder (copy the brand's font file to `public/fonts/` first). A missing font file stops the render with an error instead of falling back to another font. Always pass the video's `fps`, `width` and `height`.

| Template | Use it for | Main props | Default length |
|---|---|---|---|
| `TitleCard` | The hook title in the first seconds | `lines` (1 to 3 short lines), `highlight` (one word in the accent color), `top`, `animation` (`"pop"` or `"typewriter"`), `lettersPerSecond`, `cursor` | 2.5 s (longer for a long typewriter title) |
| `ProductTag` | Product name and price when a product is shown | `name`, `price` (written as it should appear, e.g. `€24,90`), `note` (e.g. "Link in bio"), `side`, `top` | 3.5 s |
| `EmojiPop` | Emojis on words (see Animated emojis below) | `emoji`, `left`, `top` | 43 frames |
| `CoverCard` | Cover image with the products (see `references/cover.md`) | `background`, `products` (one `image` each), `faceX`/`faceY`/`faceSize`, `lines` | a still: `npx remotion still` |
| `Thumbnail` | YouTube thumbnail, 1280x720: the face big on one side, a few huge words on the other (see `references/cover.md`) | `background`, `bgWidth`/`bgHeight`, `faceX`/`faceY`/`faceSize`, `lines` | a still: `npx remotion still` |
| `WordCaptions` | Word highlight captions: a box in the accent colour behind each word as it's said (see below) | written by `captions.py --remotion-props` | the whole video |
| `Explainer` | An animated explanation in an educational video: boxes, arrows and a moving dot showing how something works, each piece appearing as the speaker names it (see Animated explanations below) | written by `explainer.py` | the stretch it explains |
| `ProductPop` | The product's B-roll photo or clip popping in beside the speaker when they name it (see Product pop-in below) | `image` (a cut-out) or `clip` + `clipStart`, `side`, `top`, `size`, optional `name`, `price`, `note` | 2.6 s |

Shared style props: `font`, `fontFile`, `fontSize`, `textColor`, `boxColor` (`transparent` for no box), `accentColor`, `seconds`.

- **TitleCard:** keep it under about 6 words. Start it on the first frame, or a few frames in if the video opens on a word. Keep it below the app's top bar and off the face (see Titles and captions in Rule 10). When the brand's title style in `my-setup.md` is a still title, use that instead unless the user asks for an animated one.
- **TitleCard as a typewriter** (`"animation": "typewriter"`): each line's box wipes in as its first letter arrives, the letters are typed one by one (`lettersPerSecond`, default 16: a 20-letter title in about 1.3 s) with a blinking cursor in the accent colour, and the title gives a small bounce when it's complete. Letters not typed yet are already in place, so nothing shifts while typing. The clip lasts long enough to finish typing and be read for about a second. Keep typewriter titles short (about 25 letters): the typing delays the hook. Use it when the brand's `Title:` line says typewriter, or when the user asks. **Key clicks** (optional, as the brand's line says): `python -I <skill>/scripts/sfx/typing.py --line "<line 1>" --line "<line 2>" --lps <lettersPerSecond> --start <typingStart>` writes `typing.wav`, timed to the same letters; mix it like the other sound effects, delayed to the title's start, at about 0.3 to 0.45 under the voice. Checked on a real frame: the letters, cursor, highlight word and clicks lined up, and the frame count stayed the same.
- **WordCaptions (word highlight captions):** when the brand's `Captions:` line says word highlight, or the user asks. The captions are the same as the normal ones (same grouping, timing, size, position and line breaks), but each word gets a rounded box in the accent colour that wipes in from the left while it is said and fades as it ends; the words never move. Run `captions.py` as usual and add `--remotion-props word-captions.json --accent-color "<accent>" --fps <fps>` (with the video's `--width`/`--height`); add `"fontFile"` to that JSON if the font comes from a file. Render `WordCaptions` with `--props=word-captions.json` to a transparent `.mov` the length of the video, and place it from frame 0 in the captions' layer **instead of** burning `captions.ass` (never both). It renders the whole video, so it takes longer than the other templates (about 5 s per second of a 960x948 video in a test; a 3-minute Reel takes several minutes). Without Node and Remotion, use the normal captions and tell the user. Check a frame mid-word: the box sits behind the right word and the caption stays off the face.
- **ProductTag:** show it when the product is first named or held up, starting a few frames after the name is said. Use it only for the main products, once each, unless asked for more. Keep it above the caption area from `my-setup.md` and on the side away from the speaker's face and the product. Put the price only if the user gave it or it's said in the video; never guess a price.
- **Placing:** the same as emojis: `setpts=PTS-STARTPTS+<frame>/(<fps>*TB)` and `overlay=0:0:format=rgb:eof_action=pass`, with `format=rgba` on both inputs.
- **Check:** look at one frame mid-animation and one fully shown for each graphic, on the real footage: text readable, nothing covering the face, product, captions or logo.

## Animated explanations

For a part of an educational video that explains how something works (how an MCP connects Claude to Gmail, how a
request travels, the steps of a process): boxes, arrows between them and an accent-coloured dot that travels the
path, each piece appearing as the speaker names it. The voice goes on underneath. It comes from the script's
`[GRAPHIC]` notes (`references/script.md`: Claude proposes them when writing the script), or from a part the user
points at after filming. Without a script, after reading the transcript, suggest one or two passages that would
explain better as an animation, in one line each, and make them only if the user wants them.

1. **Write `explainer.json`** in the build folder, from the transcript of the cut: the title, where it starts and
   ends (`start_say`/`end_say`, phrases the speaker says, or seconds), up to 6 boxes (`nodes`: `id`, a short
   `label`, an optional `icon` emoji, and the phrase that brings it in, `say`), the arrows (`links`: `from`, `to`,
   an optional one- or two-word `label`, `both` for a two-way arrow, `say`) and the dot's trips (`flows`: a `path`
   of box ids, there and back for a request and its answer, `say`). The full format is at the top of
   `<skill>/scripts/explainer.py`. Keep labels short: two or three words fit in a box.
2. **Make the props:** `python -I <skill>/scripts/explainer.py explainer.json --captions captions.json --size
   <video size> --fps <video fps>` with the brand's colours and font (`--palette` with the brand's colours for the boxes, in
   turn, `--background`/`--background2` for the gradient, `--accent`, `--line`, `--font`, `--font-file`; `--background transparent` lays it over the speaker instead of
   filling the screen). It lays the boxes out (a row in a wide video, a column in a vertical one, with room for
   the arrows and their labels), works out when each piece appears from the captions, and prints that timeline
   and anything it couldn't find. A link never appears before its boxes, nor the dot before its path.
3. **Show the user** the timeline in one short message, then render a few stills before the whole clip
   (`npx remotion still src/index.ts Explainer out/f.png --props=explainer-props.json --frame=<n>`): one with
   every box, one with the dot halfway. Then render it and place it with the FFmpeg line it prints.
   It also writes `explainer-sfx.wav`, the graphic's sound effects timed to its frames (a pop per box, a soft
   whoosh per arrow, a whoosh as the dot sets off, a tick at each box it reaches, a sparkle when it arrives): mix
   it under the voice from the graphic's start with the other effects (`references/sound.md`). `--no-sounds` if
   the brand doesn't use sound effects.
4. **Check** on the real video: every piece appears as it's named, nothing covers the captions (put the captions
   over the explanation, or raise them), and the text is readable on a phone.

The template only draws what `explainer.py` computed, so a different diagram never needs a change to
`Explainer.tsx`. For something it can't show (a chart, a screen, a photo), use the other templates or a screen
recording.

## Product pop-in from B-roll

When the speaker names a product, its photo or a short clip from their B-roll pops in beside them for about 2.6 s while they keep talking, with a pop sound. Use it when the brand's `Product pop-in:` line says so, or when the user asks; suggest it when a product is named and the B-roll has it.

1. **Index the B-roll** (the `B-roll folder:` in `my-setup.md`, or a `B-roll kit` folder): `python -I <skill>/scripts/broll.py index "<B-roll folder>"`. It lists every photo and clip, makes search words from the file and folder names, and writes `broll-index.json` and `broll-sheet.png`, a numbered contact sheet with one thumbnail per file. Look at the sheet.
2. **Find the moments and the files:** once `captions.json` exists (Rule 3), run `python -I <skill>/scripts/broll.py match --product "<name as said>" [--product ...]` for the main products. It prints when each is first said (times in the finished video, accents and plurals ignored) and the files whose names match best, and writes `broll-matches.json`.
3. **Choose the right one:** a file name only suggests. When there is no match, a tie, or only camera names (`IMG_2041.jpg`), compare the contact sheet with a frame of the video where the product is shown or held, by shape, colour and label, and pick the file that is the same product and shade. Prefer a photo for a still product and a clip for swatches or texture.
4. **Ask before rendering:** show the user one line per product (name, chosen file, the minute it appears), with the sheet. Nothing is rendered before they say OK. If no file is the product, say so and leave that one out; don't use a look-alike.
5. **Prepare it:** a photo is cut out with `<skill>/scripts/cover/cutout.py` (as for the cover, with its check image; a see-through cut-out looks broken). A clip needs a 2 to 3 s stretch where the product is clear: set `clipStart`. Copy the file into the Remotion project's `public/` folder.
6. **Render** `ProductPop` with `image` or `clip`, the brand's colours and font, and the video's `fps`, `width` and `height`. Add `name` (and `price` only if the user gave it or it's said) to show the name too; then don't add a separate `ProductTag` for that moment.
7. **Place it beside the temple, never over the product in the hand.** Extract the frame where it starts and run `<face python> -I <skill>/scripts/popplace.py <frame.png> <face_landmarker.task> --hands <hand_landmarker.task> --image <cut-out.png> [--clip] [--label] --caption-top <caption area from my-setup.md>`. It centres the pop-in at temple height right beside the face, on the side with more room. It never covers a hand or the product it holds: if they are in the way it goes smaller and lifts above them, or uses the other side, or leaves out the name under the picture, and it says what it did. It prints `side`, `margin`, `top` and `size` for the props; if it prints `"name": null`, leave the name out. If it says there's no room, skip that pop-in and tell the user. Then place the clip like the emojis, starting a few frames after the name is said. Never over the logo or the captions either. Tested on three real frames (a lipstick held up on the only free side, a turned head with a brush in the hand, a face cut by the frame edge): the picture sat beside the head every time and covered neither the face nor what was in the hand.
8. **Sound:** `pop.wav` on its first frame (`references/sound.md`, Sound effects), at the usual 0.36 to 0.54.
9. **Check** one frame mid-pop and one fully shown on the real footage, and confirm the video's frame count didn't change.

Use it for the main products, once each, unless the user asks for more. Tested: a photo and a clip popped in and out cleanly on a real frame, the frame count stayed the same, and the pop sound landed on the first frame.

Without Remotion, the FFmpeg fallback grows the cut-out in over 0.2 s and overlays it (tested; the frame count stays the same). Give the cut-out as the second input with `-loop 1 -t <seconds> -itsoffset <start>`, then:

```
[1:v]format=rgba,scale=w='trunc(<width>*min(1,max(0.05,(t-<start>)*5))/2)*2':h=-1:eval=frame[p];
[0:v][p]overlay=x=<x>:y=<y>:eval=frame:enable='between(t,<start>,<end>)',format=yuv420p[v]
```

It has no bounce, tilt, label or clip card, so say that it's a simpler animation.

## Animated emojis

Add these when the user asks; don't ask them to supply emoji files.

- **Source:** Remotion with `<skill>/scripts/remotion/EmojiPop.tsx`. It renders one short 43-frame clip per emoji in full color, with the emoji and position passed in `--props`. FFmpeg's `ass` filter doesn't show color emoji reliably, so don't use captions for these. Use Noto Color Emoji (free to reuse) or the system emoji font; don't use Apple's emoji, which can't be reused freely. Twemoji requires credit.
- **Placing:** FFmpeg places each clip with `setpts=PTS-STARTPTS+<frame>/(<fps>*TB)` and `overlay=...:eof_action=pass`. That's much faster than one transparent overlay as long as the whole video.
- **Timing:** read the caption times from the `.ass` file and match each emoji to the word it illustrates. Start it a few frames after that caption appears, and end it with the caption or before the next emoji.
- **Look:** 150 px, a spring pop, a small wobble, a soft shadow. Keep it off the face and away from captions, logos and text. Pick a clear spot for each video, away from where the speaker moves: spots near head height can touch the hair when the speaker leans.
- **Layer order:** footage, retouch, title, product tags, emojis, then captions (or the word highlight captions) and handle, and finally the end card.
- **Choosing:** match literal words in the speech. Offer to pick them if the user only asks for "emojis". Use them only occasionally unless asked for more, and say which ones you'd remove first if it feels busy.
- **Check:** look at one frame per emoji to confirm full color and that nothing important is covered.
