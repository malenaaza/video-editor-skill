# Video Editor for Creators: a Claude Code plugin for talking-head videos



https://github.com/user-attachments/assets/0807e097-5f38-4115-aff4-7b10c7e8928d

<img width="1080" height="960" alt="cover-before-after" src="https://github.com/user-attachments/assets/63d6c838-5fdb-4293-abb4-8a602d206b84" />




A plugin for [Claude Code](https://claude.com/claude-code) that edits short-form and YouTube talking-head videos on your own computer with FFmpeg and Whisper. You stay the director: it asks before it decides anything that's a judgment call.

## What it does

- Removes retakes, pauses, fillers ("um", "uh", hums) and silent stretches, using word-level transcription, a filler-hunting second pass, and a mouth-movement check
- Speeds up delivery slightly (optional) while keeping your pitch
- Captions (plain, or with each word lit up as you say it), titles, handle, end card and logos in your brand's colors and fonts, saved once and reused
- Vertical (Reels, TikTok, Shorts) and wide (YouTube) exports, splitting long recordings into several videos
- Background noise and hum removal, voice polish and leveling, sound effects, animated emojis, titles and product tags (via Remotion), dark-footage fixes
- Face-tracked skin softening (face and neck, stronger on close-ups), an optional light beautify (soft glow, brighter under-eyes and eye whites, never makeup or reshaping) and teeth whitening, background blur that keeps held products sharp, a part in black and white, a slow push in on your face at a key line
- Log footage (Apple Log, S-Log and others) converted with the camera maker's official LUT
- A ready-to-post pack for each video: caption, hashtags and cover frame, or a cover with pictures of your products

You don't need to remember this list: ask the skill "what can you do?" for a menu, and before each edit it suggests the extras that fit that video.

## Adjusts to your computer

On first use it runs `scripts/detect_setup.py`, which checks your CPU and GPU and **test-encodes video with every hardware encoder your FFmpeg has**: NVIDIA (NVENC), Intel (Quick Sync), AMD (AMF) and Apple (VideoToolbox). It recommends the fastest one that actually works, and checks whether Whisper can use an NVIDIA GPU. Then it asks you the few things it can't detect: your cameras, whether you shoot Log, your languages, your brands and where finished videos go. Everything is saved to `~/.video-editor/my-setup.md`, so it never asks twice.

Working renders use the hardware encoder for speed. The final export always uses `libx264` at high quality, so the result looks the same on any computer.

## Install

The skill is a Claude Code plugin. In Claude Code, type these two commands (or paste them in a terminal with `claude` in front, without the slash):

```
/plugin marketplace add malenaaza/video-editor-skill
```

```
/plugin install video-editor@malenaaza
```

Restart Claude Code, then ask for an edit ("edit this video for Reels: ..."). The first time, it checks your computer and asks a few setup questions.

**Already installed it the old way** (a `video-editor` folder copied into `~/.claude/skills/`)? Say "update my video-editor skill" (or *actualiza mi skill*). Claude brings that copy up to date and then moves you to the plugin: it installs the plugin, makes a backup of the old folder and removes it, so Claude doesn't find the skill twice. Your settings in `~/.video-editor/` stay as they are.

It runs on your computer, so it's meant for Claude Code (the terminal, IDE extensions, or the Code tab in the Claude desktop app). In a regular Claude.ai chat it can't reach your files or your installed tools.

### Updating

Plugin updates come through Claude Code's plugin system. Type `/plugin`, open **Marketplaces**, choose **malenaaza**, and update, or turn on **auto-update** there once so new versions arrive by themselves. Then start a new Claude Code session. If you allow it (it asks once), Claude also checks once a week and tells you in one line when there is a new version; it only contacts GitHub and sends nothing about you.

- **Your settings are safe.** They live in `~/.video-editor/my-setup.md`, outside the skill, and an update never touches them. Each video's own settings (`retouch.json`) are in that video's folder.
- **Please don't edit the skill's own files.** Preferences go in your settings, and Claude saves them there when you ask for a change ("less blur", "always put my logo here").
- **Want your own version of the skill?** Make a copy of the repository on GitHub (a "fork") and add your copy as the marketplace instead.
- **Without the plugin system:** you can still copy the folder `plugins/video-editor/skills/video-editor` into `~/.claude/skills/` and say "update my video-editor skill" to update it. A developer's clone linked there is updated with `git pull`.

### What it installs on first use

On first use it walks you through installing what's missing:

- FFmpeg 7+ and yt-dlp
- Python 3.10–3.12 with `openai-whisper` and `faster-whisper`
- For retouch, blur and the mouth check: `mediapipe` and `opencv-python`, plus Google's MediaPipe face and hand models
- Optional: Node 20+ for Remotion graphics, rembg for product cutouts on covers, and an RNNoise model (or DeepFilterNet's `deep-filter`) for noise removal
- If you shoot Log: your camera maker's official LUT, which you download yourself



## What's tested

It was developed and used on Windows 11 with an Intel laptop (Intel Arc graphics, Quick Sync), on Spanish and English videos. The NVIDIA, AMD and Apple encoder settings, CUDA transcription, and macOS / Linux commands are included but haven't been tested on real hardware yet. Every encoder is test-encoded before it's used, so a setting that doesn't work on your machine is never picked. Reports and fixes are welcome.

The skin mask's colour thresholds were tuned on light-to-medium skin. The skill tells Claude to check the mask and adjust them on the first retouch for each person (see `skin_cr_min` in `scripts/retouch/settings.py`). Values for one video go in a `retouch.json` in that video's folder, so the scripts themselves are never edited.

## Files

```
.claude-plugin/marketplace.json   makes this repository a plugin marketplace (malenaaza)
plugins/video-editor/
  .claude-plugin/plugin.json      the plugin: name, version, description
  skills/video-editor/
    SKILL.md               the instructions Claude follows on every edit
    references/            details Claude reads only when a video needs them: setup, fillers,
                           Log footage, sound, retouch and blur, graphics, covers, brand sheet
    project-template.md    becomes project.md in each video's folder, so an edit can continue later
    support.json           where reports go: the GitHub page and, if set, an email address
    setup-template.md      becomes ~/.video-editor/my-setup.md on first use (your hardware, brands, choices)
    scripts/
      detect_setup.py      hardware, tools and encoder tests (standard library only)
      transcribe.py        faster-whisper with word times, CPU or NVIDIA GPU
      cutplan.py           builds the cut plan: pauses and listed cuts, snapped to whole frames
      captions.py          writes the captions for the cut, in the brand's style
      drops.py             second pass: removes fillers, held sounds and pauses from a finished cut
      heldsounds.py        finds held sounds ("deeee") that a filler pass misses
      asr.py, hear.py      one interface for both Whisper engines; transcribes short pieces alone
      report.py            turns a problem or idea into a report for the author (GitHub link or email)
      broll.py             indexes your B-roll and finds the right photo or clip for each product you name
      popplace.py          places the product pop-in beside your temple, never over what you hold
      balance.py           measures a colour cast (white balance) and gives the filter that removes it
      mono.py              turns a part of the video black and white, fading back to colour
      pushin.py            a slow, smooth push in on your face at a key line, keeping your head in the frame
      reframe.py           turns a wide video into a vertical one for Shorts, following you like a camera operator
      chapters.py          YouTube chapters for the description, checked against YouTube's rules
      screen.py            screen recordings: smooth zooms onto the action, and screen-above-speaker Shorts
      editreport.py        the edit in numbers: what was cut, pauses left, loudness, size
      update_skill.py      updates the skill safely, with a backup
      fillers.py, filler_prompts.py, findfill.py, checkcuts.py   filler hunting and cut checks
      hunt_fillers.py      short-window pass for fillers glued onto words
      retouch/             skin and teeth masks, beautify extras, background blur, mouth check;
                           settings.py reads each video's retouch.json
      sfx/                 four small sound effects, generated with FFmpeg, and typing.py (key clicks
                           for a typewriter title)
      remotion/EmojiPop.tsx  animated emoji pop for Remotion
      remotion/TitleCard.tsx  animated hook title for Remotion
      remotion/ProductTag.tsx product name and price lower third for Remotion
      remotion/ProductPop.tsx the product's photo or clip popping in beside you when you name it
      remotion/WordCaptions.tsx captions with each word lit up in your accent colour as you say it
      remotion/CoverCard.tsx  cover image with products around the speaker's face
      remotion/Thumbnail.tsx  YouTube thumbnail: your face big on one side, a few huge words on the other
      remotion/brandFont.ts   loads the brand font for the templates
      cover/cutout.py      cuts products out of shop photos or video frames
      cover/face_box.py    finds the face so the products go around it
      voice/clean_voice.py measures background noise, removes it and polishes the voice
      voice/leveljoin.py   joins clips and levels them to a loudness target, for quiet voices with clicks
```

`my-setup.md` holds your personal details. It's saved in `~/.video-editor/`, outside the skill folder, so it isn't in any copy of the skill you share.

## Found a bug, or have an idea?

Tell Claude, in your own words: "the skin looks bad at 3:32", "I wish it could add music". It keeps a note on your computer, and offers to send it to the author. If you say yes, it writes a short report (with no names, personal folders, frames or videos), shows it to you, and gives you a link that opens it on GitHub, already filled in: you just click Submit (you need a free GitHub account). If an email address is set, you can send it by email instead.

Fixes and new ideas reach you when you update: "Update my video-editor skill" (or "Actualiza mi skill").

## Tests and changes

`tests/test_skill.py` runs the cut plan, captions and filter files on a small generated clip (it needs Python, FFmpeg and numpy; the colour key test also needs OpenCV). GitHub runs it on every push. `CHANGELOG.md` lists what each update brings.

```bash
python tests/test_skill.py
```

## Licenses

The skill, scripts and sound effects are under the MIT License (see `LICENSE`). Tools it uses have their own licenses: FFmpeg (LGPL/GPL), OpenAI Whisper (MIT), faster-whisper (MIT), MediaPipe and its models (Apache 2.0), yt-dlp (Unlicense). Remotion is free for individuals and companies of up to 3 people; larger companies need a paid license. Camera LUTs belong to their makers and aren't included.

Only edit and download videos you own or have the right to use.
