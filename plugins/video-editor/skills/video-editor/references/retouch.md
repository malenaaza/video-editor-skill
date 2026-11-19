# Skin and teeth retouch, and background blur

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

## Retouch

**Never edit the scripts for a video.** Levels that differ from the defaults go in a `retouch.json` in the build folder, where the scripts are run; each script prints the settings it's using. `<skill>/scripts/retouch/settings.py` lists every setting, its default and the colour key format. Values that belong to a person (their skin threshold) are also saved in `my-setup.md`, and copied into each new project's `retouch.json`.

Retouch when the brand's `Look:` lines say "every video", or when the user asks. Color alone can't separate skin from things like cardboard, so use face-tracked masks. Files are in `<skill>/scripts/retouch/`: `mask.py` builds the masks, `retouch.txt` is the FFmpeg filter.

1. Render a clean edit (cuts, Log conversion, grade, zooms; no title, captions or handle) as `clean.mp4`, with the in-between encoder. The filter runs underneath the text so the text stays sharp.
2. From that folder, build `skin.mkv`, `teeth.mkv` and `skin_strong.mkv`:

```
<face python> -I <skill>/scripts/retouch/mask.py "<face_landmarker.task>"
```

3. Copy `retouch.txt` into the folder, set the levels from `my-setup.md`, and apply it, setting `-frames:v` to the frame count of `clean.mp4`:

```
ffmpeg -i clean.mp4 -i skin.mkv -i teeth.mkv -i skin_strong.mkv -/filter_complex retouch.txt -map "[v]" -frames:v <count> <8-bit in-between encoder> retouched.mp4
```

   With background blur as well, use `retouch-blur.txt` instead: the same retouch, then the blur, in one pass. Add `bgmask.mkv` as the fifth input (after `skin_strong.mkv`) and set the blur sigma in it.

4. Add the title, captions, handle and end card to `retouched.mp4`, then do the final export.

**Colour grade and colour keys:** the colour keys for the blur (clothing, held objects) are sampled on one picture, so they only work on that picture. Changing the grade afterwards (a gentler boost, a different LUT) can make a key miss the sweater. Render the clean edit twice: with the grade the keys were sampled on, to build the masks from, and with the final grade, which gets retouched and blurred with those masks. The masks follow the shapes, not the grade, so they apply to the other render. Check one blurred frame of the final render. A script that does this renders both from the same `cut-filter.txt` by changing only the grade at the end of the video filter.

**Skin tones:** the skin mask finds skin by its red level (`skin_cr_min` in `retouch.json`, default 139), tuned on one person's light-to-medium skin. On the first retouch for a new person, look at a frame of `skin.mkv` next to the video. If parts of the face are missing, lower `skin_cr_min`; if hair or background is included, raise it. Save the value in `my-setup.md`. Do the same for `lips_cr_min`, which decides when the lips count as visible for teeth whitening.

Default levels are in `my-setup.md`. If the user asks for more or less, change one step at a time and save it. To change only the skin strength without rebuilding masks, scale the skin mask in the filter: `format=gray,lut=y='min(val*1.13,255)'`.

The mask protects the eyes, brows, lips and mouth (the eyes with a margin of `protect_eyes`, default 15 px, the lips and mouth with 25), and only whitens teeth while the lips are visible, so objects passing the mouth aren't touched. Compare close-ups before and after, including a frame where teeth show. Say so if braces or shadows limit the result. Report how many frames had no face detected.

**Neck and clothing:** the skin area includes the neck under the jaw (`neck`, on by default); a softened face over an untouched neck looks odd. `skin_cr_max` keeps very red pixels out, so a red top or scarf isn't softened. Check one frame of `skin.mkv` that shows the neck and the top.

**Close-ups:** the same softening that looks right when the face is a normal size leaves texture visible when the speaker leans in or a punch-in zooms: pores are magnified 3 to 4 times. `skin_strong.mkv` adds a second, stronger softening (`bilateral=sigmaS=12:sigmaR=0.10`) on top of the normal one, ramping from nothing when the face is below `close_lo` of the frame height to full above `close_hi`, smoothed between frames so it doesn't flicker. Show the user before/after frames of the biggest-face moments before the full render. If they want it stronger, weaker, or starting earlier, change `close_lo`/`close_hi` in `retouch.json` or the second bilateral, one step at a time, and save it in `my-setup.md`.

**Beautify (a light, natural touch):** one setting, `"beautify": "light" | "medium" | "strong"` in `retouch.json` (default `"off"`), that sets the skin softening and three small extras together: a soft **glow** (a slight lift of the skin's brightness), brighter **under-eyes** (the band below each lower lid, where dark circles sit) and whiter **eye whites** (brightened and de-reddened, never the iris). The glow lifts the skin's brightness and gives back, on the skin only, the colour that lifting takes away, leaning very slightly to red rather than yellow: brightness alone made skin look pale and grey next to the original, and a whole-picture colour boost to fix that turned rosy cheeks orange. The hue stays within about a degree of the original (a test checks light to deep skin tones). It adds only a little colour, so it does not stack with the brand's colour boost (`Look, color`), which has already been applied in the clean render before this pass; if the brand uses the boost, `light` or `medium` is usually enough. **If the user finds the skin grey or orange after beautify, don't add a whole-picture saturation boost on top:** compare the cheeks with the clean render, same frame, and fix the hue first. **There is no makeup and no reshaping, and none is ever added**: no lip or blush colour, no slimming, no bigger eyes. If the user asks for those, say it isn't something this skill does.

| | skin_strength | close-up softening starts at | glow | under_eye | eye_white |
|---|---|---|---|---|---|
| light | 0.55 | 38% of frame height | 0.012 | 0.025 | 0.05 |
| medium | 0.72 | 34% | 0.022 | 0.045 | 0.09 |
| strong | 0.88 | 31% | 0.035 | 0.065 | 0.13 |

Anything written in `retouch.json` next to `beautify` wins over the preset (for example `"beautify": "light", "glow": 0.03`). The steps, after `mask.py` has built the masks with this `retouch.json` (it builds `undereye.mkv` and `eyewhite.mkv` too) and the retouch filter has made `retouched.mp4`:

1. `<face python> -I <skill>/scripts/retouch/beautify.py` writes `beautify.txt` and prints the FFmpeg command: it adds the extras to `retouched.mp4` in one more pass (an extra in-between encode).
2. Use its result as the picture for the title, captions and emojis.
3. Show a before and after frame from the user's own video before the full render, as for every retouch. Tested on a real close-up: the effects stay inside the skin, under-eye and eye-white areas (everything else moved by about 0.01 levels), with no artifacts at any level. On footage that was already retouched the steps between levels are subtle; on raw footage the smoothing does more.

**Be honest with the user about product videos.** Smoothing and glow can make a foundation, concealer or skincare result look better than it is, and some advertising rules (the UK's, for one) say a filter must not exaggerate what a product does; platforms may also expect heavy filter use to be disclosed. For a video that judges a base product or skincare, suggest `off` or `light`, and offer to say in the caption that a light touch-up was used. Never turn it on for a brand that hasn't chosen it.

**Eyebrows:** the brows are protected by their own dark hairs (`brow_mode`, default `"hair"`), not by a margin around the whole brow. A margin of 25 px, then 15, still left the skin around the brows and on the lid below them textured, with a ring of untouched skin next to the smoothed forehead; protecting only the hairs smooths that skin and keeps the hairs crisp (checked on a real close-up). If fine or pale hairs get smoothed, lower `brow_contrast` (default 14); if texture near the brows is kept, raise it. `"brow_mode": "margin"` gives the old behaviour, with `protect_brows` as the margin.

**Turned faces:** when the speaker turns their head, the tracker's face outline on the far side lies well inside the real cheek (on a real frame it ran through the middle of the cheek, 70 to 90 px short of the silhouette), so that cheek kept every freckle and pore while the rest of the face was smooth. `mask.py` therefore also softens skin-coloured pixels that touch the face inside a wider area around the outline (`region_grow`, default `[1.35, 1.1]`; `[1, 1]` switches it off). Hair, background and the red top are excluded by colour, and the ear stays sharp. Check a frame of `skin.mkv` from a shot with the head turned, and if the cheek's edge is still missing, raise the first number a step.

**Faces cut off by the frame edge:** in a tight close-up, or on a punch-in, half the face can be outside the frame. MediaPipe then finds no face, the skin mask comes out empty, and that stretch is left unsoftened: skin that looked right in the wide shots shows every pore. The scripts handle it: when the tracker finds no face, `facetrack.py` pastes a mirror image of the visible side next to the edge, finds the face in that, and maps the points back (tested on a real close-up, where the plain frame gave no face and the mirrored one gave an oval that fit the visible cheek and jaw). `mask.py` and the blur scripts print how many frames were found this way. It is on by default; set `"edge_faces": false` in `retouch.json` to turn it off. Look at a frame of `skin.mkv` from the tightest shot before the full render. Frames where the face is fully covered or turned away still get no mask, so `no face` in the printout is not always zero.

**Small faces:** in full-body framing the face tracker can miss most frames. Run detection on a 2x enlarged crop around the head, track it from frame to frame, and map the points back.

## Background blur

**First check the background isn't blurred already.** Phones' Cinematic and Portrait modes, and cameras with the lens wide open (the Sony ZV-E10's Background Defocus), blur the background while filming. Run `<face python> -I <skill>/scripts/retouch/blurcheck.py <clean.mp4 or the source> <face_landmarker.task>` before offering blur, even when the brand's `Look:` line says every video. It compares how crisp the background beside and above the head is with the face, over 8 frames: under 0.35 ("already soft") don't add blur and tell the user why in one line; 0.35 to 0.6 ("a little soft") offer it only if they want it softer, one level lower; over 0.6 ("sharp") go on as below. On a real clip the sharp original measured 1.05 and the same clip with this skill's blur 0.19. A plain wall also reads as soft, which is right: there's nothing to blur. When the footage was filmed in Cinematic or Portrait mode, look at a frame where a product is held up: that mode guesses the speaker's outline and can blur a product held towards the camera, which can't be fixed afterwards. If it's soft, say so and suggest filming product videos in the normal mode, letting this skill blur the background while keeping held products sharp. Save what the user says in the camera's line in `my-setup.md` (for example "iPhone, Blackmagic app, Cinematic mode: background already blurred") so the check isn't needed for that setup every time.

Add this when the brand's `Look:` lines say "every video", or when the user asks. A blur forgives small mask mistakes, so it's much faster and safer than replacing the background. If the user wants a background changed, offer this first: replacing it took about 45 minutes on one video, and the cutout failed whenever a held object moved or came close to the camera.

Files in `<skill>/scripts/retouch/`: `blurmask.py` (builds the mask from `clean.mp4`), `background-blur.txt` (blur alone: the start of the FFmpeg filter, with `clean.mp4` as input 0 and the mask as input 4, or renumber it), and `retouch-blur.txt` (retouch and blur together). Set the sigma from `my-setup.md`.

1. Test first. Pass frame numbers to get `bg/blurtest.png`, including frames where the speaker or an object moves:

```
<face python> -I <skill>/scripts/retouch/blurmask.py "<face_landmarker.task>" 30 75 100 150
```

2. Run with no frame numbers to build `bgmask.mkv`.
3. Add the mask as an extra input and run the blur before the title, emoji and caption steps, so text stays sharp. With retouch, both run in one pass with `retouch-blur.txt`.

- **A tall headband, hat or hair above the head:** the head area stops at the face outline, so a braided headband above the hairline was blurred. Add `"crown": {"grow": [1.45, 1.30], "raise": 0.36}` to `retouch.json`: the outline scaled by `grow` and raised by `raise` times the face height is kept sharp too (checked on a real frame: the headband stayed sharp, and the top of it was blurred without the setting). Raise `raise` if the top of the hair still blurs when the speaker looks down.
- **Keep sharp:** the mask uses face tracking for the head and neck, and colors for held objects, clothing and skin. For each video, sample the held object and the clothing in Lab and HSV on a frame (guessed values fail), and write them as `blur_keys` in `retouch.json`, for example `{"blur_keys": [{"name": "cardboard box", "lum": [106, null], "a": [2, 8], "b": [5, 19], "hue": [9, 24], "sat": [null, 94]}]}`. With no keys, only the head, neck and skin stay sharp. If the speaker's skin blurs, set `blur_skin` the same way.
- **Don't keep only the largest shape:** the head and a held object can be separate. Remove only small specks.
- **Hands holding products:** whenever the speaker holds a product, use `blurmask_hands.py`, never `blurmask.py` (which keeps products sharp only by colour). The area kept sharp is the hand plus `hand_pad` (default 120) and stretches past the fingers along the direction the hand holds the product (`hand_reach`, default 0.4 hand lengths): a serum's cap held up above the fingers was 72% blurred with a 60 px ring and up to 9% with 120, and none with the stretch. If the far end of a long product still blurs, raise `hand_reach`. A hand the tracker misses is looked for again in that frame, and while it's lost the area grows, because the hand may have moved. **Before saying a product was soft in the camera, compare with `clean.mp4` at the same time:** a screenshot from the finished video already has the background blur in it, so it can't show what the camera recorded (this was got wrong once, and the user was right: the skill had blurred the cap). It adds hand tracking and keeps a generous area around each hand sharp, so anything held stays sharp whatever its color. Give the clothing color as a key in `blur_keys`. It runs at half resolution, about 0.17 s per frame on a laptop CPU. With `write` it builds the mask and the test sheet in one pass, so don't run a separate test over a long video:

```
<face python> -I <skill>/scripts/retouch/blurmask_hands.py clean.mp4 bgmask.mkv "<face_landmarker.task>" "<hand_landmarker.task>" write 900 2300 3500
```

- **Hair:** if the top of the hair blurs when the speaker looks down, enlarge and raise the head area (about 1.4 x 1.6 of the face oval, raised by 45 px, worked in close framing). Keeping everything below about half the frame height sharp helps when products held at the edge have no tracked hand.
- **Brand props** that should stay sharp (a shopping bag, a product display): `keepsharp.py` removes blur from a fixed polygon in an existing mask and follows punch-in zooms. Check a zoomed shot, because the prop shifts there.
- **Check:** look at frames from every shot. Ask the user to check for flicker at hair and object edges while they watch.
