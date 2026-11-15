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

**Skin tones:** the skin mask finds skin by its red level (`skin_cr_min` in `retouch.json`, default 139), tuned on one person's light-to-medium skin. On the first retouch for a new person, look at a frame of `skin.mkv` next to the video. If parts of the face are missing, lower `skin_cr_min`; if hair or background is included, raise it. Save the value in `my-setup.md`. Do the same for `lips_cr_min`, which decides when the lips count as visible for teeth whitening.

Default levels are in `my-setup.md`. If the user asks for more or less, change one step at a time and save it. To change only the skin strength without rebuilding masks, scale the skin mask in the filter: `format=gray,lut=y='min(val*1.13,255)'`.

The mask protects the eyes, brows, lips and mouth, and only whitens teeth while the lips are visible, so objects passing the mouth aren't touched. Compare close-ups before and after, including a frame where teeth show. Say so if braces or shadows limit the result. Report how many frames had no face detected.

**Neck and clothing:** the skin area includes the neck under the jaw (`neck`, on by default); a softened face over an untouched neck looks odd. `skin_cr_max` keeps very red pixels out, so a red top or scarf isn't softened. Check one frame of `skin.mkv` that shows the neck and the top.

**Close-ups:** the same softening that looks right when the face is a normal size leaves texture visible when the speaker leans in or a punch-in zooms: pores are magnified 3 to 4 times. `skin_strong.mkv` adds a second, stronger softening (`bilateral=sigmaS=12:sigmaR=0.10`) on top of the normal one, ramping from nothing when the face is below `close_lo` of the frame height to full above `close_hi`, smoothed between frames so it doesn't flicker. Show the user before/after frames of the biggest-face moments before the full render. If they want it stronger, weaker, or starting earlier, change `close_lo`/`close_hi` in `retouch.json` or the second bilateral, one step at a time, and save it in `my-setup.md`.

**Small faces:** in full-body framing the face tracker can miss most frames. Run detection on a 2x enlarged crop around the head, track it from frame to frame, and map the points back.

## Background blur

Add this when the brand's `Look:` lines say "every video", or when the user asks. A blur forgives small mask mistakes, so it's much faster and safer than replacing the background. If the user wants a background changed, offer this first: replacing it took about 45 minutes on one video, and the cutout failed whenever a held object moved or came close to the camera.

Files in `<skill>/scripts/retouch/`: `blurmask.py` (builds the mask from `clean.mp4`), `background-blur.txt` (blur alone: the start of the FFmpeg filter, with `clean.mp4` as input 0 and the mask as input 4, or renumber it), and `retouch-blur.txt` (retouch and blur together). Set the sigma from `my-setup.md`.

1. Test first. Pass frame numbers to get `bg/blurtest.png`, including frames where the speaker or an object moves:

```
<face python> -I <skill>/scripts/retouch/blurmask.py "<face_landmarker.task>" 30 75 100 150
```

2. Run with no frame numbers to build `bgmask.mkv`.
3. Add the mask as an extra input and run the blur before the title, emoji and caption steps, so text stays sharp. With retouch, both run in one pass with `retouch-blur.txt`.

- **Keep sharp:** the mask uses face tracking for the head and neck, and colors for held objects, clothing and skin. For each video, sample the held object and the clothing in Lab and HSV on a frame (guessed values fail), and write them as `blur_keys` in `retouch.json`, for example `{"blur_keys": [{"name": "cardboard box", "lum": [106, null], "a": [2, 8], "b": [5, 19], "hue": [9, 24], "sat": [null, 94]}]}`. With no keys, only the head, neck and skin stay sharp. If the speaker's skin blurs, set `blur_skin` the same way.
- **Don't keep only the largest shape:** the head and a held object can be separate. Remove only small specks.
- **Hands holding products:** use `blurmask_hands.py` instead. It adds hand tracking and keeps a generous area around each hand sharp, so anything held stays sharp whatever its color. Give the clothing color as a key in `blur_keys`. It runs at half resolution, about 0.17 s per frame on a laptop CPU. With `write` it builds the mask and the test sheet in one pass, so don't run a separate test over a long video:

```
<face python> -I <skill>/scripts/retouch/blurmask_hands.py clean.mp4 bgmask.mkv "<face_landmarker.task>" "<hand_landmarker.task>" write 900 2300 3500
```

- **Hair:** if the top of the hair blurs when the speaker looks down, enlarge and raise the head area (about 1.4 x 1.6 of the face oval, raised by 45 px, worked in close framing). Keeping everything below about half the frame height sharp helps when products held at the edge have no tracked hand.
- **Brand props** that should stay sharp (a shopping bag, a product display): `keepsharp.py` removes blur from a fixed polygon in an existing mask and follows punch-in zooms. Check a zoomed shot, because the prop shifts there.
- **Check:** look at frames from every shot. Ask the user to check for flicker at hair and object edges while they watch.
