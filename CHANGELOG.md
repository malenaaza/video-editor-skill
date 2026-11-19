# Changelog

What each update of the video-editor skill brings. Newest first.

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
