# Changelog

What each update of the video-editor skill brings. Newest first.

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
