# Changelog

What each update of the video-editor skill brings. Newest first.

## 2026-11-22 · version 2.14.5

### Fixed
- **A grainy patch under the eyebrow in close-ups.** A patch of small bright specks (shimmery eyeshadow or
  highlighter, or a dry or bumpy patch of skin) is kept by the smoothing, so it stood out next to the smooth skin ("still some texture
  around the eyebrows"). The spot pass (`spots.mkv`) now also finds small bright specks and calms them
  (`shimmer_calm` in `retouch.json`, default 0.6; 0 turns it off; `shimmer_contrast`, default 8). Real reflections,
  eyes, lips and brows are never touched. **Rebuild your masks** (`mask.py`). Guide: `references/retouch.md`,
  Bright specks.

## 2026-11-22 · version 2.14.4

### Fixed
- **Eye whites looked grey and blotchy after Beautify.** The whites step lifted only the brighter half of each eye
  white and took the colour out of it, so a white with veins, spots, a shadow or a yellow tint came out in patches.
  Now the whole white is covered (not the iris or the lashes), a median takes out veins and small spots inside it,
  and it is lifted and de-coloured in one piece (`eye_white` still sets how much: 0.05, 0.09, 0.13 in the
  presets; 0 turns it off). **Rebuild your masks** (`mask.py`): `eyewhite.mkv` changed. Guide:
  `references/retouch.md`, Beautify.

## 2026-11-22 · version 2.14.3

### Fixed
- **Texture left under the eyebrows in close-ups.** The rule that keeps the brow's own hairs sharp also protected
  the skin next to them, and the band it protected grew with the face's size, so on a big close-up a strip of skin
  right under the brow (a shimmery lid, stubble, pores) stayed unsmoothed next to smooth skin. Now only a dark patch
  that is mostly inside the brow outline, or that is as thin as a hair, is kept; wider patches and round specks
  outside it are skin and are smoothed. The brow's hairs stay as sharp as before. The freckle pass from 2.14.1
  is now **off by default** (`spot_calm` 0, was 0.55): that diagnosis was wrong for the reporter, whose freckles
  never looked like dirt, and the skill shouldn't change a face's natural features unasked; set `spot_calm` to 0.55
  to turn it on (`spot_contrast` is now 14, was 18). **Rebuild your masks** (`mask.py`). If a band is still visible:
  `"brow_mode": "margin", "protect_brows": 10` in `retouch.json`. Guide: `references/retouch.md`, Grain under the brow.

## 2026-11-22 · version 2.14.2

### Fixed
- **A line across the forehead in close-ups.** The face outline the retouch follows ends in the middle of the
  forehead, and the skin mask faded out there over a fixed 9 px, so on a close-up the skin below was smooth and the skin
  above kept its fine texture and baby hairs, with a visible line between them that crawled as the head moved. Now the
  mask's outer edge fades over a share of the face's height (`forehead_feather` in `retouch.json`, default 0.04; 0 is
  the old edge), only into skin-coloured pixels, so hair and background aren't smoothed. **Rebuild your masks**
  (`mask.py`) for the fix to show. Guide: `references/retouch.md`, Hairline and forehead.

## 2026-11-22 · version 2.14.1

### Fixed
- **Freckles looked like dirt in close-ups.** A close-up smooths the skin twice, and a smoothing filter keeps small
  dark spots, so the freckles were the only texture left: "little black stains around the eyebrow", worst on the
  side of the face closer to the camera. Now a freckle keeps about half its contrast (`spot_calm` in `retouch.json`,
  default 0.55; 0 keeps spots as before, 1 smooths them away): the new mask `spots.mkv` and a last pass in
  `retouch.txt` do it, and moles, eyes, lips and brows are never touched. The eyebrow rule also stopped mistaking a
  freckle beside the brow for a brow hair (it kept it sharp and dark), and its distances now scale with the face's
  height. **Rebuild your masks** (`mask.py`) before the next retouch: the filter files take `spots.mkv` as input 4,
  and `retouch-blur.txt` takes the background mask as input 5. Guide: `references/retouch.md`, Freckles and spots.

## 2026-11-22 · version 2.14.0

### New
- **A saved list of word fixes** (`scripts/wordfixes.py`). Transcribers misspell brand names, products and foreign
  words the same way in every video ("sefora" for Sephora, "cupillon" for the French "goupillon"), and fixing them
  per video meant fixing them again every time. Now the fix is saved once, in `~/.video-editor/word-fixes.json`
  (your settings, outside the skill, so an update never touches it) and `captions.py` applies it to every video; a
  video's own `--fix` file wins, and `--no-personal-fixes` leaves it out. The skill asks once, "remember it for every
  video?", when you correct a word. With Whisper the right spellings also go to the model as a hint
  (`transcribe.py`); Parakeet takes no hints, so for it the list is the only fix. Guide: `references/setup.md`, Word fixes.

## 2026-11-22 · version 2.13.0

### New
- **AI chat window** for videos about AI: when you say what you asked an assistant, a clean chat window shows it.
  Your prompt types into the box with soft key clicks, it's sent, three dots "think", and the answer appears word
  by word, with lists as bullet points. Each turn starts as you say it. `scripts/chatwindow.py` works out the timing
  from your captions, and the new Remotion template `ChatWindow.tsx` draws it in your brand's colours, light, dark
  or warm (a theme that evokes Claude's look: cream, the answer in serif type, a coral send button), wide or vertical, full screen or over you. It's a generic chat design with the app's name (and its
  press-kit logo, if you have one), not a copy of any company's interface. Scripts mark prompts for it. Guide:
  `references/graphics.md`, AI chat window. The key clicks come from the same sound as the typewriter title.
- **Tool cards** for videos about AI: when you name a tool (Claude, Gmail, Notion...), a card with its logo and name
  slides in a beat before the word and leaves on its own, with a soft pop. Tools named in a row stack; a tool shown
  in the last 20 seconds isn't shown again. `scripts/toolcards.py` finds the names in your captions; the new
  Remotion template `ToolCard.tsx` draws them. Logos come from each brand's press kit; without one, a badge with
  the initial. Guide: `references/graphics.md`, Tool cards.
- **Web page, numbers, before and after** for educational videos (`scripts/overlays.py`, new templates
  `BrowserPage`, `StatTiles`, `BeforeAfter`): a real web page in a browser window that scrolls to what you mention
  and highlights it: a fine outline fitted to the words, with the rest of the page dimmed like a spotlight (a first
  version with a thick, tinted box hugging the text across the whole column looked crude), and a box out of view
  scrolls the page to it first; two to four numbers that count up as you say
  them, written the Spanish way; and a before and an after, images or texts, with the after sweeping in as you say
  it. Guide: `references/graphics.md`, Web page, numbers, before and after.

## 2026-11-22 · version 2.12.0

### New
- **Every cut checked by its sound** (`scripts/cutedges.py`), before the cut is rendered. Word times from a transcript
  are often 50 to 100 ms off, so a cut can land inside a word. It looks at the recording around every edge and lists
  cuts that start or end in the middle of a sound, scraps of removed words left at an edge, and pieces too short to
  see. `--fix` writes a corrected plan: a word cut in two is kept whole when most of it was kept and dropped whole
  otherwise (moving to "the quietest moment nearby" left half a word in a first test).
- **The opening checked** (`scripts/hookcheck.py`) on every finished video: a black or blank first frame, a clipped
  first word, more than half a second of silence before you speak, a sound effect on your first word, nothing
  written on screen in the first 1.5 seconds (most people start muted), and the words of the first 3 seconds, to
  judge whether they're the promise or the question.

## 2026-11-22 · version 2.11.0

### New
- **Every export is checked before it's delivered** (`scripts/checkexport.py`): black frames in the middle of the
  video, a single stray frame left by a cut (one frame unlike both its neighbours, which no contact sheet shows),
  picture and sound that end apart, sound that drops to digital silence, missing colour tags (some players then show
  faces darker and redder), and, with a transcript of the export, words clipped at a cut. A failure means fix and
  export again. The idea of checking the file itself came from comparing with another editing skill.

### Fixed
- **The final export now tags its colours as Rec.709.** It had no colour tags, so some players guessed and showed
  faces darker and redder. On FFmpeg 7 and later the tags have to be set on the frames (`setparams` at the end of
  the filter chain), because those versions ignore `-color_primaries` and the like; both are now in the export line.

### Changed
- **Calmer sound effects on animated explanations:** a soft pop as each box appears and one sparkle when the dot gets
  home, nothing on the arrows. The first version made 10 sounds in 17 seconds, which was too busy; it's still there
  as `--sounds-style lively`. Each sound now lands with its loudest moment on its cause (the sparkle used to sound
  0.16 s late), and each piece appears 0.2 s before you name it, which reads as in time. `references/sound.md` has
  the rule for every effect: a sound needs a cause on screen, never a whoosh under text.

## 2026-11-22 · version 2.10.0

### New
- **Parakeet, a second transcription engine:** NVIDIA's Parakeet v3 (through `onnx-asr`, no NVIDIA software
  needed) understands Spanish, English and 23 more European languages. On a computer without a graphics card it
  was about 5 times faster than Whisper in a first test, with the same words but for one. `transcribe.py
  --engine parakeet` writes the same transcript as Whisper, so the rest of the edit doesn't change; `hear.py`,
  `checkcuts.py` and `hunt_fillers.py` take it too. Whisper stays the default.
- **`scripts/asrcompare.py`** compares the two on a piece of your own voice: speed, text, the words where they
  disagree, the fillers each wrote, and how close each one's word times are to where your speech really starts
  after a pause (measured on the sound, since cuts are made there). Your choice is saved as `Transcription
  engine:` in your settings. Guide: `references/setup.md`, Transcription engines.

## 2026-11-21 · version 2.9.0

### New
- **Animated explanations** for educational videos: boxes, arrows and a dot that travels between them, showing how
  something works (how an MCP connects Claude to your Gmail, how a request goes and comes back). Each piece appears
  when you name it: Claude writes what the diagram has and the phrase that brings in each piece, and
  `scripts/explainer.py` finds those phrases in the captions, lays the boxes out (a row in a wide video, a column
  in a vertical one, with room for the arrows and their labels) and prints the timeline. The new Remotion template
  `Explainer.tsx` draws it in your brand's colours and font: each box in its own colour on a soft gradient, boxes
  pop in, arrows draw themselves and keep moving dashes along them, a glowing dot with a short trail travels the
  path and each box lights up as it passes. It comes with its own sound effects, timed to the picture: a
  pop as each box appears, a soft whoosh for each arrow and as the dot sets off, a tick at each box it reaches and
  a sparkle when it arrives (`explainer-sfx.wav`, mixed under your voice). Full screen, or over you with a transparent background. Guide:
  `references/graphics.md`, Animated explanations. When Claude writes a script it proposes them itself: one to three
  passages per educational video where something is explained that can't be filmed, marked with the boxes and
  arrows, and the lines written to name each piece once and in order, so the animation follows your voice. Without a
  script, it suggests passages after reading the transcript.

## 2026-11-21 · version 2.8.0

### New
- **A second camera for some lines:** film most of a video with your main camera and a few lines (the hook, the
  ending, a close-up) with your iPhone. `scripts/conform.py` makes each iPhone clip match the main camera before
  the edit: the same frame rate at a steady rate (phones record a variable one, which makes the sound drift), the
  same size (a clip filmed the other way round is cropped to fill, or put on bars), HDR turned into normal video,
  Rec.709 colour tags, and the same sound settings. `--check` only says what differs. The colour of the two
  cameras is still matched by eye in the grade. Guide: `references/cameras.md`, Two cameras.
- **Second camera at the same time:** when the main camera keeps recording and the iPhone films some parts from the
  side, `scripts/syncclip.py find` finds where each iPhone clip starts in the main recording by comparing their
  sound (to about a millisecond; a clip that doesn't clearly match is reported, not used, and drifting clocks are
  flagged), and proposes using its picture for the whole time it recorded. `build` then writes one recording with
  the iPhone's picture in those stretches and the main camera's sound throughout, so the voice never changes and
  the rest of the edit works on it unchanged. The skill asks once how you film with a second camera (at the same
  time or in separate takes) and saves it as `Second camera:`.
- **Shot list:** when some lines go on a second camera, the shot list says which camera films each line and groups
  the iPhone lines, so the phone is set up once.
- **Teleprompter:** with the first script the skill asks once whether you read from a teleprompter and on which
  camera, and saves it (`Teleprompter:` in your settings). If you do, it also writes `teleprompter.txt`: only the
  words you say, no markers or numbers, directions in capitals and brackets so you don't read them out, and a pause
  where each chapter ends. When the iPhone films from the side while you keep reading the main camera's
  teleprompter, every line is in it, with an `(IPHONE)` reminder before the iPhone parts; lines said into a front-on
  iPhone without a teleprompter go in the shot list to learn; with one on every camera, there is a file per camera.

### Fixed
- `conform.py`: on newer FFmpeg (7 and later) the conformed clip came out with no colour tags, because FFmpeg now
  takes them from the frames; they are now set on the frames too.
- `voice/leveljoin.py` (joining clips at one loudness) stopped with an error on FFmpeg 8 and later, which removed
  the `-filter_complex_script` option it used. It now passes the filter directly, which works on every version.
- With a second camera, the script's report is read per camera: lines filmed on the other camera are expected to be
  missing.

## 2026-11-21 · version 2.7.0

### New
- **Pixelate the faces of other people:** `scripts/retouch/pixelfaces.py` hides bystanders, customers or children
  and keeps the speaker sharp. `scan` finds and follows every face (with the face model the skill already uses) and
  writes a sheet with the speaker in green and everyone else in red; `build` makes the mask and prints the FFmpeg
  command; `verify` looks for any face still visible in the result. The detector misses faces under a tenth of the frame, so the scan searches the whole frame and overlapping squares
  (`--thorough` adds half-size squares, for faces of about 50 px). A face the detector loses for up to 1.5 s is
  covered by moving the box between the sightings, the box is held 0.4 s before and after, and the lost stretches
  are listed so you can look at them. Faces the detector misses (small, side-on, turned away) are added with
  `pixel_extra`; the speaker can be changed with `pixel_keep`. New settings `pixel_*` in `retouch.json`. Guide:
  `references/retouch.md`. It hides faces only: voices, name tags and licence plates stay.
- The mask is applied with alpha, not `maskedmerge`: `maskedmerge` squeezes a gray mask into video levels, and in a
  test 11,644 of 32,000 pixels of a pixelated face still held some of the original.

## 2026-11-19 · version 2.6.1

### New
- **Work folder at setup:** the first-use questions now ask where to keep working files (suggesting `~/video-work`),
  and `detect_setup.py folder [path]` checks it: it says whether it is inside OneDrive, iCloud, Dropbox or Google
  Drive (big videos time out there; Windows often syncs Documents and Desktop) and how much space is free. Claude
  creates the work folder, each video's project folder and its `build` folder itself. Older setups without a work
  folder are asked once.

### Fixed
- **Updates for a linked clone:** when `~/.claude/skills/video-editor` is a link or junction into a clone of this
  repository (how the skill's developer runs it), the weekly notice and `update_skill.py --check` now say to run
  `git pull` in that clone, and name the folder. Before, the notice said "update my skill", which then refused.
  The clone is also found from the skill's new place deep inside the repository.

## 2026-11-19 · version 2.6.0

### Changed
- **Grown-up puppets:** Lola, Max and Pixel are redrawn as adults in a flat editorial style, from the chest up behind
  a table on a warm neutral background, instead of round cartoon creatures on pink. Smaller almond eyes, thin brows,
  a nose, real hair (Lola: shoulder-length with a fringe and earrings; Max: short hair, beard and thin glasses) and
  calmer movement. `colour=` is now the clothes colour, and the new `skin=` and `hair=` set a person's skin tone and
  hair, so the characters can look like the people the video is for. Dialogues written before still work.

## 2026-11-19 · version 2.5.0

### New
- **Camera check:** the first time a video comes from a new camera, phone or app, `scripts/footcheck.py` reads how it
  was recorded and the skill tells you once what to change for the next recordings, in that app's own words: the
  frame rate for your country's lights (25 fps in Spain), the shutter (Blackmagic Camera records it: 1/50 at 25 fps),
  4K when Shorts will be cut from a horizontal video, Bluetooth sound (16 kHz, call quality), HDR, the front camera,
  and files squeezed by social or messaging apps. It recognises Blackmagic Camera (confirmed on a real file), the
  iPhone Camera app, Final Cut Camera, Android phones, Sony, GoPro and DJI; when it can't tell, it asks once. Results
  are saved per camera in your setup. Guide: `references/cameras.md`.

## 2026-11-19 · version 2.4.0

### New: puppet videos
- A second skill in the plugin, **puppet-video**: animated videos with no one on camera. One or two original
  cartoon characters (Lola, Max and the robot Pixel, drawn in code and recoloured with your brand's palette) say a
  script with a free voice made on your computer (Piper; Spanish from Spain and British English voices included),
  with mouth shapes matched to every sound (Rhubarb Lip Sync), blinking, breathing, expressions, and leaning in when
  they talk. Captions show the script's exact words (Whisper only gives the timing), and an optional translation
  goes under each line for language students. Use it for a helper character inside your videos or for short
  dialogues for students. `credits.txt` lists each voice's license and the credit line to add when it asks for one.

### New: background already blurred
- Before offering background blur, the skill now checks whether your camera already blurred the background (a
  phone's Cinematic or Portrait mode, or a lens wide open) with `scripts/retouch/blurcheck.py`, and doesn't add more.
  It also reminds you to check that a product held up wasn't blurred by that mode, which can't be fixed afterwards.

### New: for YouTube
- **Script first:** ask for a script and Claude writes it with chapters, screen recordings, graphics and Shorts
  marked, plus a shot list for filming in one sitting (`references/script.md`). After filming,
  `scripts/scriptcut.py` keeps the last good take of every line, removes the other takes and false starts, tells you
  which lines you didn't say and which talk isn't in the script, and turns the markers into the chapters and the
  Shorts. `scripts/shorts.py` then cuts each Short out of the long video with its words for vertical captions and the
  steps to finish it.
- **Shorts from your horizontal video:** `scripts/reframe.py` turns a wide video into a vertical one that follows
  you like a camera operator: still while you talk, a smooth move when you shift, keeping up when you walk, and a cut
  when the footage cuts. Film once in 4K, and get the YouTube video and the Shorts from the same recording.
- **Screen recordings for tutorials:** `scripts/screen.py` finds where the action is on the screen (typing, a menu,
  a result appearing), suggests zooms you can check on a contact sheet, and draws smooth zooms onto them. For Shorts
  it puts the screen on top and you below, centred on your face.
- **Chapters:** `scripts/chapters.py` turns the topics Claude marks in the transcript into the chapter lines for the
  YouTube description, with times that follow the cuts, checked against YouTube's rules (first at 0:00, at least 3,
  each at least 10 seconds). It can also embed them in the video file.
- **Thumbnails:** a new Remotion template, `Thumbnail.tsx`: your face big on one side and two to four huge words
  on the other, in your brand's colours, kept clear of the corner where YouTube shows the length, and checked at
  phone size. `face_box.py` now also prints the frame's size for it.

## 2026-11-18 · version 2.3.1

### Fixed
- Beautify no longer makes skin look grey. The glow lifted the skin's brightness but not its colour, so at
  `medium` the cheeks came out lighter and paler, and next to the original the face looked washed out. The glow
  now gives back, on the skin only, the colour the lift takes away, leaning very slightly to red so rosy cheeks
  stay rosy instead of turning orange (a whole-picture colour boost did that). The hue stays within about a degree
  of the original on light to deep skin tones, and a test checks it.

## 2026-11-17 · version 2.3.0

### Changed
- The skill is now a Claude Code plugin, "Video Editor for Creators". Install it with
  `/plugin marketplace add malenaaza/video-editor-skill` and `/plugin install video-editor@malenaaza`; updates come
  through the plugin system (turn on auto-update once). The skill itself works exactly as before, and your settings
  in `~/.video-editor/` are not touched.
- The skill moved to `plugins/video-editor/skills/video-editor/` in the repository. A `video-editor/VERSION` stub stays
  at the old place so copies installed the old way still learn about new versions.

### New
- A typewriter animation for the hook title (`"animation": "typewriter"` in `TitleCard`): letters typed one by
  one with a blinking cursor in the accent colour and a small bounce at the end, and `scripts/sfx/typing.py` for
  matching soft key clicks. Also fixed: the template's sample highlight word no longer leaks into real titles.
- Word highlight captions: a rounded box in the brand's accent colour wipes in behind each word while it's said,
  TikTok-style. Same captions, timing and position as the normal ones: `captions.py --remotion-props` writes the
  props for the new Remotion template `WordCaptions.tsx`, which renders them as a transparent overlay. Choose it in
  the `Captions:` line of your setup, or ask for it. (The look was tried first with a HyperFrames registry piece;
  the template is our own code.)
- A part in black and white: `scripts/mono.py` turns one or more parts of the video grey (a "before", a
  flashback), with a short fade out of and back into colour and a touch more contrast. Give the times, or a phrase
  you say ("from 'antes' until 'y ahora'"). Captions, titles and graphics stay in colour on top.
- A slow push in on your face at a key line, like a camera moving closer: `scripts/pushin.py` finds your face,
  eases in (1.15 by default), holds and eases back out, by times or by a phrase you say. It keeps your head in the
  frame (in a close-up, the forehead) and your mouth clear of the captions, lowering the zoom when there isn't
  room. Drawn with sub-pixel precision, so a slow zoom doesn't shake; captions and graphics stay still on top.
- Moving from the old install: "update my video-editor skill" brings an old copy up to date, then offers the move to
  the plugin; `update_skill.py --remove-old-copy` backs the old folder up and removes it (never a developer's clone).
  The updater never replaces a plugin install, and the skill warns once if it finds itself installed twice.

### Fixed
- A forced caption break (`|` at the end of a fix in `fixes.json`) was ignored when the transcript had a comma
  after that word ("Hypnotize," stayed in one caption with the next word).
- The background blur kept blurring the top of a product held in the hand (a serum's cap: 72% blurred with the
  old setting, up to 9% with the current one). The area kept sharp now also stretches past the fingers along the
  direction the hand holds the product (`hand_reach` in `retouch.json`), a hand the tracker misses is looked for
  again before its last place is used, and the area grows while it's lost. On the same frame the cap stayed sharp
  and most of the background was still blurred.

## 2026-11-17 · version 2.2.0

### New
- Product pop-in from B-roll: when you name a product, its photo (cut out) or a short clip from your B-roll pops
  in beside you for about 2.6 s, with a pop sound and, if you want, its name and price. `scripts/broll.py`
  indexes the B-roll folder (photos and clips, with a numbered contact sheet) and finds when each product is said
  and which file matches it (accents and plurals ignored); Claude checks the choice against the video and asks you
  before rendering. New Remotion template `ProductPop.tsx`, and a tested FFmpeg fallback without Remotion.
  `scripts/popplace.py` puts it beside the temple and never over the product in your hand: it finds the face
  and the hands, and goes smaller, lifts above them, uses the other side or drops the name when they're in the way.
  New lines in the setup: `B-roll folder:` and `Product pop-in:`.
- White balance measured, not judged by eye: `scripts/balance.py` finds the white and grey parts of the picture (or a
  region you point at), names the cast ("noticeable cool (blue) cast, 4.9%") and gives the filter that removes it. The
  user sees the frame as it is, with half and with the full correction, and decides. With the brand's colour boost
  it offers half first (`--strength 0.5`): the full correction plus the boost made skin clearly warmer on a real frame.
- The edit in numbers: `scripts/editreport.py` reports the length before and after, pieces kept, retakes and fillers
  removed, pauses left, loudness and true peak, and the picture details, and saves it next to the export.
- The cut plan offers 2 or 3 openings and endings to choose from, the brand's usual one first.
  (These three ideas come from comparing with another reels plugin; the code is our own.)

## 2026-11-17 · version 2.1.0

### New
- Users can send bugs and ideas to the author. When a user says something looks wrong, or wishes the
  skill did something it doesn't, Claude offers to send it: `scripts/report.py` writes a report in the
  user's language, adds the skill version and system, removes the home path and user name, saves it in
  `~/.video-editor/reports/`, and prints a link that opens a GitHub issue already filled in (and an email
  link if `video-editor/support.json` has an address). Nothing is sent without the user, and frames or
  videos are never included. New GitHub issue templates for bugs and ideas.

## 2026-11-17 · version 2.0.0

### New
- Updating without Git: say "update my video-editor skill" and `scripts/update_skill.py` checks the
  `VERSION`, backs up the installed skill to `~/.video-editor/backups/`, moves a `my-setup.md` that an
  older version kept inside the skill folder to `~/.video-editor/`, installs the latest version, and
  restores the old one if anything fails. It reports which files had been changed by hand, and never
  touches a skill that is linked to a Git repository. This is version 2.0.0 (`video-editor/VERSION`).
- Asking to update works in any language: the skill's description now mentions updating (so a request like
  "actualiza mi skill" loads it), and Rule 0 says to answer in the user's language.
- An optional weekly reminder: with `Update check: weekly` in `my-setup.md` (asked once), a session
  starts by checking quietly whether a newer version exists (`update_skill.py --weekly`), at most
  once every 7 days, and says one line if so.
- Problems the user notices while editing ("the skin looks bad at 3:32") are logged in
  `~/.video-editor/skill-issues.md` with the saved frame, the step and the settings in force, so
  the skill can be fixed later from the log and not from memory. `CLAUDE.md` tells a fixing session
  to start there.

## 2026-11-16

### New
- `beautify` in `retouch.json` (off, light, medium, strong): one setting for skin softening plus a
  soft glow, brighter under-eyes and whiter eye whites (`retouch/beautify.py`, `beauty.py`).
  No makeup and no reshaping, by design. Checked on real frames: the effects stay inside the skin,
  under-eye and eye-white areas.

### New (from a five-clip, 4:45 edit on real footage)
- `drops.py`: a second pass that removes fillers, held sounds and extra pauses from a finished cut
  without rebuilding masks. Every drop is a whole number of frames, picture and voice are cut
  together, and a time map moves the captions. `--list-pauses` audits a joined voice.
- `heldsounds.py`: finds held sounds ("deeee") with a strict spectrum test that clipped no word
  (an earlier detector clipped 12 of 27 cuts).
- `voice/leveljoin.py`: joins clips and levels them to a target that `loudnorm` can't reach on a
  quiet voice with clicks (it stopped at -13 LUFS when -11 was asked).
- `hear.py` transcribes short pieces alone; `asr.py` gives `hear.py`, `checkcuts.py` and
  `hunt_fillers.py` one `--engine` (openai or faster) and `--model` option. `hunt_fillers.py` also
  takes `--step`.
- `captions.py --on-cut` builds captions from a transcript of the cut voice (word times on a long
  source were up to 1 s off around pauses), `--drops` follows `drops.py`, `--two-lines` and
  `--dangling` break captions better.
- `crown` in `retouch.json` keeps a tall headband or hair above the head sharp in the background blur.

### Fixed (from the same edit)
- `cutplan.py` finds pauses by loudness against the voice's peaks instead of a fixed level, so
  pauses with a breath or click in them are removed (48 were left in a 4:45 cut), and it never
  cuts a whispered word as a pause.
- `cutplan.py filter` splits a long cut into several selects of 40 terms: FFmpeg stopped with
  "Cannot allocate memory" on one select with 128 terms.
- The instructions now say to run the filler hunt last, on the final joined voice (it found 8
  real fillers only there), to check cuts with the `medium` model, and to build blur masks on the
  render the colour keys were sampled on when the grade changes.

## 2026-11-15

**If you're updating from an earlier version:** copy `video-editor/my-setup.md` out before you
replace the folder, and put it back afterwards. The skill then moves it to
`~/.video-editor/my-setup.md`, where later updates can't delete it.

### New
- `cutplan.py` builds the cut plan: it finds the pauses, applies the retakes and fillers listed
  in `cuts.json`, snaps every cut to whole frames, and writes the FFmpeg filter that makes the cut.
- `captions.py` writes the captions for the cut in the brand's style, with a fixes file for
  misspelt product names.
- Each video's folder gets a `project.md` that records what's done, so an edit can continue in a
  new conversation without transcribing, cutting or building masks again.
- Retouch and blur levels for one video go in a `retouch.json` in that video's folder. The
  scripts are no longer edited per video. Colour keys for clothing and held objects are written
  as data there.
- A test suite (`tests/test_skill.py`) that GitHub runs on every push.

### Changed
- `SKILL.md` is about half its old size. Details for optional steps moved to
  `video-editor/references/` and are read only when a video needs them. A build order near the
  top shows the steps of an edit in sequence.
- Returning users get a one-line confirmation instead of four questions when the brand, its
  platforms and its usual call to action are already saved.
- `my-setup.md` is saved in `~/.video-editor/` instead of the skill folder.
- The background blur scripts keep only the head, neck and skin sharp by default. The cardboard
  box and red sweater keys that were built in as examples are now examples in `settings.py`.

### Fixed
- Products held up in the hand stay sharp when they stick out past the fingers: the area kept
  sharp around a hand is larger (`hand_pad` 120 instead of 60; the top of a lipstick was being
  blurred).
- The skin around the eyebrows and on the lid below them is smoothed like the rest of the face.
  The brows are protected by their own dark hairs instead of a 25 px margin around the whole
  brow, and the margin around the eyes is 15 px (`brow_mode`, `brow_contrast`, `protect_eyes` in
  `retouch.json`).
- Skin softening covers the far cheek when the head is turned: the tracker's outline ran through
  the middle of that cheek, so its outer strip kept every freckle. `mask.py` now adds the
  skin-coloured area that touches the face (`region_grow` in `retouch.json`).
- Skin softening and background blur work on faces cut in half by the frame edge. In a tight
  close-up the face tracker found no face, so the mask was empty and the skin was left
  unsoftened. The scripts now retry with the visible half mirrored across the edge
  (`facetrack.py`; `edge_faces` in `retouch.json`).
- Retouch and background blur can run together: `retouch-blur.txt` does both in one pass (the
  two separate filter files clashed).
- `blurmask.py` reads `clean.mp4`, as the instructions say.
- `hunt_fillers.py` accepts any audio or video and converts it itself; it gave wrong results on
  audio that wasn't 16 kHz.
- `checkcuts.py` stops when FFmpeg fails instead of reporting an empty transcript.
- `findfill.py` reads `plan.json` and allows for the speed-up.
- The setup template has the fields the skill saves: cutout Python, noise removal paths,
  Remotion license, usual call to action.
