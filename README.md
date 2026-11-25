# Video Editor for Creators: a Claude Code plugin for talking-head videos



https://github.com/user-attachments/assets/aa4c613b-1997-4f54-aed8-40265f171824




<img width="1080" height="960" alt="cover-before-after" src="https://github.com/user-attachments/assets/63d6c838-5fdb-4293-abb4-8a602d206b84" />




A plugin for [Claude Code](https://claude.com/claude-code) that edits short-form and YouTube talking-head videos on your own computer with FFmpeg and Whisper. You stay the director: it asks before it decides anything that's a judgment call.

## What it does

- Removes retakes, pauses, fillers ("um", "uh", hums) and silent stretches, using word-level transcription, a filler-hunting second pass, and a mouth-movement check
- Speeds up delivery slightly (optional) while keeping your pitch
- Captions (plain, or with each word lit up as you say it), titles, handle, end card and logos in your brand's colors and fonts, saved once and reused
- Vertical (Reels, TikTok, Shorts) and wide (YouTube) exports, splitting long recordings into several videos
- Background noise and hum removal, voice polish and leveling, sound effects, animated emojis, titles and product tags (via Remotion), dark-footage fixes
- Big letters behind you (the "text behind subject" effect): a hook word or a title in the background, with you in front of it, fading in as you say it
- Face-tracked skin softening (face and neck, stronger on close-ups), an optional light beautify (soft glow, brighter under-eyes and eye whites, never makeup or reshaping) and teeth whitening, background blur that keeps held products sharp (and isn't added when your camera already blurred the background), a part in black and white, a slow push in on your face at a key line
- Makes its own folders: at first setup it asks where to keep working files (suggesting `~/video-work`), checks that the folder isn't in OneDrive, iCloud, Dropbox or Google Drive (where big videos time out), and creates it and a folder for each video. You never make folders by hand
- Pixelates the faces of other people in the shot (bystanders, customers, children) and keeps yours sharp: it follows every face, shows you a sheet to check, covers moments the detector loses, and checks the result for any face left visible. People who are small or far away (shop staff and customers in the background) need the thorough search; it hides faces only, not voices or name tags
- A second camera for some parts: your main camera films the whole video and your iPhone films a few parts from another angle. Filmed at the same time, it syncs them by their sound and switches to the iPhone's picture for those parts while your voice stays the main camera's; filmed as separate takes, it joins them. Either way it makes the iPhone clips match first (same frame rate, at a steady rate, same size, HDR turned into normal video) and marks in the shot list which parts go on which camera
- Log footage (Apple Log, S-Log and others) converted with the camera maker's official LUT
- A ready-to-post pack for each video: caption, hashtags and cover frame, or a cover with pictures of your products (you choose the cover frame while you edit; product images already cut out are used as they are)
- Checks how each video was recorded (Blackmagic Camera, the iPhone Camera app, Android phones, Sony, GoPro, DJI) and tells you once what to change for better footage: frame rate for your country's lights, shutter, 4K, Bluetooth sound, HDR, front camera
- For YouTube: Shorts cut from your horizontal video that follow you like a camera operator, screen recordings with smooth zooms onto the action (and a screen-above-you layout for Shorts), chapters for the description, and thumbnails with your face and a few big words
- Puppet videos, with no one on camera: one or two illustrated adult characters or a robot (drawn in code, all original, with your brand's colours and the skin tones and hair you choose) say your script with a free voice made on your computer, Spanish from Spain and British English included, with mouths that match every sound, blinking, expressions, captions in the script's exact words, and an optional translation under each line for language students
- For educational videos: a real web page in a browser window that scrolls to what you mention and highlights it, two to four numbers counting up as you say them, and a before and after with a sweep (a weak prompt and a good one)
- Tool cards for videos about AI: when you name a tool, its logo and name slide in, tools named in a row stack, and a tool isn't shown again for a while
- An AI chat window for videos about AI: your prompt types with key clicks, it's sent, the assistant thinks and answers word by word, in your brand's colours, wide or vertical
- Animated explanations for educational videos: boxes, arrows and a moving dot that show how something works (how an MCP connects Claude to your Gmail, how a request travels), each appearing as you name it, in your brand's colours, wide or vertical, with pops and whooshes timed to the picture
- A list of word corrections that's saved once and applied to every video: brand names, products and foreign words that a transcriber always misspells are fixed in your captions (and, with Whisper, given to the transcriber as a hint)
- A choice of transcription engine: Whisper, or NVIDIA Parakeet (several times faster on a computer without a graphics card), with a tool that compares both on your own voice before you switch
- Checks every cut by its sound before rendering (a word clipped in half, a scrap of a removed word, a cut that flashes by) and fixes it, keeping or dropping the word whole
- Checks the opening of every video: a black first frame, a clipped first word, silence before you speak, a sound effect on your first word, nothing to read with the sound off, and what the first 3 seconds say
- Checks every export before it's delivered: black frames, a stray single frame left by a cut, picture and sound that end apart, sound that cuts out, missing colour tags, and words clipped at a cut
- Script first: ask for a script and it writes one with chapters, screen recordings and Shorts marked, and one to three AI clips for atmosphere (a visual metaphor, an intro scene) with prompts ready to paste into Google Flow or another generator, all in the same look and never for text, diagrams or real people; after filming it matches each clip to your camera and places it under your voice, plus a clean text for your teleprompter if you use one (it asks once); after you film it, it keeps the last good take of each line, tells you what you missed, and cuts the chapters and Shorts from it
- Several videos in one request: you answer the questions once for all of them, each video gets its own folder and runs the normal edit (two at a time, so the computer isn't overloaded), and you see every cut plan and draft together and approve each before the final export. One video at a time works exactly as before

You don't need to remember this list: ask the skill "what can you do?" for a menu, and before each edit it suggests the extras that fit that video.

## Adjusts to your computer

On first use it runs `scripts/detect_setup.py`, which checks your CPU and GPU and **test-encodes video with every hardware encoder your FFmpeg has**: NVIDIA (NVENC), Intel (Quick Sync), AMD (AMF) and Apple (VideoToolbox). It recommends the fastest one that actually works, checks whether Whisper can use an NVIDIA GPU, and reads your GPU memory to say whether the computer could generate AI video locally. Then it asks you the few things it can't detect: your cameras, whether you shoot Log, your languages, your brands and where finished videos go. Everything is saved to `~/.video-editor/my-setup.md`, so it never asks twice.

Working renders use the hardware encoder for speed. The final export always uses `libx264` at high quality, so the result looks the same on any computer.

## Install

The skill is a Claude Code plugin. In Claude Code, type these two commands (or paste them in a terminal with `claude` in front, without the slash):

```
/plugin marketplace add malenaaza/video-editor-skill
```

```
/plugin install video-editor@malenaaza
```

The plugin has two skills, and these commands install both: **video-editor** (editing the videos you film) and
**puppet-video** (animated characters that say a script, with no one on camera).

Restart Claude Code, then ask for an edit ("edit this video for Reels: ...") or a puppet video ("make a puppet video
where Lola orders a coffee in English"). The first time, it checks your computer and asks a few setup questions; the
first puppet video also installs its voice and lip-sync tools.

**Already installed it the old way** (a `video-editor` folder copied into `~/.claude/skills/`)? Say "update my video-editor skill" (or *actualiza mi skill*). Claude brings that copy up to date and then moves you to the plugin: it installs the plugin, makes a backup of the old folder and removes it, so Claude doesn't find the skill twice. Your settings in `~/.video-editor/` stay as they are.

It runs on your computer, so it's meant for Claude Code (the terminal, IDE extensions, or the Code tab in the Claude desktop app). In a regular Claude.ai chat it can't reach your files or your installed tools.

### Updating

Plugin updates come through Claude Code's plugin system. Type `/plugin`, open **Marketplaces**, choose **malenaaza**, and update, or turn on **auto-update** there once so new versions arrive by themselves. Then start a new Claude Code session. If you allow it (it asks once), Claude also checks once a week and tells you in one line when there is a new version; it only contacts GitHub and sends nothing about you.

- **Your settings are safe.** They live in `~/.video-editor/my-setup.md`, outside the skill, and an update never touches them. Each video's own settings (`retouch.json`) are in that video's folder.
- **Please don't edit the skill's own files.** Preferences go in your settings, and Claude saves them there when you ask for a change ("less blur", "always put my logo here").
- **Want your own version of the skill?** Make a copy of the repository on GitHub (a "fork") and add your copy as the marketplace instead.
- **Without the plugin system:** you can still copy the folder `plugins/video-editor/skills/video-editor` into `~/.claude/skills/` and say "update my video-editor skill" to update it. For puppet videos, copy `plugins/video-editor/skills/puppet-video` there too, next to it (it uses the video editor's scripts). A developer's clone linked there is updated with `git pull`.

### What it installs on first use

On first use it walks you through installing what's missing:

- FFmpeg 7+ and yt-dlp
- Python 3.10–3.12 with `openai-whisper` and `faster-whisper`
- For retouch, blur and the mouth check: `mediapipe` and `opencv-python`, plus Google's MediaPipe face and hand models
- Optional: Node 20+ for Remotion graphics, rembg for product cutouts on covers, and an RNNoise model (or DeepFilterNet's `deep-filter`) for noise removal
- If you shoot Log: your camera maker's official LUT, which you download yourself
- For puppet videos: Piper (`piper-tts`, the voices) and its voice files, and Rhubarb Lip Sync (the mouth shapes)



## What's tested

It was developed and used on Windows 11 with an Intel laptop (Intel Arc graphics, Quick Sync), on Spanish and English videos. The NVIDIA, AMD and Apple encoder settings, CUDA transcription, and macOS / Linux commands are included but haven't been tested on real hardware yet. Every encoder is test-encoded before it's used, so a setting that doesn't work on your machine is never picked. Reports and fixes are welcome.

The skin mask's colour thresholds were tuned on light-to-medium skin. The skill tells Claude to check the mask and adjust them on the first retouch for each person (see `skin_cr_min` in `scripts/retouch/settings.py`). Values for one video go in a `retouch.json` in that video's folder, so the scripts themselves are never edited.

## Files

```
.claude-plugin/marketplace.json   makes this repository a plugin marketplace (malenaaza)
docs/es/SKILL.es.md                 Spanish (Spain) translation of SKILL.md, to read; Claude follows the English one
plugins/video-editor/
  .claude-plugin/plugin.json      the plugin: name, version, description
  skills/video-editor/
    SKILL.md               the instructions Claude follows on every edit
    references/            details Claude reads only when a video needs them: setup, fillers,
                           Log footage, sound, retouch and blur, graphics, covers, brand sheet, batches of several videos
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
      behindtext.py        big letters behind the speaker, who stays in front of them (uses the background-blur mask)
      pushin.py            a slow, smooth push in on your face at a key line, keeping your head in the frame
      reframe.py           turns a wide video into a vertical one for Shorts, following you like a camera operator
      chapters.py          YouTube chapters for the description, checked against YouTube's rules
      footcheck.py         reads how a video was recorded (camera, app, settings) and says what to change next time
      conform.py           makes a clip from a second camera (an iPhone) match the main camera before the edit
      cutedges.py          checks every cut edge by its sound (clipped words, fragments, slivers) and fixes the plan
      hookcheck.py         checks the first seconds of a finished video: first frame, first word, silence, text on screen
      checkexport.py       checks a finished export for black frames, stray frames, sound that ends early or cuts out, and clipped words
      wordfixes.py         keeps your list of word corrections (brands, products, foreign words) and applies it to every video
      asrcompare.py        compares Whisper and Parakeet on a piece of your own voice: speed, words, fillers, timing
      overlays.py          times the web page, numbers and before-and-after graphics from your captions
      toolcards.py         finds where each tool is named and times its card, with a pop per logo
      chatwindow.py        turns a described AI chat and the captions into the chat window's timing and key clicks
      explainer.py         turns a described diagram and the captions into an animated explanation's layout and timing
      syncclip.py          syncs a second camera filmed at the same time by its sound and puts its picture into the main recording
      screen.py            screen recordings: smooth zooms onto the action, and screen-above-speaker Shorts
      scriptcut.py         follows your script in the edit: keeps the last good take of each line, finds chapters and Shorts
      shorts.py            cuts the Shorts out of the long video, with their words for vertical captions
      editreport.py        the edit in numbers: what was cut, pauses left, loudness, size
      update_skill.py      updates the skill safely, with a backup
      fillers.py, filler_prompts.py, findfill.py, checkcuts.py   filler hunting and cut checks
      hunt_fillers.py      short-window pass for fillers glued onto words
      retouch/             skin and teeth masks, beautify extras, background blur (and blurcheck.py, which notices a
                           background your camera already blurred), mouth check, pixelfaces.py (pixelates other people's faces);
                           spots.py (calms small bright specks, and freckles if asked, and tells a brow hair from a speck); roi.py (masks are built only where
                           they matter, about 5 times faster); feather.py (the skin mask fades out gradually
                           over the forehead, with no line near the hairline);
                           settings.py reads each video's retouch.json
      sfx/                 four small sound effects, generated with FFmpeg, and typing.py (key clicks
                           for a typewriter title)
      remotion/EmojiPop.tsx  animated emoji pop for Remotion
      remotion/TitleCard.tsx  animated hook title for Remotion
      remotion/ProductTag.tsx product name and price lower third for Remotion
      remotion/ProductPop.tsx the product's photo or clip popping in beside you when you name it
      remotion/WordCaptions.tsx captions with each word lit up in your accent colour as you say it
      remotion/BrowserPage.tsx a web page in a browser window, scrolling, with highlight boxes, from overlays.py
      remotion/StatTiles.tsx  two to four numbers counting up, from overlays.py
      remotion/BeforeAfter.tsx a before and an after with a sweep, from overlays.py
      remotion/ToolCard.tsx   a tool's logo and name sliding in when you name it, from toolcards.py
      remotion/ChatWindow.tsx an AI chat: the prompt types, is sent, the answer appears word by word, from chatwindow.py
      remotion/Explainer.tsx  animated explanation: boxes, arrows and a moving dot, from explainer.py
      remotion/CoverCard.tsx  cover image with products around the speaker's face
      remotion/Thumbnail.tsx  YouTube thumbnail: your face big on one side, a few huge words on the other
      remotion/brandFont.ts   loads the brand font for the templates
      cover/cutout.py      cuts products out of shop photos or video frames (leaves ready cutouts as they are)
      cover/face_box.py    finds the face so the products go around it
      voice/clean_voice.py measures background noise, removes it and polishes the voice
      voice/leveljoin.py   joins clips and levels them to a loudness target, for quiet voices with clicks
  skills/puppet-video/     the second skill: animated puppet videos from a script
    SKILL.md               the steps Claude follows for a puppet video
    references/puppet.md   the dialogue format, the voices and their licenses, installs, writing tips
    scripts/dialogue.py    makes the voice of every turn (Piper) and the mouth shapes (Rhubarb), and the timing
    scripts/captionwords.py  caption words exactly as written in the script, timed to the voice
    scripts/remotion/Puppet.tsx  the characters and the animation
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

The skill, scripts and sound effects are under the MIT License (see `LICENSE`). Tools it uses have their own licenses: FFmpeg (LGPL/GPL), OpenAI Whisper (MIT), faster-whisper (MIT), MediaPipe and its models (Apache 2.0), yt-dlp (Unlicense), Piper (GPL, run as a separate program; each Piper voice has its own license, listed in the puppet skill's `references/puppet.md`), Rhubarb Lip Sync (MIT). Remotion is free for individuals and companies of up to 3 people; larger companies need a paid license. Camera LUTs belong to their makers and aren't included.

Only edit and download videos you own or have the right to use.
