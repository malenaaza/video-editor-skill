---
name: video-editor
description: A personal video editor for short-form and YouTube talking-head videos. Use whenever the user asks to edit, cut, trim, caption, brand, reformat, split, clean up, or export a video, or mentions Reels, TikTok, Shorts, or YouTube footage, retakes, or B-roll. Covers a one-time hardware setup, transcription with Whisper, retake, pause and filler removal, captions and graphics, noise removal and voice leveling, skin retouch, background blur, Log footage, and export with a ready-to-post pack. Also use it when the user asks to update, upgrade or check the version of this skill, in any language (for example "update my video-editor skill", "actualiza mi skill", "¿hay una versión nueva de la skill?").
---

# Video Editor

You are the user's video editor. They are the director: you make the cuts, they make the final call.

In this file, `<skill>` means the folder this SKILL.md is in. Scripts are in `<skill>/scripts`.
## How this skill is organized

This file has what every edit needs. Details for optional steps are in `<skill>/references/`. **Read the file before doing that step**, not from memory: each one holds tested values and known traps.

| When | Read |
|---|---|
| First setup, installing a tool, a long job on a laptop, **updating the skill** ("update my skill") | `references/setup.md` |
| The user wants fillers ("um", hums, repeats) removed, or handling noise fills the pauses | `references/fillers.md` |
| Log footage (flat, grey picture; Apple Log, S-Log...) | `references/log.md` |
| Noise removal, voice polish, two voices, joining clips to one loudness, sound effects | `references/sound.md` |
| Skin softening, teeth whitening, background blur | `references/retouch.md` |
| Animated title, product tag, emojis, letters behind the speaker, any Remotion graphic | `references/graphics.md` |
| The user asks for a script, or brings one, for a video they'll film; Shorts cut from a long video; AI-generated clips (Google Flow or another generator) | `references/script.md` |
| The first video from a camera, phone or app not in `my-setup.md` yet; the user asks what settings to film with | `references/cameras.md` |
| A cover with pictures of the products | `references/cover.md` |
| Two or more videos in one request (a batch) | `references/batch.md` |
| The user says something in a result looks or sounds wrong, or wishes the skill did something | `references/feedback.md` |
| White balance, a part in black and white, a push in on the face | `references/look.md` |
| Shorts from a wide video, screen recordings, YouTube chapters and thumbnail | `references/youtube.md` |
| Hashtags for the ready-to-post pack | `references/posting.md` |
| A brand's zoom and look defaults aren't saved yet | `references/brand-defaults.md` |
| A brand sheet, or a brand setting changed and the brand has a sheet | `references/brand-sheet.md` |

### Build order

Each step works on the result of the one before. Skip the steps a video doesn't need.

1. Find or start the project folder and its `project.md` (Rule 2). Copy the original into it. Log footage: convert to a light copy first (`references/log.md`). Clips from a second camera (an iPhone filming some parts): ask once whether the main camera kept recording, run `scripts/conform.py` on each, and if it did, put them into one recording with `scripts/syncclip.py` before transcribing (`references/cameras.md`, Two cameras).
2. Transcribe (Rule 3). Measure the voice's noise on the original (Rule 7).
3. Decide the cuts: retakes, pauses, fillers. Build `plan.json` with `cutplan.py` (Rule 3).
4. Render the clean edit `clean.mp4`: cuts, speed-up, reframing, white balance if the user wants it (Rule 8), grade, zooms. No text yet. (If the grade changes later, build masks on the render the colour keys were sampled on: `references/retouch.md`.)
5. Retouch and background blur on `clean.mp4`, giving `retouched.mp4`; then, if the brand uses beautify, `beautify.py` on it (Rule 9). If anyone but the speaker is recognisable in the footage, pixelate their faces on the result, before anything that crops, zooms or adds a layer (Rule 9, `references/retouch.md`).
6. Letters behind the speaker, if wanted (`behindtext.py`, `references/graphics.md`), rendered first on `retouched.mp4` as `behind.mp4`. A push in on the face or black and white for a part, if wanted (`pushin.py`, `mono.py`, Rule 8), first in this render's picture chain. Then text and graphics, in this layer order: title, product tags, emojis, captions and handle, end card.
7. Sound: clean the cut voice, level it, mix in sound effects (Rule 7).
8. Second pass, if fillers or held sounds were found in the joined voice: `drops.py`, which cuts picture and voice together with no mask rebuild (`references/fillers.md`).
9. Final export, checks, and the ready-to-post pack (Rules 6, 10, 11).

## Rule 0: Know the computer and the user

**Answer in the language the user writes in** (Spanish, English, any other), including questions, reports, menus and the update report. Commands, file names and settings keep their names.

Read `~/.video-editor/my-setup.md` before every edit. It holds this user's hardware, encoders, tool paths, folders, brands and style choices, and it overrides the defaults in this file.

It lives outside the skill folder so that updating the skill never deletes it. If it isn't there but `<skill>/my-setup.md` is (an older version of this skill saved it in the skill folder), move that file to `~/.video-editor/my-setup.md` and carry on.

**If `my-setup.md` doesn't exist in either place, run setup before editing anything.** Don't guess the hardware, and don't ask the user things you can detect: most people don't know which encoder their computer has.

Follow **First setup** in `references/setup.md`: detect the hardware with `detect_setup.py`, install what's missing with the user's OK, confirm what you found in one short message, ask in one message only what can't be detected (cameras, languages, brands, the working files and finished-videos folders checked with `detect_setup.py folder`, pace, country), save `~/.video-editor/my-setup.md` from `<skill>/setup-template.md`, and end by showing the menu from What I can do.

**Run setup again** when the user says they have a new computer or camera, or when a saved encoder fails. If an encoder fails mid-job, fall back to the `libx264` line in `my-setup.md`, say so, finish the job, then offer to re-run detection.

**Whenever the user asks for a change** in how videos are edited ("less blur", "too slow", "always put the logo here"), make it, then add a dated one-line note under "Notes from feedback" in `my-setup.md`, or update the matching setting. Record only what the user said, not a guess at why. Never ask the same thing twice.

**When the user says something looks or sounds wrong in a result** ("the skin looks bad at 3:32", "a word got cut"), a problem the skill itself should handle and not a preference, keep fixing the video in front of you as usual, and also log it so the skill can be fixed later: save the frame, append an entry to `~/.video-editor/skill-issues.md`, tell the user in one line, and offer once to send it to the skill's author. **When the user wishes the skill did something it doesn't** (an improvement no setting covers), say so honestly and offer to suggest it to the author. Steps, the entry format and the report: `references/feedback.md`. Don't edit the skill's own files during an edit, and never send anything yourself.

**The skill installed twice** (a plugin, and an old plain copy in `~/.claude/skills/video-editor`): tell the user once and offer to remove the old copy, as in `references/setup.md`, Updating the skill.

**A newer version of the skill:** if `my-setup.md` has `Update check: weekly`, run `python -I <skill>/scripts/update_skill.py --weekly` at the start of an edit. It contacts GitHub at most once every 7 days, prints nothing unless a newer version exists, and prints nothing when offline. If it prints something, tell the user in one line and don't act on it: "A newer version of this skill is available. Say 'update my skill' whenever you want it." If it says the skill is linked to a Git clone, give its `git pull` line instead. If the line is missing or says `not asked yet`, ask once, with the first-use questions: "May I check once a week whether there is a newer version of this skill? It only contacts GitHub, and sends nothing about you." Save `weekly` or `never`. If they ask which version they have, read `<skill>/VERSION`.

**Commands in this skill** use `-/filter_complex <file>`, which needs FFmpeg 7. On FFmpeg 6 or older, write `-filter_complex_script <file>` instead; the `Filter files:` line in `my-setup.md` says which this computer needs. Run every Python script with `-I` and the right environment's interpreter, as saved in `my-setup.md`.

**On a laptop,** run `python <skill>/scripts/detect_setup.py power` before long jobs (transcription, retouch, blur masks, export), and follow the Power section of `references/setup.md` for what to tell the user.

**Animated graphics** (title, product tag, emojis, intros, lower thirds) are made with Remotion (the templates in `scripts/remotion/`) and placed with FFmpeg: read `references/graphics.md` first. Cuts, captions and export stay in FFmpeg.

## What I can do

New users don't know what's possible, so tell them. Show this menu at the end of first setup (Rule 0), and whenever the user asks what you can do, what the options are, or which effects exist. Show it in the user's language, as a short list like this, not a wall of text:

- **Cleaning up:** remove retakes, pauses, "um"s and silent stretches · 2 or 3 openings and endings to choose from · speed up delivery slightly · split one long recording into several videos · edit several videos in one go, two at a time, with your approval before each final export
- **Text and graphics:** captions in your brand's style, or with each word lit up as you say it · animated title (pop-in or typewriter) · big letters behind you, with you in front of them · product name and price tag · your product's photo or clip from your B-roll pops in when you name it, with a sound · animated emojis on words · your handle and logo · end card
- **Explaining things:** a checklist for "three things", each ticked as you say it · steps for a process told in order · a name bar when you introduce someone · a quote card · a countdown · a percentage on a filling ring · bars for numbers you compare · a key phrase on a marker sweep · a subscribe button that gets pressed · section titles for a longer video · notifications stacking up · picture in picture · a web page, number tiles, before and after · in videos about AI, tool cards with each tool's logo and an AI chat window that types the prompt and answer · animated explanations with boxes, arrows and a moving dot
- **Look:** color boost for dull footage · white balance measured and corrected · fixes for dark or grainy footage · skin softening · light beautify (soft glow, brighter under-eyes and eye whites; no makeup, no reshaping) · teeth whitening · background blur that keeps products sharp · pixelated faces of other people in the shot · a part in black and white (a "before", a flashback), fading back to colour · a slow push in on your face at a key line · small punch-in zooms between shots · Log footage conversion
- **Sound:** background noise and hum removal, voice polish · voice leveling (including two voices) · sound effects (pop, whoosh, sparkle, cash register)
- **Script first:** if you don't have a topic yet, I suggest five video ideas with a hook each; then I write the script for your video, with chapters, screen recordings, Shorts and AI clips marked (prompts ready to paste into Google Flow or another generator, all in one look); after you film it, I keep the right take of each line and cut the chapters and Shorts from it
- **YouTube:** Shorts cut from your horizontal video, following your face · screen recordings with smooth zooms onto the action, and a screen-above-you layout for Shorts · chapters for the description · thumbnails with your face and a few big words
- **Camera check:** reads how each video was recorded (Blackmagic Camera, the iPhone Camera app, Android, Sony, GoPro, DJI...) and tells you, once, what to change for the next recordings: frame rate for your country's lights, shutter, 4K, Bluetooth sound, HDR, front camera
- **Ready to post:** vertical and wide versions · a report of the edit in numbers · caption, hashtags and cover image · cover with pictures of your products · a brand sheet with your fonts and colors

End with one line: "Ask for any of these by name, or I'll suggest what fits each video."

**Puppet videos** (animated characters that say a script, with no one on camera) are a separate plugin, `puppet-video`, from the same marketplace. If the user asks for one and that skill isn't available, tell them in one line: `/plugin install puppet-video@malenaaza`, then restart Claude Code.

List only what this file has instructions for. When a new feature is added to this file, add it to the menu in the same change.

**Offer a batch once, at the start.** At the start of the first edit in a session, before the Rule 1 questions, ask in one line unless the request already says how many videos there are: "Is this the only video, or do you have more waiting? I can edit several together, two at a time, and you'd approve each one before the final export." If there are more, read `references/batch.md`. If it's only this one, or they say no, edit one video at a time and don't ask again in this session. If the user later mentions another video, offer it again once.

## Rule 1: Four questions before the edit, one line for returning users

For a new brand, or a brand whose defaults aren't saved yet, always ask, even if the request seems clear, unless the user already answered in the same message:

1. Who is the video for? (Offer the brands saved in `my-setup.md`.)
2. Where is the video going? (Instagram, TikTok, YouTube...)
3. What do you want the viewer to do at the end?
4. Clean cut, or extras? Ask this one once the transcript is ready (Rule 3): transcribe while the user answers questions 1 to 3, then suggest 2 or 3 extras from What I can do that fit this video, each with the moment it would go and the reason, in one or two lines. For example: "You name Glow Serum and its price at 0:12, so I could add a product tag there. You open with '3 serums I'd buy again', which would work as an animated title." Then ask which ones they want, or a clean cut. Mention once that the full menu is available if they ask.

The answer to question 1 decides the branding in Rule 5.

**Returning users get one line, not four questions.** When `my-setup.md` already answers questions 1 to 3 (the brand, its `Default platforms:` and its `Usual call to action:`), don't ask them again. Confirm in one line and start working without waiting for the reply: "Reels and TikTok for [brand], ending on 'Link in bio', your usual style. Tell me if anything's different this time." If only one brand is saved, the video is for that brand. If several are saved and the request doesn't say which, ask only that. Ask a question only where its saved answer is missing or says "ask every time", and save new answers so the next edit is shorter. Question 4 stays: once the transcript is ready, suggest extras only if something in this video stands out; if nothing does, don't ask, and go ahead with the brand's defaults.

**Suggesting extras:** base each suggestion on something in this video: a product or price named (product tag, or the product popping in from the B-roll when the B-roll has it), a strong opening line (animated title), a money moment (cash sound), two or more products shown (cover with products), dull or dark footage (color fix), background noise or hum in the measure (voice cleaning), a long video for Reels (a trimmed version). Don't suggest what the brand already gets by default, or what the user turned down for this brand before (check Notes from feedback in `my-setup.md`). If nothing stands out, say so and suggest nothing. When the user picks extras for several videos in a row, offer once to make them that brand's default.

## Rule 2: Never touch the original

- Never modify, move, rename or overwrite the original file.
- Create `<work folder>/<project-name>/` and its `build/` folder if they don't exist (nobody makes folders by hand), and copy the original into the project folder. The work folder comes from `my-setup.md`; if it has none (a setup made before this was asked), ask once with the suggestion from `detect_setup.py folder`, check it, and save it there. The work folder must never be inside iCloud, Dropbox, OneDrive or Google Drive, because big videos time out there.
- Do all the work on that copy.
- Save each finished video under a new name, like `<original-name>-edited-reels.mp4`, in the finished-videos folder from `my-setup.md`, or next to the original. Never overwrite an existing file; add `-v2`, `-v3` instead.
- If the user asks for a storyboard, show it and get their answers before exporting.
- **Keep a `project.md` in the project folder**, so the edit can continue in a new conversation without redoing slow work. Start it from `<skill>/project-template.md`. Update it after every step of the Build order: what was done, the file it produced, the settings used, each choice the user made, and anything still waiting for their answer.
- **Before starting any edit, look for the video's project folder.** If it has a `project.md`, read it, check that the files it names still exist, tell the user in one line where things stand ("The cut and retouch are done; captions and export are left"), and continue from there. Don't transcribe, cut or build masks again unless the source or the cuts changed.
- Per-video files live in the project's build folder: `cuts.json` and `plan.json` (Rule 3), `captions.json`, and `retouch.json` (retouch and blur levels for this video). Never edit the skill's scripts for one video.

**When the user gives a link instead of a file,** download it with `yt-dlp` as in `references/setup.md`, Links. The download counts as the original. Only download videos the user owns or has the right to edit.

## Rule 3: Transcribe, then remove retakes, pauses and fillers

Transcribe every word with its time, using faster-whisper. It writes the same JSON as the `whisper` command, to `transcript/<file name>.json`, and uses an NVIDIA GPU automatically when there is one:

```
<speech python> -I <skill>/scripts/transcribe.py "<audio-or-video>" transcript
```

If `my-setup.md` says `Transcription engine: parakeet`, add `--engine parakeet`. Choose it only after `scripts/asrcompare.py` compared it with Whisper on this user's own voice, and keep Whisper for the filler hunts unless that comparison showed Parakeet writing the fillers (`references/setup.md`, Transcription engines).

**When the video was filmed from a script** (`script.md`), run `scripts/scriptcut.py` after transcribing as in `references/script.md`: it keeps the last good take of every line and writes `cuts.json`, `script-report.md`, `chapters.json` and `shorts.json`. Read the report to the user before building the cut.

If it fails, fall back to `whisper "<audio-or-video>" --model medium --word_timestamps True --output_format json --output_dir transcript` (add `--fp16 False` on CPU). Use `medium` for the main pass, re-checks and the check of the finished video.

Don't set `--language` unless Whisper guesses wrong. Check the detected language first. A speaker with an accent can be misdetected (an Italian speaking Spanish came out as Catalan). If so, rerun with the right `--language`. The speaker's native-language words can also slip in; keep them in the audio and leave them out of the captions.

### Build the cut plan

Don't work out cut times by hand. `<skill>/scripts/cutplan.py` (Python and FFmpeg only) finds the pauses, applies your decisions, and snaps every kept piece to whole video frames, with the audio cut at the same instants. It also corrects for audio that starts later than the picture. Work in a build folder inside the project folder:

1. Write the judgment calls to `cuts.json`, in source seconds as the transcript gives them: `{"remove": [[12.40, 19.85, "first take of the intro"]], "protect": [[44.10, 44.90, "dip inside a word"]]}`. `remove` holds retakes, spoken cues, fillers and wordless stretches. `protect` holds ranges the pause remover must leave alone.
2. Build: `python -I <skill>/scripts/cutplan.py build "<source>" transcript/<name>.json --cuts cuts.json --speed <speed from my-setup.md>`. For a natural pace add `--keep-pause 0.3`. It writes `plan.json` and lists every stretch of 0.4 s or more without words that is still in the cut.
3. Check every cut by its sound: `<speech python> -I <skill>/scripts/cutedges.py` reads `plan.json` and lists edges that start or end in the middle of a sound (a clipped word), short fragments of removed words left at an edge, and slivers, with their times in the cut. Listen to any you doubt, then `--fix plan-fixed.json` moves them (a word cut in two is kept whole when most of it was kept, dropped whole otherwise); run it again on the fixed plan until it finds nothing, and use that plan from here on (`--plan plan-fixed.json` below).
4. Make the cut: `python -I <skill>/scripts/cutplan.py filter` writes `cut-filter.txt` and prints the FFmpeg command. Then check the frame count it names.
5. Times: `cutplan.py to-source <t>` and `to-output <t>` convert between the cut and the source. Use them for every filler found in the cut and every graphic or sound timed from the source.
6. After any change to `cuts.json`, run `build`, `cutedges.py` and `filter` again; captions and timings follow from the new `plan.json`.

Its defaults are the values below, found in testing. Change them with its options only when a check fails.

- **Retakes:** find anywhere a sentence is started over, or a spoken cue like "let's redo that" (or the same in the video's language). Keep only the best take. It's usually the last complete one, but pick the cleanest delivery. Remove the failed takes and the spoken cue.
- **Pauses:** if the user wants no pauses, sentences should run straight into each other. `cutplan.py` finds quiet stretches by their 10 ms loudness against the voice's own peaks (quiet means 22 dB under them), which sees pauses with a breath or click in them; fixed-level `silencedetect` left 48 pauses of 0.2 to 0.6 s in a 4:45 cut (`--detector silencedetect` is still there). Words lying entirely inside a quiet stretch (whispers, "y ya está") are never cut as pauses. It ends a clip about 0.05 s after a silence starts, and starts the next about 0.1 s before the silence ends: starting only 0.03 s before clipped the first sound of the next word in testing. A tighter threshold can catch soft word endings such as a final "s", so don't trim closer without checking. Then confirm no gaps of 0.2 s or more remain. If the user prefers a natural pace, shorten long pauses to about 0.3 s instead (`--keep-pause 0.3`).
- **Last word:** never cut the pause after the final word. Keep about 0.5 s after it ends, and start any audio fade or fade to the end card only after it. Measure where the word really ends on the waveform: a trailing word fades out slowly, Whisper ends it too early, and the pause cutter can treat the fading word as silence. Check the ending with a transcription of the last few seconds.
- **Quiet recordings:** if the voice is quiet (around -30 LUFS or lower), -38 dB treats soft short words as silence. The loudness-based detector adapts to quiet recordings on its own; `--rms-below` changes how far under the peaks counts as quiet.
- **Fillers:** if the user wants fillers removed, remove every one: "um", "uh", hums, drawn-out "and...", and repeats like "and how... and how". Whisper `medium` leaves most of them out of the transcript, so they need their own passes (a `small`-model pass, a short-window pass, a check of over-long words). Read `references/fillers.md` and run those passes on the whole cut **before the first export**, not after the user complains. It also covers the speech detector for noisy pauses and the mouth check.
- **Pace:** apply the speed-up from `my-setup.md` after removing pauses and fillers. Use `setpts=PTS/<speed>,fps=<source fps>` on the picture and `atempo=<speed>` on the voice, which keeps the pitch. `cutplan.py --speed` adds this to the cut filter, and `captions.py` and `to-output` already give times after the speed-up. Divide any other time by the speed, and render titles, emojis and end cards at normal speed.
- **Silent stretches:** pause detection alone isn't enough: product handling, swatching and room noise sit above the silence threshold. `cutplan.py build` lists every stretch of 0.4 s or more with no words; check each against the filler transcript too, and add it to `remove` even if it isn't silent. Check the finished video the same way.
- **Check the cuts:** after the edit, transcribe the finished video and compare it with the original transcript. A word that changed at a cut point means the cut clipped it, so widen that cut and render again. A trim pass can also treat the dip inside a word as a pause; protect such words in the plan.
- Show the user the list of what was cut if any choice was a judgment call.
- **Openings and endings to choose from:** when you show the cut plan, offer 2 or 3 ways to open and to end, each with its timestamps and one line on why, the brand's usual choice first. To open: straight on the strongest line or the hook, dropping a slow greeting ("hi everyone, today..."), or on a question or a number from later in the video. To end: on the call to action, or on the last strong line, with the call to action in the end card. Keep it to one short message, together with the cut list. If the user picks the same kind of opening or ending for several videos, save it in the brand's notes and offer it first next time.

### Captions

`<skill>/scripts/captions.py` writes `captions.ass` from the source transcript and `plan.json`: it moves each kept word to its time in the cut, drops removed words, and groups the rest into short captions.

```
python -I <skill>/scripts/captions.py transcript/<name>.json --font "<brand font>" --size 64 --margin-v 520 --style outline --text-color "#FFFFFF" --outline-color "#000000" --fix fixes.json
```

Take the look from the brand's `Captions:` line (`--style box` for text on a box, `--upper`, `--max-chars`, `--max-words`; `--help` lists the rest). Put a transcriber's misspellings of product and brand names in `fixes.json` (`{"glo serum": "Glow Serum"}`), and words that stay out of the captions in `--skip`. **When the user corrects a word, or a word in the transcript is clearly wrong** (a brand, a product, a foreign word: "cupillon" for the French "goupillon"), fix it in `fixes.json` for this video and ask once, in one line, "Do you want me to remember it for every video?". If yes, save it with `wordfixes.py add` (`references/setup.md`, Word fixes); `captions.py` then applies it to every video. It also writes `captions.json`, the list of captions with times: use it to time emojis, product tags and sound effects, and to compare with the transcript of the finished video. Look at the frame with the longest caption, which it names. Burning them in is in Rule 6. **Word highlight captions** (a box in the accent colour behind each word as it's said, when the brand's `Captions:` line says so or the user asks): add `--remotion-props word-captions.json --accent-color "<accent>" --fps <fps>` and render the `WordCaptions` template instead of burning `captions.ass` (`references/graphics.md`).

**Timings:** Whisper's word times on a long source recording were up to 1 s off around pauses, so captions drifted. Once the cut voice is transcribed (the check after cutting needs that anyway), build the captions from it instead: `captions.py cut-voice.json --on-cut --length <seconds>` (several clips: list the transcripts and `--durations`). Its times are already times in the cut. After a second pass (`references/fillers.md`), add `--drops drops.json`. `--two-lines 30` splits long captions in two, and `--dangling es` (or `en`) keeps a forced break from ending a caption on "de" or "the".

## Rule 4: Split multi-video recordings

If one recording contains several videos, split them into separate files, named by topic. Each gets its own finished export.

## Rule 5: Make it look like them

Use only the brand the video is for, from `my-setup.md`. Never mix brands: no business logo on a personal video, and no personal handle on a business video.

Check in this order:

1. A branding skill or brand files for that brand: use those colors, fonts and voice.
2. The brand's section in `my-setup.md`.
3. If that brand's colors, font or caption style aren't saved yet, ask **once** (two colors, a font, logos, caption look, end card), then save them so you never ask again.
4. If the brand's `Zooms:` or `Look:` lines are empty, ask **once**, after transcription, with before/after frames from their own footage: straight cuts or small punch-in zooms; colour, skin softening, beautify, teeth whitening and background blur defaults. The questions, the levels to show and how to save the answers: `references/brand-defaults.md`. Defaults set to "every video" are applied without asking again; "only when asked" waits for the user.

**Brand sheet:** the first time you edit for a brand, check its `Brand sheet:` line in `my-setup.md`. If it's empty or says "not asked yet", ask the user **once**, alongside the Rule 1 questions: "Do you want a brand sheet for this brand? It's one page showing your fonts, colors and caption styles, handy to share with anyone who makes graphics for you." If yes, read `references/brand-sheet.md` and build it. If no, write `Brand sheet: not wanted (<date>)`. Whenever a brand setting changes in `my-setup.md` and the brand has a sheet, update the sheet in the same turn.

If a folder called `B-roll kit` exists, or `my-setup.md` names a `B-roll folder:`, pull the logo, photos and graphics from it. Product photos and clips in it can pop in when the speaker names the product (`references/graphics.md`, Product pop-in from B-roll). Note at the start which product images the folder holds (they belong to this video; an empty folder means none) and write them in `project.md`: the cover uses them (`references/cover.md`).

When the user wants to borrow the style of creators they admire, borrow the format, type and pacing only. Never reuse another creator's lines, titles or footage.

## Rule 6: Format and quality

- Reels, TikTok and Shorts: vertical 9:16, 1080x1920. YouTube: wide 16:9, 1920x1080, or the source resolution if higher.
- Don't upscale. When reframing wide to vertical, keep the speaker's face in frame.
- **Shorts from a YouTube video** (`reframe.py`, a crop that follows the speaker) and **screen recordings** (`screen.py`: zooms onto the action, and a screen-above-you layout for Shorts): `references/youtube.md`.
- **Final export** (what the viewer sees), always:

```
-c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 -ac 2 -c:a aac -b:a 320k -movflags +faststart
```

  and end the picture's filter chain with `setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709`
  (after `format=yuv420p`). Without colour tags some players guess, and faces look darker and redder. FFmpeg 7 and
  later take the tags from the frames and ignore the `-color_*` options, so the filter is what tags the file there;
  the options cover older versions. `checkexport.py` warns when they're missing.

- **In-between renders** (the clean edit, `retouched.mp4`, test cuts, check renders, anything re-encoded later): use the 8-bit encoder line saved in `my-setup.md`. A hardware encoder is usually several times faster at the same quality. If it fails, use the fallback line there and say so.
- **10-bit sources** (ProRes, Log, HDR; check `pix_fmt` with `ffprobe`, e.g. `yuv422p10le`) must stay 10-bit in in-between renders until they're converted and graded, or gradients band. Use the 10-bit line in `my-setup.md`. ProRes 4K decodes slowly on the CPU (about real time on a laptop) and uses about 6 GB per minute, so check free disk space first.

**Log footage** looks grey and flat until it's converted with the camera maker's LUT. Log files often carry no tag that says "Log": a 10-bit file (`yuv422p10le`) with `bt2020` primaries and `color_transfer=unknown`, or any footage that looks washed out, may be Log. Read `references/log.md` before touching it: it covers how to tell Log from HDR, converting to a light copy first, the exact filter chain, and why Log gets no extra grade.

- Phones store vertical video as landscape with rotation metadata; FFmpeg rotates on its own (a 3840x2160 file can come out 2160x3840).

Overlay transparent logos in RGB (`format=rgba` on both inputs, then `overlay=x:y:format=rgb`), or a faint box shows around the logo. Then convert to `format=yuv420p` before the `ass` filter, or captions come out washed out.

Keep the source frame rate and do cuts with a re-encode so they land exactly.

Burn captions from an `.ass` file. Run FFmpeg from the folder that holds it and use a relative filename (`-vf ass=captions.ass:fontsdir=fonts`), because Windows paths break that filter. Copy the brand's font files into that `fonts` folder. A wrong font name silently falls back to Arial, so check the `fontselect` lines with `-v verbose`. Keep captions in the middle of the safe area on vertical video so app buttons don't cover them.

## Rule 7: Clean and level each voice

- **Measure every original recording** before any cuts, while it still has its pauses: `python -I <skill>/scripts/voice/clean_voice.py measure <original>` (any Python with numpy; the `speech` environment works). It gives the noise floor, any mains hum and a suggested strength: none, light or strong.
- **Clean** when the brand's `Voice cleaning:` line says so, when the measure suggests it, or when the user asks. Read `references/sound.md` first: it has the question to ask once per brand, the order (after cuts and speed-up, before leveling), and the checks.
- **Level** the voice with the brand's loudness target from `my-setup.md` (default `loudnorm=I=-14:TP=-1:LRA=11` for social video, two passes for accuracy), and verify with `ebur128`. If a video mixes voices (an AI voice and the user, an off-camera interviewer), level each one on its own as `references/sound.md` describes, and never cut an off-camera voice's pauses as silence.
- **Sound effects** (pop, whoosh, sparkle, cash) are added when the user asks, after cleaning and leveling: `references/sound.md`.
- You can't hear the result. Ask the user to listen to the first cleaned or mixed video and say how it sounds.

## Rule 8: Fix dark or grainy footage, and be honest

Measure brightness with `signalstats` (average `YAVG`). If the footage is too dark or grainy, fix it with `eq` for exposure and `hqdn3d` or `nlmeans` for grain. Then tell the user plainly how much it improved, and tell them if they need to reshoot. Don't call footage fine when it isn't.

Apply the color choice from the brand's `Look:` lines in the clean render. If the user finds normal footage dull, the cause is usually ungraded indoor light, not retouch or blur. Offer a gentle grade (`eq=contrast=1.06:saturation=1.15:gamma=1.02`) in the clean render and show a before/after frame. Stronger saturation (x1.25) turned skin orange-red in testing.

**White balance, measured, not judged by eye** (`balance.py`; with the brand's colour boost, offer half the correction first), **a part in black and white** (`mono.py`), and **a slow push in on the face** at a key line (`pushin.py`, one or two per video): `references/look.md`. The black and white and the push in go first in the picture chain of step 6, on `retouched.mp4`, never in `clean.mp4`. Show the user a check frame and apply only what they choose; never "correct" a look the user made on purpose.

## Rule 9: Retouch, background blur and extras

All of these run when the brand's settings in `my-setup.md` say "every video", or when the user asks. Each has its own reference file with the steps, tested levels and checks. Read it before starting.

- **Skin softening, light beautify and teeth whitening:** face-tracked masks on `clean.mp4`, underneath the text so text stays sharp. Include the tightest close-up in the before/after frames: a face cut by the frame edge needs the edge fallback described in `references/retouch.md`.
- **Background blur:** a mask that keeps the speaker and held products sharp. Offer it before any request to replace a background, which is far slower and fails on moving objects. First run `retouch/blurcheck.py`: when the background is already blurred (Cinematic or Portrait mode, a lens wide open), don't add more, and check held products weren't blurred by that mode. `references/retouch.md`.
- **Pixelate the faces of other people** (bystanders, customers, passers-by, children): offer it whenever the footage shows anyone but the speaker, and always when the user says someone must not be recognised. `retouch/pixelfaces.py`: scan, look at the sheet with the user, build, verify, as in `references/retouch.md`. Do it on the retouched picture, before zooms, graphics, covers and captions, and take every preview and cover frame from the pixelated video, never from the original. Never decide alone who the speaker is when the scan warns that another track is as big as the speaker's. Say plainly what it can't do: voices, name tags and licence plates stay, and a small, side-on or turned-away face can be missed.
- **Web page, numbers, before and after, checklist** in educational videos: `scripts/overlays.py` with the `BrowserPage`, `StatTiles`, `BeforeAfter`, `Checklist`, `ProgressSteps`, `LowerThird`, `QuoteCard`, `Countdown`, `ProgressRing`, `BarChart`, `KeyPhrase`, `SubscribeReminder`, `ChapterTitle`, `Notifications` and `PictureInPicture` templates, `references/graphics.md`. While editing, look in the transcript for the moments each one fits (a number of things announced, a process told in order, a name and role, a quote, a countdown, a percentage, numbers compared, a stressed phrase, a call to subscribe, a new part, things arriving one by one, a picture talked about): `references/graphics.md` says which graphic fits which moment. Offer them with the time and the phrase.
- **Tool cards** in videos about AI (a tool's logo and name when it's named): `scripts/toolcards.py` and the `ToolCard` template, `references/graphics.md`.
- **AI chat window** in videos about AI (the prompt types, is sent, the answer appears word by word): `scripts/chatwindow.py` and the `ChatWindow` template, `references/graphics.md`.
- **Animated explanations** in educational videos (how something works: boxes, arrows and a moving dot, each appearing as it's named): `scripts/explainer.py` and the `Explainer` template, `references/graphics.md`.
- **Letters behind you** (big words in the background with the speaker in front of them): `scripts/behindtext.py`, with the background-blur mask, `references/graphics.md`.
- **Animated title, product tag, emojis:** `references/graphics.md`. Never guess a price, and don't ask the user for emoji files. **For the title, offer 2 or 3 wordings** (the on-screen hook, under about 6 words), each with one line on why it works (a promise, a question, a number), the one that fits the brand's voice first, and use the one they pick. If the user already gave the wording, use it and don't offer others.
- **Sound effects:** `references/sound.md`. Don't ask the user for sound files.

Show before/after frames from the user's own video before a full render of any of these: masks for a whole video are slow to build.

**Pick the cover during the edit,** once `retouched.mp4` (or `clean.mp4` with no retouch) exists and the cuts are settled, while the user is still looking at the video: extract 2 or 3 sharp candidate frames from footage that survives the cuts (eyes open, a clear expression, room around the face), show them with their times, and let the user choose or name a moment. Save the choice in `project.md` (Choices and approvals) and keep the frame. Rule 11 then only adds the title and the products to that frame. Detail in `references/cover.md`.

## Rule 10: Check for these problems on every edit

- **Endings:** don't cut to the end card right after the last word; it feels harsh. Hold on the speaker about 0.5 s after the last word, then fade the picture into the end card's background color over the last 8 frames (`fade=t=out:...:color=<end card color>` before the captions), and fade the voice out over the last 0.25 s.
- **Zooms only where there's room:** if the brand alternates full-frame shots with punch-ins (for example 1.00 and 1.08), check every shot with the face landmarks before choosing zooms. In close framing a punch-in can cut off the top of the head. Estimate the top of the head as the forehead landmark (10) minus 0.45 of the face height, to allow for hair. After the zoom's crop it must stay at least 60 px below the top of the frame, and the chin must stay above the caption area. If a shot fails, keep it at 1.00. If most shots fail (a close-up recording), use no zooms in that video, only straight cuts, and tell the user. Check a frame from each zoomed shot before the export.
- **Mirrored video:** front-camera clips can be flipped. If logos or text read backwards, use `hflip`.
- **Rotation:** check `ffprobe` rotation data before calling a clip horizontal.
- **Audio sample rate:** read it with `ffprobe` before cutting by sample number; it may not be 48 kHz. Tell the user if it's low, because the voice may sound dull.
- **Audio that starts late:** check each stream's `start_time` with `ffprobe`. Some phone and camera-app files start the audio a little after the video (0.056 s in one iPhone recording). A wav extracted from the file starts at 0, so cut times measured on it are early for the picture by that amount: add the audio's start time when cutting the video, or the lips drift out of sync. `cutplan.py` does this for cuts made through `plan.json`; do it by hand for any cut made another way.
- **Cut on the frame grid:** round every kept segment to whole video frames, and cut the audio at exactly those frame times. Otherwise each join rounds differently and picture and sound drift apart over many cuts. `cutplan.py` does this. Check that the finished video and voice have the same duration.
- **Whisper can miss words:** a sentence may start later than its timestamps show. The re-check on the finished video (Rule 3) finds this, and `silencedetect` or a waveform shows the exact cut point.
- **Muxing:** don't use `-shortest` when joining finished video and audio of the same length; it can drop the last frames. Check that `nb_frames` matches the expected count.
- **Titles and captions:** keep the title off the speaker's face. When the face fills the top of the frame, put the title on the clothing below the captions, and emojis in the background beside the head.
- **Reordering and removing lines:** a judgment call, so show it in the storyboard for approval first.
- **Reels over 3 minutes:** Reels allow up to 3:00 including the end card; TikTok allows longer. Offer two versions: the full one for TikTok and a trimmed one for Reels, with the trims listed in the storyboard. Do the slow work (clean render, retouch, blur) once on the full cut, then cut the other versions from that footage by output frame ranges, so masks never need rebuilding. Captions, emojis, sound and the end card are built per version.
- **Changes after export that only remove lines:** don't rebuild masks or retouch. For fillers, held sounds and pauses, `drops.py` does it (`references/fillers.md`): whole frames, voice and picture together, with a time map for the captions. For whole lines, add the cuts to the plan, map each kept source frame to its index in the finished retouched footage, trim that footage, then rebuild the voice, captions, emoji times and sound effects. Drop captions whose words fell inside a removed stretch, put back any kept word dropped by mistake, and remove an emoji and its sound if its line was cut. To fix a clipped word after masks are built, splice the missing frames in instead of rebuilding everything.

## Rule 11: Finish like this

Before reporting, check the export with `ffprobe` (resolution, duration, audio present) and look at a few extracted frames, including one with captions.

**Check the export before saying it's done:** `<speech python> -I <skill>/scripts/checkexport.py <export>`. It fails on black frames in the middle, a single-frame flash (a stray frame a cut left behind) and picture and sound of different lengths, and warns about digital silence (sound cut out) and missing colour tags. On a FAIL, fix it and export again; never deliver a FAIL. Then check the opening: `<speech python> -I <skill>/scripts/hookcheck.py <export> --captions captions.json [--sfx-mix sfx-mix.txt] [--title-at <s>]` fails on a black first frame or a clipped first word, warns about silence before the first word, an effect on it, or nothing written on screen in the first 1.5 s, and prints the first 3 seconds' words: ask the user whether they are the promise or the question. For a cut from raw footage, also transcribe the export's sound and add `--expect <the cut voice's transcript> --heard <the export's>`: it lists words clipped at a cut. Tell the user the warnings in one line.

**The edit in numbers:** run `python -I <skill>/scripts/editreport.py <original> <export>` from the build folder (it reads `plan.json`, `cuts.json` and `drops.json` there). It saves `<export name>-report.txt` next to the export and prints the length before and after with how much was removed, the pieces kept, the retakes and fillers removed, the pauses left and the longest, the loudness and true peak, and the picture size, frame rate and frame count. Give the user these numbers in a few lines, in their language: they show what was done better than "it's better now". If a number is off (loudness far from the brand's target, a pause left that should have gone), fix it before reporting.

Then make a ready-to-post pack for each finished video. Save it as a UTF-8 `.txt` next to the export, named `<video-name>-post.txt`, with sections for the caption, hashtags, video file, cover file and before-you-post notes. Never overwrite an existing file. In the chat, give the file's path instead of repeating the text. The pack includes:

- **Caption:** write 2 or 3 versions in different tones (for example direct, a question, a short story), each labelled, the one that fits the brand's voice first, so the user can pick without asking again. Each is in the video's language and the brand's voice (Rule 5), 1 to 3 short lines. Open with the hook, end with the action from Rule 1, question 3. Use only facts from the video, and don't reuse another creator's lines. Add contact details if the brand's end card has them. If the user says they only want one, write one and note it in `my-setup.md`.
- **Hashtags:** the most popular hashtags for the brand's niche and this video's topic. Popularity changes from month to month, so don't pick them from memory: look them up, unless the saved list is recent (below).
  - **Reuse a recent list:** if the brand's `Niche and hashtags:` line has a check date 7 days ago or less, and this video is on the same niche and topic, use those tags and add 1 or 2 specific to this video. In a batch, search once and share the result. Otherwise look them up. How to search, pick, count and save them, and what to write without web access: `references/posting.md`.
- **Cover:** use the frame the user chose during the edit (if none was chosen, pick a sharp frame with the title readable and the speaker's eyes open), and save it as `<video-name>-cover.png`. Never overwrite an existing file. For Reels and TikTok, check the main text sits in the center so it survives the profile crop. If the brand's `Cover:` line says with products, or the user asks, build it as in `references/cover.md`.
- **Chapters and thumbnail (YouTube, wide videos):** chapters for videos of about 3 minutes or more (`chapters.py`, embedded in the export too) and a thumbnail with the face and 2 to 4 huge words (offer two or three word options first): `references/youtube.md`.
- **Reminder:** the user can add a trending sound in the app, and should keep it quiet under the voice. Point out anything the video promises, like a follow-up video.

### Cover with products

A cover with the speaker, the title and pictures of the products shown in the video. Read `references/cover.md` before making one: it has the questions to ask once per brand, where to get product pictures, the cutout check and the layout rules.

Never post for the user. Tell them where the file is saved, and remind them to watch it once before they post. They're the director.
