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
| `TitleCard` | The hook title in the first seconds | `lines` (1 to 3 short lines), `highlight` (one word in the accent color), `top` | 2.5 s |
| `ProductTag` | Product name and price when a product is shown | `name`, `price` (written as it should appear, e.g. `€24,90`), `note` (e.g. "Link in bio"), `side`, `top` | 3.5 s |
| `EmojiPop` | Emojis on words (see Animated emojis below) | `emoji`, `left`, `top` | 43 frames |
| `CoverCard` | Cover image with the products (see `references/cover.md`) | `background`, `products` (one `image` each), `faceX`/`faceY`/`faceSize`, `lines` | a still: `npx remotion still` |

Shared style props: `font`, `fontFile`, `fontSize`, `textColor`, `boxColor` (`transparent` for no box), `accentColor`, `seconds`.

- **TitleCard:** keep it under about 6 words. Start it on the first frame, or a few frames in if the video opens on a word. Keep it below the app's top bar and off the face (see Titles and captions in Rule 10). When the brand's title style in `my-setup.md` is a still title, use that instead unless the user asks for an animated one.
- **ProductTag:** show it when the product is first named or held up, starting a few frames after the name is said. Use it only for the main products, once each, unless asked for more. Keep it above the caption area from `my-setup.md` and on the side away from the speaker's face and the product. Put the price only if the user gave it or it's said in the video; never guess a price.
- **Placing:** the same as emojis: `setpts=PTS-STARTPTS+<frame>/(<fps>*TB)` and `overlay=0:0:format=rgb:eof_action=pass`, with `format=rgba` on both inputs.
- **Check:** look at one frame mid-animation and one fully shown for each graphic, on the real footage: text readable, nothing covering the face, product, captions or logo.

## Animated emojis

Add these when the user asks; don't ask them to supply emoji files.

- **Source:** Remotion with `<skill>/scripts/remotion/EmojiPop.tsx`. It renders one short 43-frame clip per emoji in full color, with the emoji and position passed in `--props`. FFmpeg's `ass` filter doesn't show color emoji reliably, so don't use captions for these. Use Noto Color Emoji (free to reuse) or the system emoji font; don't use Apple's emoji, which can't be reused freely. Twemoji requires credit.
- **Placing:** FFmpeg places each clip with `setpts=PTS-STARTPTS+<frame>/(<fps>*TB)` and `overlay=...:eof_action=pass`. That's much faster than one transparent overlay as long as the whole video.
- **Timing:** read the caption times from the `.ass` file and match each emoji to the word it illustrates. Start it a few frames after that caption appears, and end it with the caption or before the next emoji.
- **Look:** 150 px, a spring pop, a small wobble, a soft shadow. Keep it off the face and away from captions, logos and text. Pick a clear spot for each video, away from where the speaker moves: spots near head height can touch the hair when the speaker leans.
- **Layer order:** footage, retouch, title, product tags, emojis, then captions and handle, and finally the end card.
- **Choosing:** match literal words in the speech. Offer to pick them if the user only asks for "emojis". Use them only occasionally unless asked for more, and say which ones you'd remove first if it feels busy.
- **Check:** look at one frame per emoji to confirm full color and that nothing important is covered.
