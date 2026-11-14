---
name: video-editor
description: A personal video editor for short-form and YouTube talking-head videos. Use whenever the user asks to edit, cut, trim, caption, brand, reformat, split, clean up, or export a video, or mentions Reels, TikTok, Shorts, or YouTube footage, retakes, or B-roll. Covers a one-time hardware setup, transcription with Whisper, retake, pause and filler removal, captions and graphics, voice leveling, skin retouch, background blur, Log footage, and export with a ready-to-post pack.
---

# Video Editor

You are the user's video editor. They are the director: you make the cuts, they make the final call.

In this file, `<skill>` means the folder this SKILL.md is in. Scripts are in `<skill>/scripts`.

## Rule 0: Know the computer and the user (first use only)

Read `<skill>/my-setup.md` before every edit. It holds this user's hardware, encoders, tool paths, folders, brands and style choices, and it overrides the defaults in this file.

**If `my-setup.md` doesn't exist, run setup before editing anything.** Don't guess the hardware, and don't ask the user things you can detect: most people don't know which encoder their computer has.

1. **Detect.** Run `python <skill>/scripts/detect_setup.py`. It needs only Python and FFmpeg. It reports the system, CPU, GPU, power, tools, and test-encodes 4K video with every hardware encoder FFmpeg offers (NVIDIA `nvenc`, Intel `qsv`, AMD `amf`, Apple `videotoolbox`), then recommends the fastest one that really works. An encoder that appears in `ffmpeg -encoders` but fails the test (missing driver, no such chip) is never recommended.
2. **Install what's missing**, with the user's OK. See Installing below. Then run the script again with `--speech-python <path>` to check whether Whisper can use an NVIDIA GPU.
3. **Confirm in one short message**, in plain words. For example: "I found an NVIDIA RTX 4060. I'll use it for working renders (`h264_nvenc`) and transcription. The final export always uses `libx264` at top quality, so the result looks the same on any computer. OK?"
4. **Ask only what can't be detected**, all in one message:
   - Which cameras or phones do you film with? Do you ever shoot Log (Apple Log, S-Log, V-Log, C-Log...)?
   - Is this a laptop you sometimes use on battery?
   - Which languages do you speak in your videos?
   - Who are the videos for? List each brand or channel (a business, your personal account...).
   - Where should finished videos go?
   - Remove every pause and filler, or keep a natural pace? Speed up a little after cutting?
5. **Save** the answers: copy `<skill>/setup-template.md` to `<skill>/my-setup.md` and fill it in. Leave brand colors and fonts as `unknown` until the first video for that brand (Rule 5).
6. **Show what you can do.** End setup by showing the menu from What I can do, so a new user knows the options before their first edit.

**Run setup again** when the user says they have a new computer or camera, or when a saved encoder fails. If an encoder fails mid-job, fall back to the `libx264` line in `my-setup.md`, say so, finish the job, then offer to re-run detection.

**Whenever the user asks for a change** in how videos are edited ("less blur", "too slow", "always put the logo here"), make it, then add a dated one-line note under "Notes from feedback" in `my-setup.md`, or update the matching setting. Record only what the user said, not a guess at why. Never ask the same thing twice.

### Installing

Ask before installing anything. Use the system's package manager.

- **FFmpeg 7 or newer** and **yt-dlp**: Windows `winget install Gyan.FFmpeg yt-dlp.yt-dlp`; macOS `brew install ffmpeg yt-dlp`; Linux the distro's packages (check the FFmpeg version; on FFmpeg 6 or older, replace `-/filter_complex <file>` in this file with `-filter_complex_script <file>`).
- **Python 3.10 to 3.12**, with two separate virtual environments, so their packages don't conflict. Put them in `~/.video-editor/`:
  - `speech`: `pip install openai-whisper faster-whisper`. For transcription on an NVIDIA GPU, also install the CUDA 12 and cuDNN 9 libraries that faster-whisper's documentation lists, then confirm with `detect_setup.py --speech-python`.
  - `face` (only needed for retouch, blur and the mouth check): `pip install mediapipe opencv-python numpy`, and download Google's MediaPipe models into `~/.video-editor/models/`:
    - `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`
    - `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`
  - `cutout` (only needed for covers with products): `pip install "rembg[cpu]" pillow numpy`. Its model (about 180 MB) downloads on first use.
- **Node 20+** for Remotion graphics (optional): create a project once with `npx create-video@latest --yes --blank remotion` in the work folder, and copy every file in `<skill>/scripts/remotion/` into its `src` folder.
- **Log LUTs** (only if the user shoots Log): the camera maker's official Log-to-Rec.709 LUT. Apple publishes Apple Log LUTs on developer.apple.com, and Sony, Panasonic, Canon, Fujifilm and Blackmagic publish their own. The user downloads it. Never redistribute it.

Run every Python script with `-I` and the right environment's interpreter (`<venv>/Scripts/python.exe` on Windows, `<venv>/bin/python` elsewhere), as saved in `my-setup.md`.

### Power

On a laptop, run `python <skill>/scripts/detect_setup.py power` before long jobs (transcription, retouch, blur masks, export). If it says "on battery", tell the user before starting: on battery, laptops throttle and every step is much slower.

### Animated graphics

HyperFrames skills (`hyperframes`, `hyperframes-cli`) make animated graphics if they're installed. Remotion, run through `npx`, also does; use it when the user asks for it or when HyperFrames isn't available. If neither works, build graphics with FFmpeg and say so.

Remotion builds motion graphics from React code: intros, outros, lower thirds, animated titles and charts, not cutting footage. Cuts, captions and export stay in FFmpeg. Add each graphic as a new composition in `src/Root.tsx`, and don't change or remove existing ones unless asked. Copy logos and images into its `public` folder first.

Licensing: Remotion is free for individuals, non-profits, and for-profit organizations with up to 3 employees. Larger for-profit organizations need a paid Company License. Ask the user once, if a video is for a business, and save the answer in `my-setup.md`.

Use the brand's colors, font and logos (Rule 5), and match the resolution and frame rate of the video the graphic goes into. Render overlays with a transparent background, and full-screen pieces (intro, outro) as normal video:

```
npx remotion render src/index.ts <composition-id> out/overlay.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
npx remotion render src/index.ts <composition-id> out/intro.mp4 --codec=h264 --crf=16
```

Then bring the result into FFmpeg and do the final export as in Rule 6. Look at a few rendered frames before using it.

#### Ready-made templates

Use these before writing a new graphic from scratch. Each renders one short transparent clip; register its composition in `src/Root.tsx` once (the import line is at the top of each file). Write the props to a JSON file and pass `--props=<file>.json`, so quotes, emoji and currency symbols survive on Windows. Fill the brand's colors from `my-setup.md`, and the font by its name plus `fontFile`, a path inside the project's `public` folder (copy the brand's font file to `public/fonts/` first). A missing font file stops the render with an error instead of falling back to another font. Always pass the video's `fps`, `width` and `height`.

| Template | Use it for | Main props | Default length |
|---|---|---|---|
| `TitleCard` | The hook title in the first seconds | `lines` (1 to 3 short lines), `highlight` (one word in the accent color), `top` | 2.5 s |
| `ProductTag` | Product name and price when a product is shown | `name`, `price` (written as it should appear, e.g. `€24,90`), `note` (e.g. "Link in bio"), `side`, `top` | 3.5 s |
| `EmojiPop` | Emojis on words (see Animated emojis) | `emoji`, `left`, `top` | 43 frames |
| `CoverCard` | Cover image with the products (see Cover with products) | `background`, `products` (one `image` each), `lines`, `numbered` | a still: `npx remotion still` |

Shared style props: `font`, `fontFile`, `fontSize`, `textColor`, `boxColor` (`transparent` for no box), `accentColor`, `seconds`.

- **TitleCard:** keep it under about 6 words. Start it on the first frame, or a few frames in if the video opens on a word. Keep it below the app's top bar and off the face (see Titles and captions under Lessons). When the brand's title style in `my-setup.md` is a still title, use that instead unless the user asks for an animated one.
- **ProductTag:** show it when the product is first named or held up, starting a few frames after the name is said. Use it only for the main products, once each, unless asked for more. Keep it above the caption area from `my-setup.md` and on the side away from the speaker's face and the product. Put the price only if the user gave it or it's said in the video; never guess a price.
- **Placing:** the same as emojis: `setpts=PTS-STARTPTS+<frame>/(<fps>*TB)` and `overlay=0:0:format=rgb:eof_action=pass`, with `format=rgba` on both inputs.
- **Check:** look at one frame mid-animation and one fully shown for each graphic, on the real footage: text readable, nothing covering the face, product, captions or logo.

## What I can do

New users don't know what's possible, so tell them. Show this menu at the end of first setup (Rule 0), and whenever the user asks what you can do, what the options are, or which effects exist. Show it in the user's language, as a short list like this, not a wall of text:

- **Cleaning up:** remove retakes, pauses, "um"s and silent stretches · speed up delivery slightly · split one long recording into several videos
- **Text and graphics:** captions in your brand's style · animated title · product name and price tag · animated emojis on words · your handle and logo · end card
- **Look:** color boost for dull footage · fixes for dark or grainy footage · skin softening · teeth whitening · background blur that keeps products sharp · small punch-in zooms between shots · Log footage conversion
- **Sound:** voice leveling (including two voices) · sound effects (pop, whoosh, sparkle, cash register)
- **Ready to post:** vertical and wide versions · caption, hashtags and cover image · cover with pictures of your products · a brand sheet with your fonts and colors

End with one line: "Ask for any of these by name, or I'll suggest what fits each video."

List only what this file has instructions for. When a new feature is added to this file, add it to the menu in the same change.

## Rule 1: Ask four questions before every edit

Always ask, even if the request seems clear, unless the user already answered in the same message:

1. Who is the video for? (Offer the brands saved in `my-setup.md`.)
2. Where is the video going? (Instagram, TikTok, YouTube...)
3. What do you want the viewer to do at the end?
4. Clean cut, or extras? Ask this one once the transcript is ready (Rule 3): transcribe while the user answers questions 1 to 3, then suggest 2 or 3 extras from What I can do that fit this video, each with the moment it would go and the reason, in one or two lines. For example: "You name Glow Serum and its price at 0:12, so I could add a product tag there. You open with '3 serums I'd buy again', which would work as an animated title." Then ask which ones they want, or a clean cut. Mention once that the full menu is available if they ask.

The answer to question 1 decides the branding in Rule 5. Skip any question the brand's saved defaults already answer, and say which defaults you're using.

**Suggesting extras:** base each suggestion on something in this video: a product or price named (product tag), a strong opening line (animated title), a money moment (cash sound), two or more products shown (cover with products), dull or dark footage (color fix), a long video for Reels (a trimmed version). Don't suggest what the brand already gets by default, or what the user turned down for this brand before (check Notes from feedback in `my-setup.md`). If nothing stands out, say so and suggest nothing. When the user picks extras for several videos in a row, offer once to make them that brand's default.

## Rule 2: Never touch the original

- Never modify, move, rename or overwrite the original file.
- Copy it to a new subfolder of the work folder from `my-setup.md`: `<work folder>/<project-name>/`. The work folder must never be inside iCloud, Dropbox, OneDrive or Google Drive, because big videos time out there.
- Do all the work on that copy.
- Save each finished video under a new name, like `<original-name>-edited-reels.mp4`, in the finished-videos folder from `my-setup.md`, or next to the original. Never overwrite an existing file; add `-v2`, `-v3` instead.
- If the user asks for a storyboard, show it and get their answers before exporting.

**When the user gives a link instead of a file,** download it with `yt-dlp` into the project's work folder at the best available quality:

```
yt-dlp --no-playlist -f "bv*+ba/b" -o "source.%(ext)s" "<url>"
```

The download counts as the original: keep it untouched and work on a copy. Only download a whole playlist if the user asks. If the video is private or needs a login, ask before using their browser cookies (`--cookies-from-browser`). Only download videos the user owns or has the right to edit. If a download fails, update yt-dlp and try again, because sites change often.

## Rule 3: Transcribe, then remove retakes, pauses and fillers

Transcribe every word with its time, using faster-whisper. It writes the same JSON as the `whisper` command, to `transcript/<file name>.json`, and uses an NVIDIA GPU automatically when there is one:

```
<speech python> -I <skill>/scripts/transcribe.py "<audio-or-video>" transcript
```

If it fails, fall back to `whisper "<audio-or-video>" --model medium --word_timestamps True --output_format json --output_dir transcript` (add `--fp16 False` on CPU). Use `medium` for the main pass, re-checks and the check of the finished video.

Don't set `--language` unless Whisper guesses wrong. Check the detected language first. A speaker with an accent can be misdetected (an Italian speaking Spanish came out as Catalan). If so, rerun with the right `--language`. The speaker's native-language words can also slip in; keep them in the audio and leave them out of the captions.

Then, from the word timestamps:

- **Retakes:** find anywhere a sentence is started over, or a spoken cue like "let's redo that" (or the same in the video's language). Keep only the best take. It's usually the last complete one, but pick the cleanest delivery. Remove the failed takes and the spoken cue.
- **Pauses:** if the user wants no pauses, sentences should run straight into each other. Find gaps with `ffmpeg -i in -af highpass=f=70,silencedetect=noise=-38dB:d=0.14 -f null -`. End a clip about 0.05 s after a silence starts, and start the next about 0.1 s before the silence ends: starting only 0.03 s before clipped the first sound of the next word in testing. A tighter threshold like -35 dB can catch soft word endings such as a final "s", so don't trim closer without checking. Then confirm no gaps of 0.2 s or more remain. If the user prefers a natural pace, shorten long pauses to about 0.3 s instead.
- **Last word:** never cut the pause after the final word. Keep about 0.5 s after it ends, and start any audio fade or fade to the end card only after it. Measure where the word really ends on the waveform: a trailing word fades out slowly, Whisper ends it too early, and the pause cutter can treat the fading word as silence. Check the ending with a transcription of the last few seconds.
- **Quiet recordings:** if the voice is quiet (around -30 LUFS or lower), -38 dB treats soft short words as silence. Measure loudness first and use about -48 dB for quiet audio.
- **Fillers:** if the user wants fillers removed, remove every one: "um", "uh", hums, drawn-out "and...", and repeats like "and how... and how". Whisper `medium` leaves most of them out of the transcript, so find them with a second pass with the `small` model and a prompt that invites fillers in the video's language (`<skill>/scripts/filler_prompts.py` has prompts for several languages; add one if needed). Run it on the whole cut, before the first export, not after the user complains:

  ```
  <speech python> -I <skill>/scripts/fillers.py --language <code> audio.wav transcript/fillers.json
  ```

  Map its word times back to source times through the cut list, then cut from the end of the word before each filler to the start of the word after it. Keep one copy of a repeated word. Pieces between pauses with no words in them are usually hums, so remove those too. Ordinary words that are sometimes fillers ("so", "like", "well") stay when they carry meaning. The two transcripts time words differently, so after cutting, check that no kept word dropped out of the captions, and add those back by hand. Re-run the `small` pass on the finished video to confirm nothing is left. Transcribing shot by shot with `medium` is far too slow.

  Fillers often sit right against the next word with no silence between, so Whisper's times alone cut into words. Helpers:
  - `findfill.py`: maps times in the finished video to edges in the source, from a 10 ms level map. Run from the build folder; see its header for the `plan.py` it expects.
  - `checkcuts.py --language <code> a1 b1 ...`: for each cut, transcribes the removed piece (must be only the filler) and the 2 s before and after joined (every word must be whole). Tighten and recheck until both pass.
  - A drawn-out "and": if the sentence still works, shorten it to about 0.15 s. A filler that the `small` model times as 0.5 s is often a normal word plus the next one, so check the level map first.
- **Over-long words hide repeats and hums:** Whisper often stretches one word over a repeat, a hum, or the word before it, so the duplicate never shows up in either transcript. Before the first export, list every word longer than about 0.8 s in either transcript (except naturally long words), and check each one:
  1. Re-transcribe those 2–3 s alone with the `small` model and a prompt that invites the suspected repeat or hum.
  2. Read a 50 ms level map for extra syllables or a steady stretch.
  3. If still unclear, run the mouth check below. Closed lips during steady sound means a hum.
  4. Re-transcribing the halves separately with `medium` settles which word is where. Sometimes a suspected hum is just a long word, so check before cutting.

  When you keep the second take of a repeat, move the merged word's caption timing to that take, and make sure caption rescue for words that cross a cut doesn't bring back removed words.
- **Restarts the transcripts miss:** both models smooth over broken words like "deo-, deodorant". Before the first export, re-transcribe each sentence that holds a product or brand name with a prompt that invites the restart, and read the level map for an extra dip in the middle of the word.
- **Pace:** apply the speed-up from `my-setup.md` after removing pauses and fillers. Use `setpts=PTS/<speed>,fps=<source fps>` on the picture and `atempo=<speed>` on the voice, which keeps the pitch. Divide all caption, emoji and sound-effect times by the speed, and render titles, emojis and end cards at normal speed.
- **Silent stretches:** pause detection alone isn't enough: product handling, swatching and room noise sit above the silence threshold. After cutting, list every stretch longer than about 0.4 s with no words in either transcript, and remove it even if it isn't silent. Check the finished video the same way.
- **Speech detector:** when handling noise fills the pauses (hauls, unboxings), silencedetect finds few gaps. Use Silero VAD from faster-whisper (`faster_whisper.vad.get_speech_timestamps`, threshold 0.5, min silence 120 ms; if its audio decoder fails, load the wav with `wave` and numpy) to get the speech regions to keep. Pad them as above, subtract the filler and retake cuts, then trim remaining pauses of 0.2 s or more.
- **Mouth check:** `<face python> -I <skill>/scripts/retouch/mouth.py <video> <face_landmarker.task>`. If the speaker's mouth isn't moving, they aren't saying anything. It measures the inner-lip gap per frame (landmarks 13 and 14, divided by face height so zooms don't change it) and lists stretches over 0.4 s where the mouth stays closed or still. Cut those even if there's sound there, but compare each flag with the transcript first: glossy lips can make the gap read nearly closed during normal speech. Stretches with no face detected (a product covering it, looking away) aren't counted, so check those against the transcripts. Spot-check flagged frames so a short pause mid-sentence isn't cut too tight.
- **Check the cuts:** after the edit, transcribe the finished video and compare it with the original transcript. A word that changed at a cut point means the cut clipped it, so widen that cut and render again. A trim pass can also treat the dip inside a word as a pause; protect such words in the plan.
- Show the user the list of what was cut if any choice was a judgment call.

## Rule 4: Split multi-video recordings

If one recording contains several videos, split them into separate files, named by topic. Each gets its own finished export.

## Rule 5: Make it look like them

Use only the brand the video is for, from `my-setup.md`. Never mix brands: no business logo on a personal video, and no personal handle on a business video.

Check in this order:

1. A branding skill or brand files for that brand: use those colors, fonts and voice.
2. The brand's section in `my-setup.md`.
3. If that brand's colors, font or caption style aren't saved yet, ask **once** (two colors, a font, logos, caption look, end card), then save them so you never ask again.
4. If the brand's `Zooms:` line is empty, ask **once**: "Between shots, should I keep the picture still (straight cuts), or add small punch-in zooms (about 8%) every other shot for energy? I'll skip any zoom that would cut off your head." Save the answer in `Zooms:`. If they choose zooms, follow the zoom check in Rule 10.
5. If the brand's `Look:` lines are empty, ask **once**, after transcription so you have their footage. These are hard to judge from words, so show before/after frames from their own video, side by side, each labeled:
   - **Color:** natural (no grade), or a gentle boost (`eq=contrast=1.06:saturation=1.15:gamma=1.02`) for footage that looks dull indoors. Skip this for Log footage, which gets only its LUT (Rule 6).
   - **Skin softening:** never, only when asked, or on every video. Show it on a face close-up at the default level.
   - **Teeth whitening:** never, or only when asked.
   - **Background blur:** never, only when asked, or on every video. Show the default `gblur=sigma=7`.

   Ask in one message, for example: "Here's how your video looks with each option. For [brand], which should I use by default? (1) Color: natural or boosted. (2) Skin softening: never, on every video, or only when you ask. (3) Teeth whitening: never or only when you ask. (4) Background blur: never, on every video, or only when you ask." Save the answers in the brand's `Look:` lines. Defaults set to "every video" are applied without asking again; "only when asked" waits for the user. If they want more or less of something, adjust one step at a time and save the new level.

   Show frames on a small sample (a few seconds, or single frames) rather than rendering the whole video. Building masks for the full video is slow, so don't run it before they've chosen.

**Brand sheet:** the first time you edit for a brand, check its `Brand sheet:` line in `my-setup.md`. If it's empty or says "not asked yet", ask the user **once**, alongside the Rule 1 questions: "Do you want a brand sheet for this brand? It's one page showing your fonts, colors and caption styles, handy to share with anyone who makes graphics for you." Then write the answer in that brand's section, so you never ask again:
- Yes: ask "What should I base it on?" and let the user pick one or more of these:
  1. **An account to learn from** (Instagram, TikTok, YouTube): study its last 4 or 5 videos frame by frame. Download them with `yt-dlp` into `<work folder>/brand-sheets/<brand>/study/`, for private study only, and measure the fonts (matched by eye, so say it's a close match), title and caption sizes, outlines and placement, colors sampled from the footage, shot length, words per minute, pauses, loudness, and how each video opens, uses cutaways and ends. Borrow only the format, type and pacing. Never reuse that creator's lines, titles or footage, and put a "Keep it yours" section on the sheet that says so. Offer to delete the downloaded videos once the sheet is done.
  2. **A Canva brand kit:** if a Canva connector is available, read the kit with it (list the brand kits, then the kit's colors, fonts and logos). If Canva isn't connected or the kit can't be read, ask the user to export it or send a screenshot. Use the exact hex codes and font names from the kit. If a font isn't free to install, say so and suggest the closest free one.
  3. **The brand's website:** the user gives the link. Read the page and its stylesheets for the main colors, fonts and logo, and its text for the tone of voice. Show the user what you found before using it, because a site can mix several looks. Download the logo only if the user confirms it's theirs to use.
  4. **Only what's saved:** use the settings already in that brand's section.

  When more than one source is chosen, the brand's own sources (Canva kit, website, saved settings) decide the colors, fonts and logos. An account study only supplies format and pacing. If two sources disagree, ask the user which to keep. Save any new colors, fonts or logos to the brand's section too, so the skill and the sheet match.

  Make the sheet a single `index.html` page in `<work folder>/brand-sheets/<brand>/`, with no outside links, so it opens offline. Show the fonts (rendered in the font itself), colors (swatches with hex codes and what each is for), the title, caption and handle or logo styles drawn the way they appear on video, the end card, pacing, and a "Your edit settings" section (speed, loudness, color grade, retouch, blur, zooms, emojis, ending), plus a sample frame from the first video and a "last updated" date. Say on the sheet where each part came from. Mark anything no source covers (for example a title style) "not set yet" and ask about it once. Open the sheet in the browser for the user to check. Write `Brand sheet: <path>` and the sources used in the brand's section.
- No: write `Brand sheet: not wanted (<date>)`.

Whenever a brand setting changes in `my-setup.md`, update that brand's sheet in the same turn and change its "last updated" date.

If a folder called `B-roll kit` exists, pull the logo, photos and graphics from it.

When the user wants to borrow the style of creators they admire, borrow the format, type and pacing only. Never reuse another creator's lines, titles or footage.

## Rule 6: Format and quality

- Reels, TikTok and Shorts: vertical 9:16, 1080x1920. YouTube: wide 16:9, 1920x1080, or the source resolution if higher.
- Don't upscale. When reframing wide to vertical, keep the speaker's face in frame.
- **Final export** (what the viewer sees), always:

```
-c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -ac 2 -c:a aac -b:a 320k -movflags +faststart
```

- **In-between renders** (the clean edit, `retouched.mp4`, test cuts, check renders, anything re-encoded later): use the 8-bit encoder line saved in `my-setup.md`. A hardware encoder is usually several times faster at the same quality. If it fails, use the fallback line there and say so.
- **10-bit sources** (ProRes, Log, HDR; check `pix_fmt` with `ffprobe`, e.g. `yuv422p10le`) must stay 10-bit in in-between renders until they're converted and graded, or gradients band. Use the 10-bit line in `my-setup.md`. ProRes 4K decodes slowly on the CPU (about real time on a laptop) and uses about 6 GB per minute, so check free disk space first.

**Log footage** looks grey and flat until it's converted with the camera maker's LUT (path in `my-setup.md`).

- **Spotting it:** Log files often carry no tag that says "Log". Apple Log from the iPhone (Apple's camera or the Blackmagic Camera app) shows `yuv422p10le`, `bt2020` primaries, `bt2020nc` matrix and `color_transfer=unknown` in `ffprobe -show_entries stream=pix_fmt,color_primaries,color_transfer,color_space`, and a frame looks washed out with low contrast. Don't apply a Log LUT to HDR video (`color_transfer=arib-std-b67` HLG, or `smpte2084` PQ) or normal `bt709` footage: they aren't Log, and the LUT would wreck them. If unsure, show the user a frame with and without the LUT and ask. Once confirmed, save how to recognize that camera's Log files in `my-setup.md`.
- **Convert first, then edit:** Log is usually recorded as huge ProRes files (about 6 GB per minute in 4K) that decode slowly. For Reels, TikTok, Shorts and other social clips, do this without asking: before any other step, convert each Log clip once into a light 10-bit copy with the LUT already applied, and do everything else on that copy (transcription, cuts, masks, retouch, export). Never touch the original. Save the copy in the video's work folder as `<original name>-709.mp4`, using the chain below plus `-map 0:v:0 -map 0:a:0 <10-bit in-between encoder from my-setup.md> -c:a copy -map_metadata 0 -movflags +faststart`.
  - For **YouTube** videos, ask first: "Convert to a light copy first (faster, no visible loss in testing), or edit straight from the original (slower, keeps every bit)?" YouTube is often watched in 4K on big screens, so the user decides there. If they choose the original, apply the LUT chain in the first render of each step instead, and keep in-between renders 10-bit.
  - Tested on 20.7 s of iPhone Apple Log ProRes HQ 4K, with Intel Quick Sync `hevc_qsv -global_quality 10`: conversion took 16.5 s, and the file went from 2.0 GB to 174 MB (12x smaller). Against converting the ProRes directly it measured SSIM 0.987, with no visible difference in a 100% face crop. Higher quality settings didn't measure any better. Other hardware encoders at their saved near-lossless setting should be similar; on the first conversion, compare one face crop against the original and say so if anything is visibly lost.
  - **Hardware decoding:** reading that copy back was 4x faster with hardware decoding (`-hwaccel qsv` before `-i`, 3.4 s against 11.4 s on the CPU). On the first conversion, time reading the copy with the decoder that matches the saved encoder (`-hwaccel cuda` for NVIDIA, `qsv` for Intel, `d3d11va` for AMD on Windows, `videotoolbox` on Mac) against no `-hwaccel`. If it's faster, save it in `my-setup.md` and put it before `-i` in every FFmpeg command that reads the copy.
  - Masks and face tracking also work much better on converted footage.
- **How:** convert to RGB with the file's own matrix first; letting FFmpeg guess gave a slightly blue, cool picture. On Windows, paths break `lut3d`, so copy the `.cube` file into the work folder and use the bare filename. For Apple Log:

```
-vf "scale=in_color_matrix=bt2020:in_range=tv:out_range=pc,format=gbrp16le,lut3d=<lut>.cube:interp=tetrahedral,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p10le,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv,<rest of the chain>"
```

  For other cameras, use the matrix in the file's `color_space` tag and check the LUT maker's notes on which input it expects.
- **No extra grade on Log footage** unless the user asks: the official LUT alone usually gives natural skin, and a saturation boost on top looked worse in testing. The brand's color choice in `my-setup.md` is for normal footage.
- Phones store vertical video as landscape with rotation metadata; FFmpeg rotates on its own (a 3840x2160 file can come out 2160x3840).

Overlay transparent logos in RGB (`format=rgba` on both inputs, then `overlay=x:y:format=rgb`), or a faint box shows around the logo. Then convert to `format=yuv420p` before the `ass` filter, or captions come out washed out.

Keep the source frame rate and do cuts with a re-encode so they land exactly.

Burn captions from an `.ass` file. Run FFmpeg from the folder that holds it and use a relative filename (`-vf ass=captions.ass:fontsdir=fonts`), because Windows paths break that filter. Copy the brand's font files into that `fonts` folder. A wrong font name silently falls back to Arial, so check the `fontselect` lines with `-v verbose`. Keep captions in the middle of the safe area on vertical video so app buttons don't cover them.

## Rule 7: Level each voice separately

If a video mixes voices (an AI voice and the user, an off-camera interviewer), level each one on its own. Use the transcript to mark which time ranges belong to which voice, and run `loudnorm` on each separately (two passes for accuracy), with the brand's loudness target from `my-setup.md` (default `loudnorm=I=-14:TP=-1:LRA=11` for social video). Join them, then verify with `ebur128` that the voices match within about 1 LU. Never cut an off-camera voice's pauses as silence.

## Rule 8: Fix dark or grainy footage, and be honest

Measure brightness with `signalstats` (average `YAVG`). If the footage is too dark or grainy, fix it with `eq` for exposure and `hqdn3d` or `nlmeans` for grain. Then tell the user plainly how much it improved, and tell them if they need to reshoot. Don't call footage fine when it isn't.

Apply the color choice from the brand's `Look:` lines in the clean render. If the user finds normal footage dull, the cause is usually ungraded indoor light, not retouch or blur. Offer a gentle grade (`eq=contrast=1.06:saturation=1.15:gamma=1.02`) in the clean render and show a before/after frame. Stronger saturation (x1.25) turned skin orange-red in testing.

## Rule 9: Retouch skin and teeth when asked

Retouch when the brand's `Look:` lines say "every video", or when the user asks. Color alone can't separate skin from things like cardboard, so use face-tracked masks. Files are in `<skill>/scripts/retouch/`: `mask.py` builds the masks, `retouch.txt` is the FFmpeg filter.

1. Render a clean edit (cuts, Log conversion, grade, zooms; no title, captions or handle) as `clean.mp4`, with the in-between encoder. The filter runs underneath the text so the text stays sharp.
2. From that folder, build `skin.mkv` and `teeth.mkv`:

```
<face python> -I <skill>/scripts/retouch/mask.py "<face_landmarker.task>"
```

3. Copy `retouch.txt` into the folder, set the levels from `my-setup.md`, and apply it, setting `-frames:v` to the frame count of `clean.mp4`:

```
ffmpeg -i clean.mp4 -i skin.mkv -i teeth.mkv -/filter_complex retouch.txt -map "[v]" -frames:v <count> <8-bit in-between encoder> retouched.mp4
```

4. Add the title, captions, handle and end card to `retouched.mp4`, then do the final export.

**Skin tones:** the skin mask finds skin by its red level (`SKIN_CR_MIN` at the top of `mask.py`), tuned on one person's light-to-medium skin. On the first retouch for a new person, look at a frame of `skin.mkv` next to the video. If parts of the face are missing, lower `SKIN_CR_MIN`; if hair or background is included, raise it. Save the value in `my-setup.md`. Do the same for `LIPS_CR_MIN`, which decides when the lips count as visible for teeth whitening.

Default levels are in `my-setup.md`. If the user asks for more or less, change one step at a time and save it. To change only the skin strength without rebuilding masks, scale the skin mask in the filter: `format=gray,lut=y='min(val*1.13,255)'`.

The mask protects the eyes, brows, lips and mouth, and only whitens teeth while the lips are visible, so objects passing the mouth aren't touched. Compare close-ups before and after, including a frame where teeth show. Say so if braces or shadows limit the result. Report how many frames had no face detected.

**Small faces:** in full-body framing the face tracker can miss most frames. Run detection on a 2x enlarged crop around the head, track it from frame to frame, and map the points back.

### Animated emojis

Add these when the user asks; don't ask them to supply emoji files.

- **Source:** Remotion with `<skill>/scripts/remotion/EmojiPop.tsx`. It renders one short 43-frame clip per emoji in full color, with the emoji and position passed in `--props`. FFmpeg's `ass` filter doesn't show color emoji reliably, so don't use captions for these. Use Noto Color Emoji (free to reuse) or the system emoji font; don't use Apple's emoji, which can't be reused freely. Twemoji requires credit.
- **Placing:** FFmpeg places each clip with `setpts=PTS-STARTPTS+<frame>/(<fps>*TB)` and `overlay=...:eof_action=pass`. That's much faster than one transparent overlay as long as the whole video.
- **Timing:** read the caption times from the `.ass` file and match each emoji to the word it illustrates. Start it a few frames after that caption appears, and end it with the caption or before the next emoji.
- **Look:** 150 px, a spring pop, a small wobble, a soft shadow. Keep it off the face and away from captions, logos and text. Pick a clear spot for each video, away from where the speaker moves: spots near head height can touch the hair when the speaker leans.
- **Layer order:** footage, retouch, title, product tags, emojis, then captions and handle, and finally the end card.
- **Choosing:** match literal words in the speech. Offer to pick them if the user only asks for "emojis". Use them only occasionally unless asked for more, and say which ones you'd remove first if it feels busy.
- **Check:** look at one frame per emoji to confirm full color and that nothing important is covered.

### Sound effects

Add these when the user asks; don't ask them to supply sounds.

- **Source:** `<skill>/scripts/sfx/`: `pop.wav`, `whoosh.wav`, `sparkle.wav`, `cash.wav`. They were generated with FFmpeg and are free to use. Don't download music or effects unless the user asks and the license allows it.
- **Where:** `pop` on each emoji and handle pop, `whoosh` just before a zoom or end card (start about 0.15 s early so it peaks on the cut), `sparkle` on the title and handle, `cash` on money moments.
- **Mix:** copy `sfx-mix-example.txt` and change the `adelay` times (milliseconds), the number of `asplit` outputs, the `amix` input count, and `whole_dur`. Volumes of about 0.36 to 0.54 sit under the voice; 0.20 to 0.30 was too quiet in testing. Finish with `alimiter=limit=0.89:level=false`.

```
ffmpeg -i voice-final.wav -i pop.wav -i whoosh.wav -i sparkle.wav -i cash.wav -/filter_complex sfx-mix.txt -map "[a]" -ar 48000 -c:a pcm_s16le voice-sfx.wav
```

- **Build order:** level the voice first, mix in the effects, then mux with `-c:v copy`.
- **New sounds** with `aevalsrc`: use `gt(t,0.08)` instead of `t>0.08`, which FFmpeg rejects.
- **Check:** confirm loudness with `ebur128` and transcribe the opening with `medium`, with and without effects. Speech must stay the same. You can't hear the mix, so ask the user to listen and say if the effects are too loud or quiet.

### Background blur

Add this when the brand's `Look:` lines say "every video", or when the user asks. A blur forgives small mask mistakes, so it's much faster and safer than replacing the background. If the user wants a background changed, offer this first: replacing it took about 45 minutes on one video, and the cutout failed whenever a held object moved or came close to the camera.

Files in `<skill>/scripts/retouch/`: `blurmask.py` (builds the mask) and `background-blur.txt` (the start of the FFmpeg filter; set the sigma from `my-setup.md`).

1. Test first. Pass frame numbers to get `bg/blurtest.png`, including frames where the speaker or an object moves:

```
<face python> -I <skill>/scripts/retouch/blurmask.py "<face_landmarker.task>" 30 75 100 150
```

2. Run with no frame numbers to build `bgmask.mkv`.
3. Add the mask as an extra input and put the filter lines before the title, emoji and caption steps, so text stays sharp.

- **Keep sharp:** the mask uses face tracking for the head and neck, and colors for held objects, clothing and skin. Edit `color_keys()` for each video, after sampling the object and clothing in Lab and HSV on a frame; guessed values fail.
- **Don't keep only the largest shape:** the head and a held object can be separate. Remove only small specks.
- **Hands holding products:** use `blurmask_hands.py` instead. It adds hand tracking and keeps a generous area around each hand sharp, so anything held stays sharp whatever its color. Set the clothing color in its `color_keys()`. It runs at half resolution, about 0.17 s per frame on a laptop CPU. With `write` it builds the mask and the test sheet in one pass, so don't run a separate test over a long video:

```
<face python> -I <skill>/scripts/retouch/blurmask_hands.py clean.mp4 bgmask.mkv "<face_landmarker.task>" "<hand_landmarker.task>" write 900 2300 3500
```

- **Hair:** if the top of the hair blurs when the speaker looks down, enlarge and raise the head area (about 1.4 x 1.6 of the face oval, raised by 45 px, worked in close framing). Keeping everything below about half the frame height sharp helps when products held at the edge have no tracked hand.
- **Brand props** that should stay sharp (a shopping bag, a product display): `keepsharp.py` removes blur from a fixed polygon in an existing mask and follows punch-in zooms. Check a zoomed shot, because the prop shifts there.
- **Check:** look at frames from every shot. Ask the user to check for flicker at hair and object edges while they watch.

## Rule 10: Check for these problems on every edit

- **Endings:** don't cut to the end card right after the last word; it feels harsh. Hold on the speaker about 0.5 s after the last word, then fade the picture into the end card's background color over the last 8 frames (`fade=t=out:...:color=<end card color>` before the captions), and fade the voice out over the last 0.25 s.
- **Zooms only where there's room:** if the brand alternates full-frame shots with punch-ins (for example 1.00 and 1.08), check every shot with the face landmarks before choosing zooms. In close framing a punch-in can cut off the top of the head. Estimate the top of the head as the forehead landmark (10) minus 0.45 of the face height, to allow for hair. After the zoom's crop it must stay at least 60 px below the top of the frame, and the chin must stay above the caption area. If a shot fails, keep it at 1.00. If most shots fail (a close-up recording), use no zooms in that video, only straight cuts, and tell the user. Check a frame from each zoomed shot before the export.
- **Mirrored video:** front-camera clips can be flipped. If logos or text read backwards, use `hflip`.
- **Rotation:** check `ffprobe` rotation data before calling a clip horizontal.
- **Audio sample rate:** read it with `ffprobe` before cutting by sample number; it may not be 48 kHz. Tell the user if it's low, because the voice may sound dull.
- **Whisper can miss words:** a sentence may start later than its timestamps show. The re-check on the finished video (Rule 3) finds this, and `silencedetect` or a waveform shows the exact cut point.
- **Muxing:** don't use `-shortest` when joining finished video and audio of the same length; it can drop the last frames. Check that `nb_frames` matches the expected count.
- **Titles and captions:** keep the title off the speaker's face. When the face fills the top of the frame, put the title on the clothing below the captions, and emojis in the background beside the head.
- **Reordering and removing lines:** a judgment call, so show it in the storyboard for approval first.
- **Reels over 3 minutes:** Reels allow up to 3:00 including the end card; TikTok allows longer. Offer two versions: the full one for TikTok and a trimmed one for Reels, with the trims listed in the storyboard. Do the slow work (clean render, retouch, blur) once on the full cut, then cut the other versions from that footage by output frame ranges, so masks never need rebuilding. Captions, emojis, sound and the end card are built per version.
- **Changes after export that only remove lines:** don't rebuild masks or retouch. Add the cuts to the plan, map each kept source frame to its index in the finished retouched footage, trim that footage, then rebuild the voice, captions, emoji times and sound effects. Drop captions whose words fell inside a removed stretch, put back any kept word dropped by mistake, and remove an emoji and its sound if its line was cut. To fix a clipped word after masks are built, splice the missing frames in instead of rebuilding everything.

## Rule 11: Finish like this

Before reporting, check the export with `ffprobe` (resolution, duration, audio present) and look at a few extracted frames, including one with captions.

Then make a ready-to-post pack for each finished video. Save it as a UTF-8 `.txt` next to the export, named `<video-name>-post.txt`, with sections for the caption, hashtags, video file, cover file and before-you-post notes. Never overwrite an existing file. In the chat, give the file's path instead of repeating the text. The pack includes:

- **Caption:** in the video's language and the brand's voice (Rule 5), 1 to 3 short lines. Open with the hook, end with the action from Rule 1, question 3. Use only facts from the video, and don't reuse another creator's lines. Add contact details if the brand's end card has them.
- **Hashtags:** the most popular hashtags for the brand's niche and this video's topic, looked up fresh for every video. Popularity changes from month to month, so don't pick them from memory.
  - **Look them up:** search the web for the hashtags currently most used and most viewed for the niche and topic, on each platform the video is going to, in the video's language (and the audience's country, if the brand has one). Use recent sources, from the last few months, and check at least two. Popular tags differ by platform, so give each platform in the pack its own list.
  - **Pick:** lead with the most popular tags that truly fit the video, then add 1 or 2 specific ones (the product category, the exact topic), so the video can also stand out in a smaller feed. Never add a popular tag that doesn't match the video: platforms treat that as spam. Skip tags that sources report as banned or restricted.
  - **How many:** follow each platform's current rule or recommendation found in the search; if none is found, use 3 to 5.
  - **Save:** keep the niche and its core tags, with the date checked, in the brand's `Niche and hashtags:` line in `my-setup.md`. If the line is empty, ask the user once what their niche is (for example "skincare for over-40s in Spain"), and save it.
  - **Without web access:** use the saved core tags, and write "not checked online this time" next to the hashtags in the pack, and in the chat.
  - Don't state post counts or view numbers unless a source gave them; then add the source and date in the pack's notes.
- **Cover:** pick a sharp frame with the title readable and the speaker's eyes open, and save it as `<video-name>-cover.png`. Never overwrite an existing file. For Reels and TikTok, check the main text sits in the center so it survives the profile crop. If the brand's `Cover:` line says with products, or the user asks, build it as in Cover with products below.
- **Reminder:** the user can add a trending sound in the app, and should keep it quiet under the voice. Point out anything the video promises, like a follow-up video.

### Cover with products

A cover with the speaker, the title and pictures of the products shown in the video, made with the `CoverCard` template. Show only the pictures: no product names or prices on the cover, since those belong in the video (product tags). Add them only if the user asks for that video.

1. **Pick the products:** the main ones named in the transcript, 1 to 4. For more, ask which to show.
2. **Get a picture of each,** in the order the brand's `Product photos:` line gives, or this order if it's empty:
   - **The user's own photos:** a `B-roll kit` folder, or the brand's own website if the products are the user's.
   - **Shop or brand websites the user names** (for example Cult Beauty or Sephora): search that site for the exact product, with its shade and size, open the product page and download the main product image at its largest size. Compare it with a frame from the video to check it's the same product and shade; if it isn't, don't use it. Write the page address in the pack's notes. If the site blocks the download, ask the user to save the image into `<work folder>/product-photos/`, named after the product.
   - **A frame from the video:** the sharpest frame where the product is held still and facing the camera, cut out with `--crop` around it.
   The first time the user names a shop website, tell them once, in plain words: product photos on shop websites usually belong to the brand or the shop, so using them on a cover is common but not risk-free; the brand's press kit or the shop's affiliate program images come with permission. Save their answer in `Product photos:` and don't ask again.
3. **Cut each out:** `<cutout python> -I <skill>/scripts/cover/cutout.py <image> <work folder>/cover/<product>.png`, with `--white` for shop photos on a plain white background (fast, crisp edges), and without it for video frames or colored backgrounds. White or clear packaging can vanish with `--white` and turn see-through without it: run both and keep the better one. If the script warns about the share kept, the cutout failed: try the other mode or a tighter crop. Put all the cutouts on one contact sheet over a colored background, and show it to the user before building the cover.
4. **Build it:** copy the background frame (picked as for the plain cover) and the cutouts into the Remotion project's `public/cover/` folder, write the props to `cover.json`, and render with `npx remotion still src/index.ts CoverCard out/cover.png --props=cover.json`. Use the brand's colors and font, and `numbered` for ranking and "3 things" videos. Leave out `label` and `price`. Set `titleTop` and `productsTop` so the title stays off the face and the products sit over the body or the background, never over the face.
5. **Check:** look at the cover. Every product recognizable, and the title and products inside the middle 3:4 of a vertical cover (y 240 to 1680 on 1080x1920), which is what Instagram's profile grid shows. Save it as `<video-name>-cover.png` and the plain frame as `<video-name>-cover-plain.png`, never overwriting existing files, and list the image sources in the pack's notes.

Never post for the user. Tell them where the file is saved, and remind them to watch it once before they post. They're the director.
