# First setup, links, installing, updating and the power check

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

## First setup

Run when `~/.video-editor/my-setup.md` doesn't exist (SKILL.md, Rule 0), or again for a new computer or camera.

1. **Detect.** Run `python <skill>/scripts/detect_setup.py`. It needs only Python and FFmpeg. It reports the system, CPU, GPU, GPU memory (and whether the computer could generate video locally: `no`, `limited` or `yes`, saved in `my-setup.md` for any feature that needs a GPU), power, tools, and test-encodes 4K video with every hardware encoder FFmpeg offers (NVIDIA `nvenc`, Intel `qsv`, AMD `amf`, Apple `videotoolbox`), then recommends the fastest one that really works. An encoder that appears in `ffmpeg -encoders` but fails the test (missing driver, no such chip) is never recommended.
2. **Install what's missing**, with the user's OK. See `references/setup.md`. Then run the script again with `--speech-python <path>` to check whether Whisper can use an NVIDIA GPU.
3. **Confirm in one short message**, in plain words. For example: "I found an NVIDIA RTX 4060. I'll use it for working renders (`h264_nvenc`) and transcription. The final export always uses `libx264` at top quality, so the result looks the same on any computer. OK?"
4. **Ask only what can't be detected**, all in one message:
   - Which cameras or phones do you film with? Do you ever shoot Log (Apple Log, S-Log, V-Log, C-Log...)?
   - Which languages do you speak in your videos?
   - Who are the videos for? List each brand or channel (a business, your personal account...).
   - Where should I keep working files, and where should finished videos go? Get the suggestion first with `python <skill>/scripts/detect_setup.py folder` (it proposes `~/video-work`): "I'll keep working files in `<path>`: big temporary files, never in OneDrive, iCloud, Dropbox or Google Drive. OK, or another folder? And finished videos next to the originals, or in a folder?"
   - Remove every pause and filler, or keep a natural pace? Speed up a little after cutting?
   - Which country do they film in (for 50 or 60 Hz lights)? Then, with the first video from each camera or app, run the footage check in `references/cameras.md` and give the settings advice once.
5. **Create the folders and save** the answers. Check the work folder with `python <skill>/scripts/detect_setup.py folder <path>`; if it says NOT OK, tell the user in one line and use the suggested one. Then create the work folder (and the finished-videos folder, if it isn't "next to the original") yourself. Copy `<skill>/setup-template.md` to `~/.video-editor/my-setup.md` and fill it in. Leave brand colors and fonts as `unknown` until the first video for that brand (Rule 5).
6. **Show what you can do.** End setup by showing the menu from What I can do in SKILL.md, so a new user knows the options before their first edit.

## Links

When the user gives a link instead of a file (SKILL.md, Rule 2).

**When the user gives a link instead of a file,** download it with `yt-dlp` into the project's work folder at the best available quality:

```
yt-dlp --no-playlist -f "bv*+ba/b" -o "source.%(ext)s" "<url>"
```

The download counts as the original: keep it untouched and work on a copy. Only download a whole playlist if the user asks. If the video is private or needs a login, ask before using their browser cookies (`--cookies-from-browser`). Only download videos the user owns or has the right to edit. If a download fails, update yt-dlp and try again, because sites change often.

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

### The skill installed twice

**The skill installed twice:** this skill is now a plugin. If it runs from Claude's plugin folder (`<skill>` contains `.claude/plugins/`) and `~/.claude/skills/video-editor` also exists as a plain folder (not a link to a Git clone, which is a developer's setup), tell the user once, in one line, that the old copy can make Claude pick either one, and offer to remove it: `python -I <skill>/scripts/update_skill.py --remove-old-copy` (it makes a backup first). Then ask them to restart Claude Code.

## Installing

Ask before installing anything. Use the system's package manager.

- **FFmpeg 7 or newer** and **yt-dlp**: Windows `winget install Gyan.FFmpeg yt-dlp.yt-dlp`; macOS `brew install ffmpeg yt-dlp`; Linux the distro's packages (check the FFmpeg version; on FFmpeg 6 or older, replace `-/filter_complex <file>` in this file with `-filter_complex_script <file>`).
- **Python 3.10 to 3.12**, with separate virtual environments, so their packages don't conflict (`speech` is always needed; `face` and `cutout` only for the features named). Put them in `~/.video-editor/`:
  - `speech`: `pip install openai-whisper faster-whisper`. Optional, to try NVIDIA Parakeet: `pip install "onnx-asr[cpu,hub]"` (its 640 MB model downloads on first use). For transcription on an NVIDIA GPU, also install the CUDA 12 and cuDNN 9 libraries that faster-whisper's documentation lists, then confirm with `detect_setup.py --speech-python`.
  - `face` (only needed for retouch, blur and the mouth check): `pip install mediapipe opencv-python numpy`, and download Google's MediaPipe models into `~/.video-editor/models/`:
    - `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`
    - `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`
  - `cutout` (only needed for covers with products): `pip install "rembg[cpu]" pillow numpy`. Its model (about 180 MB) downloads on first use.
- **Voice cleaning** (optional, `references/sound.md`): the RNNoise model `cb.rnnn`, saved as `~/.video-editor/models/cb.rnnn`, from `https://raw.githubusercontent.com/GregorR/rnnoise-models/master/conjoined-burgers-2018-08-28/cb.rnnn` (about 300 KB; FFmpeg runs it, no other install). For the best noise removal, also DeepFilterNet's standalone `deep-filter` program for the user's system from `https://github.com/Rikorose/DeepFilterNet/releases` (one file, no Python packages), on the PATH or with its path saved in `my-setup.md`. The script uses `deep-filter` first, then RNNoise, then FFmpeg's weaker `afftdn`.
- **Node 20+** for Remotion graphics (optional): create a project once with `npx create-video@latest --yes --blank remotion` in the work folder, and copy every file in `<skill>/scripts/remotion/` into its `src` folder.
- **Log LUTs** (only if the user shoots Log): the camera maker's official Log-to-Rec.709 LUT. Apple publishes Apple Log LUTs on developer.apple.com, and Sony, Panasonic, Canon, Fujifilm and Blackmagic publish their own. The user downloads it. Never redistribute it.

Run every Python script with `-I` and the right environment's interpreter (`<venv>/Scripts/python.exe` on Windows, `<venv>/bin/python` elsewhere), as saved in `my-setup.md`.

## Power

`detect_setup.py` also reports GPU memory (NVIDIA: the card's own; Apple Silicon: the computer's shared memory) and a rough verdict on local AI video generation: `no` (under 8 GB or no suitable GPU), `limited` (8 to 16 GB: short, small, slow clips) or `yes` (16 GB or more). Save it in `my-setup.md`; a feature that needs a strong GPU reads it instead of asking, and is not offered on `no`.

On a laptop, run `python <skill>/scripts/detect_setup.py power` before long jobs (transcription, retouch, blur masks, export). Being on battery isn't slow by itself: what slows jobs down is the power mode the laptop uses on battery, and each user sets that differently. So say only what the check found:

- **"plugged in"**: start, no warning.
- **"on battery, power mode … long jobs will be slower"** (a power-saving mode): tell the user before starting, and offer two fixes: plug in, or switch the power mode for battery to Best performance (Windows: Settings > System > Power & battery > Power mode; Mac: turn off Low Power Mode). If `my-setup.md` has a measured slowdown for this laptop, give that number instead of a guess.
- **"on battery, power mode … close to full speed"**: start, and only mention that a long job will drain the battery.
- **"unknown"**: say it may be slower on battery, without claiming it is.

The first time a long job runs on battery in a power-saving mode, time it against the same job plugged in if the user agrees, and save the result on the `Laptop:` line in `my-setup.md` (for example "transcription took 1.5x longer on battery in Best power efficiency").

## Word fixes

Every transcriber misspells brand names, product names and foreign words, the same way each time ("sefora" for
Sephora, "cupillon" for the French "goupillon"). Instead of correcting them in each video, the corrections live in
the user's own list, `~/.video-editor/word-fixes.json`, kept outside the skill so an
update never touches it:

```
python -I <skill>/scripts/wordfixes.py add "cupillon" "goupillon"
python -I <skill>/scripts/wordfixes.py list
python -I <skill>/scripts/wordfixes.py remove "cupillon"
```

`captions.py` applies it to every video. With Whisper, `transcribe.py` also gives the right spellings to the model as
a hint, so it often writes them correctly the first time; Parakeet takes no hints, so with Parakeet the list is what
corrects the captions. Count the corrections over the first two or three videos: if they become a chore with
Parakeet, Whisper with the hint is the alternative (set `Transcription engine: whisper`).

## Transcription engines

Whisper (faster-whisper `medium`) is the default and the one every step was tuned with. **Parakeet**
(NVIDIA parakeet-tdt-0.6b-v3, through `onnx-asr`) is an option: it understands 25 European languages including
Spanish and English and finds the language itself. In a first test (16 s of synthetic Spanish speech, CPU only)
it took 1.3 s against 7.1 s for Whisper medium, wrote the same words but for one ("basta" for "va hasta"), wrote
"mmm" but dropped an "eh" as Whisper did, and its word starts were as close to the real starts of speech
(0.13 s off on average against 0.10 s). That says nothing yet about a real voice or a long recording, where
Whisper's word times drifted up to 1 s around pauses. So compare on the user's own voice before switching:

```
<speech python> -I <skill>/scripts/asrcompare.py <recording> --start 60 --seconds 120 --language es
```

Pick two minutes with pauses, a filler or two and the brand's names. It prints each engine's speed, its text,
the words where they disagree (read them), the fillers each wrote and how far each one's word starts are from
where speech really starts after each pause, measured on the sound. Tell the user the result in plain words
and save their choice as `Transcription engine:` in `my-setup.md`. `hear.py`, `checkcuts.py` and
`hunt_fillers.py` take `--engine parakeet` too.

