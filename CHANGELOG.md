# Changelog

What each update of the video-editor skill brings. Newest first.

## 2026-11-17

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
