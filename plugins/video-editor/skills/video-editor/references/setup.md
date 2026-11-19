# Installing, and the power check

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

## Folders

Nobody creates folders by hand: Claude makes them. Setup asks where to keep working files (suggesting `~/video-work`) and where finished videos go, checks the work folder with `python -I <skill>/scripts/detect_setup.py folder <path>` (it creates nothing; it says whether the folder is inside OneDrive, iCloud, Dropbox or Google Drive, where big videos time out, and the free space), then creates it. Each video gets `<work folder>/<project-name>/` with a `build/` folder for its working files (`cuts.json`, `plan.json`, `captions.json`, `retouch.json`), `project.md`, and `issues/` when a problem is reported. Finished videos go to the finished-videos folder, or next to the original. A `B-roll kit` folder is optional and the user's own. Windows often syncs Documents and Desktop to OneDrive, so don't suggest those.

## Updating the skill

**Installed as a plugin** (the usual way now): updates come through Claude Code's plugin system, not this updater. If the user asks to update, tell them: `/plugin`, then **Marketplaces**, **malenaaza**, update (or turn on auto-update there once), then start a new session. `update_skill.py` says the same and changes nothing.

**Installed the old way** (a copy in `~/.claude/skills/video-editor`): the updater below brings it up to date and then prints the move to the plugin. With the user's OK: run `claude plugin marketplace add malenaaza/video-editor-skill` and `claude plugin install video-editor@malenaaza`, then `python -I <skill>/scripts/update_skill.py --remove-old-copy` (a backup of the old folder goes to `~/.video-editor/backups/`), then ask them to restart Claude Code. Plugin first, old copy second, so the skill is never missing. Their settings stay where they are.


Most users don't know Git, so updating is done by this skill. When the user asks to update, upgrade or get the latest version of the skill (or says it's out of date), in any language ("actualiza mi skill", "¿hay una versión nueva?"), run it, and give the report in the language they used:

```
python -I <skill>/scripts/update_skill.py --check
python -I <skill>/scripts/update_skill.py
```

The first only says whether a newer version exists (the `VERSION` file). The second backs up the whole installed skill to `~/.video-editor/backups/`, moves a `my-setup.md` that an older version kept inside the skill folder to `~/.video-editor/`, replaces the skill with the latest version, and restores the old one if anything fails. Then:

- Tell the user, in plain words and their language, the new version and what's new, from the changelog it prints. Don't paste the changelog.
- If it lists files the user had changed by hand, say that the update replaced them, and that their versions are in the backup folder it names. Offer to put a change back if they want it.
- If it says it can't tell whether files were changed (the skill wasn't installed by this updater before), say so once.
- If it says the skill is linked to a Git clone, nothing was changed: that setup (the skill's developer, with `~/.claude/skills/video-editor` a link or junction into a clone) is updated with `git pull` in the clone it names, on `main`, then a new session. Tell the user that command and stop. `--check` and `--weekly` say the same when a newer version exists.
- If it can't reach the internet, say so and that nothing was changed.
- Tell the user to start a new session so the new instructions are read.

If `my-setup.md` says `Update check: weekly`, the skill also checks quietly once a week at the start of an edit and mentions a newer version in one line (`update_skill.py --weekly`). It asks permission once. Say "update my skill" to get it.

Never edit the skill's own files to apply a user's preference: those go in `my-setup.md` and in each video's `retouch.json`, which an update never touches.

## Installing

Ask before installing anything. Use the system's package manager.

- **FFmpeg 7 or newer** and **yt-dlp**: Windows `winget install Gyan.FFmpeg yt-dlp.yt-dlp`; macOS `brew install ffmpeg yt-dlp`; Linux the distro's packages (check the FFmpeg version; on FFmpeg 6 or older, replace `-/filter_complex <file>` in this file with `-filter_complex_script <file>`).
- **Python 3.10 to 3.12**, with separate virtual environments, so their packages don't conflict (`speech` is always needed; `face` and `cutout` only for the features named). Put them in `~/.video-editor/`:
  - `speech`: `pip install openai-whisper faster-whisper`. For transcription on an NVIDIA GPU, also install the CUDA 12 and cuDNN 9 libraries that faster-whisper's documentation lists, then confirm with `detect_setup.py --speech-python`.
  - `face` (only needed for retouch, blur and the mouth check): `pip install mediapipe opencv-python numpy`, and download Google's MediaPipe models into `~/.video-editor/models/`:
    - `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`
    - `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`
  - `cutout` (only needed for covers with products): `pip install "rembg[cpu]" pillow numpy`. Its model (about 180 MB) downloads on first use.
- **Voice cleaning** (optional, `references/sound.md`): the RNNoise model `cb.rnnn`, saved as `~/.video-editor/models/cb.rnnn`, from `https://raw.githubusercontent.com/GregorR/rnnoise-models/master/conjoined-burgers-2018-08-28/cb.rnnn` (about 300 KB; FFmpeg runs it, no other install). For the best noise removal, also DeepFilterNet's standalone `deep-filter` program for the user's system from `https://github.com/Rikorose/DeepFilterNet/releases` (one file, no Python packages), on the PATH or with its path saved in `my-setup.md`. The script uses `deep-filter` first, then RNNoise, then FFmpeg's weaker `afftdn`.
- **Node 20+** for Remotion graphics (optional): create a project once with `npx create-video@latest --yes --blank remotion` in the work folder, and copy every file in `<skill>/scripts/remotion/` into its `src` folder.
- **Log LUTs** (only if the user shoots Log): the camera maker's official Log-to-Rec.709 LUT. Apple publishes Apple Log LUTs on developer.apple.com, and Sony, Panasonic, Canon, Fujifilm and Blackmagic publish their own. The user downloads it. Never redistribute it.

Run every Python script with `-I` and the right environment's interpreter (`<venv>/Scripts/python.exe` on Windows, `<venv>/bin/python` elsewhere), as saved in `my-setup.md`.

## Power

On a laptop, run `python <skill>/scripts/detect_setup.py power` before long jobs (transcription, retouch, blur masks, export). Being on battery isn't slow by itself: what slows jobs down is the power mode the laptop uses on battery, and each user sets that differently. So say only what the check found:

- **"plugged in"**: start, no warning.
- **"on battery, power mode … long jobs will be slower"** (a power-saving mode): tell the user before starting, and offer two fixes: plug in, or switch the power mode for battery to Best performance (Windows: Settings > System > Power & battery > Power mode; Mac: turn off Low Power Mode). If `my-setup.md` has a measured slowdown for this laptop, give that number instead of a guess.
- **"on battery, power mode … close to full speed"**: start, and only mention that a long job will drain the battery.
- **"unknown"**: say it may be slower on battery, without claiming it is.

The first time a long job runs on battery in a power-saving mode, time it against the same job plugged in if the user agrees, and save the result on the `Laptop:` line in `my-setup.md` (for example "transcription took 1.5x longer on battery in Best power efficiency").
