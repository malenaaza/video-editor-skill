# video-editor: a Claude skill for talking-head videos

A skill for [Claude Code](https://claude.com/claude-code) that edits short-form and YouTube talking-head videos on your own computer with FFmpeg and Whisper. You stay the director: it asks before it decides anything that's a judgment call.

## What it does

- Removes retakes, pauses, fillers ("um", "uh", hums) and silent stretches, using word-level transcription, a filler-hunting second pass, and a mouth-movement check
- Speeds up delivery slightly (optional) while keeping your pitch
- Captions, titles, handle, end card and logos in your brand's colors and fonts, saved once and reused
- Vertical (Reels, TikTok, Shorts) and wide (YouTube) exports, splitting long recordings into several videos
- Background noise and hum removal, voice polish and leveling, sound effects, animated emojis, titles and product tags (via Remotion), dark-footage fixes
- Face-tracked skin softening (face and neck, stronger on close-ups) and teeth whitening, background blur that keeps held products sharp
- Log footage (Apple Log, S-Log and others) converted with the camera maker's official LUT
- A ready-to-post pack for each video: caption, hashtags and cover frame, or a cover with pictures of your products

You don't need to remember this list: ask the skill "what can you do?" for a menu, and before each edit it suggests the extras that fit that video.

## Adjusts to your computer

On first use it runs `scripts/detect_setup.py`, which checks your CPU and GPU and **test-encodes video with every hardware encoder your FFmpeg has**: NVIDIA (NVENC), Intel (Quick Sync), AMD (AMF) and Apple (VideoToolbox). It recommends the fastest one that actually works, and checks whether Whisper can use an NVIDIA GPU. Then it asks you the few things it can't detect: your cameras, whether you shoot Log, your languages, your brands and where finished videos go. Everything is saved to `~/.video-editor/my-setup.md`, so it never asks twice.

Working renders use the hardware encoder for speed. The final export always uses `libx264` at high quality, so the result looks the same on any computer.

## Install

The skill is the `video-editor` folder in this repository. It goes in your personal skills folder:

- Windows: `C:\Users\<your name>\.claude\skills\`
- macOS / Linux: `~/.claude/skills/`

Pick whichever way is easiest for you.

### Option 1: ask Claude Code to install it (easiest)

In Claude Code, type:

> Install the skill from https://github.com/malenaaza/video-editor-skill into my personal skills folder.

### Option 2: download the ZIP (no tools needed)

1. At the top of this page, click the green **Code** button, then **Download ZIP**.
2. Unzip it. Inside the `video-editor-skill-main` folder there's a folder called `video-editor`.
3. Move that `video-editor` folder into your skills folder (paths above). If the `skills` folder doesn't exist, create it.
   On a Mac, the `.claude` folder is hidden in Finder: press **Cmd + Shift + .** to show hidden folders.

### Option 3: terminal

macOS / Linux:

```bash
git clone https://github.com/malenaaza/video-editor-skill.git
mkdir -p ~/.claude/skills
cp -r video-editor-skill/video-editor ~/.claude/skills/
```

Windows (PowerShell):

```powershell
git clone https://github.com/malenaaza/video-editor-skill.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills"
Copy-Item -Recurse video-editor-skill\video-editor "$HOME\.claude\skills\"
```

### Check it worked

Restart Claude Code, then type `/video-editor` or ask for an edit ("edit this video for Reels: ..."). The first time, it checks your computer and asks a few setup questions.

### Updating

To get a newer version, replace the `video-editor` folder with the new one. Your settings are in `~/.video-editor/my-setup.md`, outside the skill folder, so they survive the update.

If you installed an earlier version, your settings are still in `video-editor/my-setup.md`: copy that file out before replacing the folder, and put it back afterwards. The skill moves it to the new place the next time you edit.

### What it installs on first use

On first use it walks you through installing what's missing:

- FFmpeg 7+ and yt-dlp
- Python 3.10–3.12 with `openai-whisper` and `faster-whisper`
- For retouch, blur and the mouth check: `mediapipe` and `opencv-python`, plus Google's MediaPipe face and hand models
- Optional: Node 20+ for Remotion graphics, rembg for product cutouts on covers, and an RNNoise model (or DeepFilterNet's `deep-filter`) for noise removal
- If you shoot Log: your camera maker's official LUT, which you download yourself

It runs on your computer, so it's meant for Claude Code (the terminal, IDE extensions, or the Code tab in the Claude desktop app). In a regular Claude.ai chat it can't reach your files or your installed tools.

## What's tested

It was developed and used on Windows 11 with an Intel laptop (Intel Arc graphics, Quick Sync), on Spanish and English videos. The NVIDIA, AMD and Apple encoder settings, CUDA transcription, and macOS / Linux commands are included but haven't been tested on real hardware yet. Every encoder is test-encoded before it's used, so a setting that doesn't work on your machine is never picked. Reports and fixes are welcome.

The skin mask's colour thresholds were tuned on light-to-medium skin. The skill tells Claude to check the mask and adjust them on the first retouch for each person (see `SKIN_CR_MIN` in `scripts/retouch/mask.py`).

## Files

```
video-editor/
  SKILL.md               the instructions Claude follows on every edit
  references/            details Claude reads only when a video needs them: setup, fillers,
                         Log footage, sound, retouch and blur, graphics, covers, brand sheet
  setup-template.md      becomes ~/.video-editor/my-setup.md on first use (your hardware, brands, choices)
  scripts/
    detect_setup.py      hardware, tools and encoder tests (standard library only)
    transcribe.py        faster-whisper with word times, CPU or NVIDIA GPU
    cutplan.py           builds the cut plan: pauses and listed cuts, snapped to whole frames
    captions.py          writes the captions for the cut, in the brand's style
    fillers.py, filler_prompts.py, findfill.py, checkcuts.py   filler hunting and cut checks
    hunt_fillers.py      short-window pass for fillers glued onto words
    retouch/             skin and teeth masks, background blur, mouth check
    sfx/                 four small sound effects, generated with FFmpeg
    remotion/EmojiPop.tsx  animated emoji pop for Remotion
    remotion/TitleCard.tsx  animated hook title for Remotion
    remotion/ProductTag.tsx product name and price lower third for Remotion
    remotion/CoverCard.tsx  cover image with products around the speaker's face
    remotion/brandFont.ts   loads the brand font for the templates
    cover/cutout.py      cuts products out of shop photos or video frames
    cover/face_box.py    finds the face so the products go around it
    voice/clean_voice.py measures background noise, removes it and polishes the voice
```

`my-setup.md` holds your personal details. It's saved in `~/.video-editor/`, outside the skill folder, so it isn't in any copy of the skill you share.

## Licenses

The skill, scripts and sound effects are under the MIT License (see `LICENSE`). Tools it uses have their own licenses: FFmpeg (LGPL/GPL), OpenAI Whisper (MIT), faster-whisper (MIT), MediaPipe and its models (Apache 2.0), yt-dlp (Unlicense). Remotion is free for individuals and companies of up to 3 people; larger companies need a paid license. Camera LUTs belong to their makers and aren't included.

Only edit and download videos you own or have the right to use.
