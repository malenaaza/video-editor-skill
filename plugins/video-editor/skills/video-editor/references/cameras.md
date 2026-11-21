# Cameras and apps: checking how a video was recorded

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

Read this the first time a video comes from a camera, phone or app that isn't in `my-setup.md`'s `Cameras / phones:`
line yet, or when the user asks what settings to use.

## Run the checks

```
python -I <skill>/scripts/footcheck.py <source video> --mains <50 or 60> [--shorts] [--target vertical|wide]
<face python> -I <skill>/scripts/retouch/blurcheck.py <source video> <face_landmarker.task>
```

- `--mains`: 50 in Spain, the rest of Europe, the UK, most of Africa, Asia, Australia and South America; 60 in North
  America, Mexico, Brazil, parts of Central and South America, Taiwan, South Korea, the Philippines and western
  Japan. Ask once if the country isn't in `my-setup.md`, and save it.
- `--shorts` when the horizontal recording will also be cut into Shorts; `--target` where the video goes.
- `blurcheck.py` says whether the background is already blurred (Cinematic or Portrait mode, a lens wide open):
  then don't offer background blur (`references/retouch.md`).

Tell the user the findings in a few plain lines, the most useful first (usually the sound and the frame rate), as
advice for the **next** recordings: this video is edited as it is. Never lecture: if they chose something on purpose
(24 fps for a film look, the front camera to see themselves), note it and don't raise it again. Save the camera, the
app and what was agreed in `my-setup.md`, for example: "iPhone 16 Pro Max, Blackmagic Camera app: 4K 25 fps, shutter
1/50, back camera with remote monitoring, mic receiver plugged in (checked 2026-11-19)". Run the check again only
when the camera or app changes, or a video looks or sounds wrong.

## What the file says, by app

`footcheck.py` reads the file's own details. How sure it is depends on what each app writes:

| App or camera | Recognised by | Settings it can read | Confirmed on a real file |
|---|---|---|---|
| Blackmagic Camera (iPhone, Android) | `com.blackmagic-design.*` tags and its name in `software` | frame rate, shutter, ISO, white balance, lens (front or back), aperture | yes (iPhone 16 Pro Max, app 3.5) |
| iPhone Camera app | Apple make and model, no app name | frame rate, size, HDR, sound | not yet |
| Final Cut Camera | its name in `software` | frame rate, size | not yet |
| Samsung, Pixel and other Android camera apps | Android or maker tags | frame rate, size, HDR, sound | not yet |
| GoPro | GoPro handler or firmware tags | frame rate, size | not yet |
| DJI (Osmo Pocket and others) | DJI handler or encoder | frame rate, size | not yet |
| Sony cameras | XAVC brand or Sony make | frame rate, size | not yet |
| Saved through Instagram, TikTok, CapCut, WhatsApp | low bit rate and no camera details | frame rate, size | heuristic |

When the app isn't recognised, the general checks still run, and Claude asks once which app or camera was used. When
a user's file shows a new app's tags, add them to `identify()` in `footcheck.py`, mark the row confirmed, and add a
test with those tags (never the video).

## The settings, by app

The fixes `footcheck.py` prints come from this table (`STEPS` in the script). Menu names change between versions:
if the user can't find one, ask what they see and guide them from there.

- **Blackmagic Camera:** frame rate, shutter, ISO and resolution are at the top of the screen; tap one to change it.
  Shutter at twice the frame rate (1/50 at 25 fps), or a 180° shutter angle. Back main camera (1x) for the best
  picture; to see yourself, the app's remote monitoring shows the picture on a second phone or tablet. Lock white
  balance and focus before recording.
- **iPhone Camera app:** Settings > Camera > Record Video: 4K, and Show PAL Formats for 25 fps; HDR Video off unless
  the user grades HDR. The app sets the shutter itself. Record Sound > stereo.
- **Final Cut Camera:** manual controls for frame rate, shutter, ISO and focus, like Blackmagic.
- **Samsung and other Android phones:** Pro video mode for frame rate and shutter (S); if 25 fps isn't offered, 30
  fps, and check the lights don't flicker. HDR10+ off unless graded.
- **Sony cameras:** NTSC/PAL Selector (Setup menu) to PAL for 25p and 50p; movie mode shutter at 1/50; XAVC S 4K.
- **GoPro:** Anti-Flicker or Video Format to 50 Hz / PAL in Spain, then 25 fps.
- **DJI:** Anti-flicker to 50 Hz in Spain, frame rate 25 fps.
- **Any app, sound:** 44.1 or 48 kHz. 16 kHz or less means a Bluetooth mic: connect the mic's receiver by its plug
  or cable instead.
- **Social apps:** recording inside Instagram, TikTok, CapCut or Edits, or sending the file over WhatsApp, squeezes
  it. Record with the camera app and send the original file (AirDrop, a cable, a cloud folder with original
  quality).

## Two cameras: the main one, and an iPhone for some lines

The easy way to change angle: the main camera films most of the video and the iPhone films a few lines (the hook,
the ending, a close-up). They don't film at the same time, so there is nothing to sync: each take is its own clip
and the angle changes where one clip ends and the next begins, between sentences. Filming everything with both at
once is real multicam; the skill doesn't do it, and it's much more work while filming.

**Before filming,** tell the user once:
- the same frame rate on both (25 fps in Spain; iPhone: Settings > Camera > Record Video, Show PAL Formats), and
  HDR Video off on the iPhone;
- the iPhone on a stand, with exposure and focus locked (press and hold on the screen);
- the same light, clothes and position in every take, and the same microphone for both if they have one, because
  the two cameras' own sound differs;
- film the iPhone lines one after another, not swapping camera every sentence. Mark them in the shot list
  (`references/script.md`).

**In the edit,** run the footage check (above) once for the iPhone, then make each iPhone clip match the main camera
before transcribing it:

```
python -I <skill>/scripts/conform.py <iphone clip> --like <main camera clip> --check
python -I <skill>/scripts/conform.py <iphone clip> --like <main camera clip> --encoder "<in-between encoder>"
```

`--check` only lists what differs. Without it, it writes `<clip>-conformed.mov`: the main camera's frame rate at a
constant rate (phones record a variable one, which makes the sound drift), its size (a clip filmed the other way
round is cropped to fill, or `--fit pad` for bars), HDR tone mapped to SDR, Rec.709 tags, and the main camera's
sample rate and channels. Tell the user the lines it prints in one short message. Then the clips go through the
usual steps, and their voices are joined at one loudness with `voice/leveljoin.py` (`references/sound.md`).

**Colour is not matched by the script:** the two cameras' white balance, contrast and saturation differ. Put a
frame of each side by side, correct the iPhone clips in the grade until skin and the background match, and show
the user the pair before the full render.

