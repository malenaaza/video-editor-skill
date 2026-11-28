# Submitting video-editor to Anthropic's plugin directory

A draft of everything the submission form at https://claude.ai/directory/manage asks for. Copy each part into the
form. It needs a paid claude.ai plan (Pro, Max or Ultra), and the repository must be public when the listing goes
live (it already is).

Submit **only `plugins/video-editor`**. `plugins/puppet-video` stays in this repository's own marketplace: it makes
voices with a text-to-speech model (Piper), and the directory policy doesn't allow plugins that use AI models to
generate audio, video or images.

## Before you submit

1. **The icon.** The first icon the portal sees becomes the listing's icon for good. The placeholder is
   `plugins/video-editor/.claude-plugin/icon.png` (1024 x 1024, a phone frame with a play button and captions). To use
   your own, replace that file with a square PNG of 512 to 2048 px, under 2 MB, before the first submission.
2. **Validate:** `claude plugin validate ./plugins/video-editor --strict` should end with "Validation passed" and
   nothing to report. The portal runs more checks than this command, plus a security scan.
3. **Expect a person to review it.** The four sound effects in `scripts/sfx/` are `.wav` files, and any binary that
   isn't an image or a font holds the version for a reviewer. That is a hold, not a rejection.

## Source

- Repository: `malenaaza/video-editor-skill`
- Plugin folder: `plugins/video-editor`

## Listing details

**Name:** Video Editor for Creators

**Short description:**
Edit talking-head Reels, TikToks, Shorts and YouTube videos on your own computer, in your brand's style.

**Description:**
A personal video editor for people who film themselves talking to camera: beauty and product creators, teachers,
small businesses. Give Claude a recording and it does what an editor would: removes retakes, pauses and filler
words ("um", "eh"), adds captions in your brand's fonts and colours, levels and cleans the voice, softens skin and
blurs the background while keeping products sharp, adds an animated title, product tags and explanatory graphics
timed to what you say, and exports vertical and wide versions with a ready-to-post caption, hashtags and cover.

It runs entirely on your computer with FFmpeg and Python: your videos are never uploaded anywhere. The first time,
it checks your hardware, picks the fastest encoder that really works on it, and asks a few questions about your
brands, which it remembers. You stay the director: it shows you the cuts and choices and never posts for you.
Works in any language; developed on Spanish and English videos.

**Category:** Media

**Works in:** Claude Code (it needs your files and locally installed tools, so it doesn't run in a claude.ai chat).

**Example prompts** (the form asks for at least three):

1. "Edit this video for Reels and TikTok: C:\Videos\serum-review.mp4. Remove the retakes and pauses and add captions."
2. "Make a YouTube video from this recording, with chapters, and cut two Shorts from it that follow my face."
3. "My voice sounds echoey and there's a hum in this clip. Clean it up and level it for Instagram."
4. "I say 'three things' in this video. Add a checklist that ticks each one off as I say it."
5. "Write me a script for a video about choosing a vitamin C serum, then cut it after I film it."

## Data handling

**Does it collect personal data?** No. It processes the user's own video and audio files on their computer. Nothing
is sent to the author or to any service run by the author.

**Where data stays:**
- Videos, transcripts, frames and masks stay in a work folder on the user's computer, chosen at setup.
- Settings (hardware, brands, style choices) are saved in `~/.video-editor/my-setup.md` on the user's computer.
- Transcription (Whisper or Parakeet), face tracking (MediaPipe) and noise removal run locally.

**Network access, all disclosed in the skill's instructions:**
- Installing tools at setup, with the user's OK: Python packages from PyPI, FFmpeg and yt-dlp from the system's
  package manager, Remotion from npm.
- Model files downloaded once: Whisper models (Hugging Face, through faster-whisper), MediaPipe face and hand models
  (`storage.googleapis.com/mediapipe-models`), an RNNoise model (`raw.githubusercontent.com/GregorR/rnnoise-models`),
  and optionally the rembg cutout model on first use.
- Update check: only if the user agrees (asked once), at most once a week it reads the skill's `VERSION` file from
  `raw.githubusercontent.com/malenaaza/video-editor-skill`. It sends nothing about the user.
- Downloading a video only when the user gives a link (yt-dlp), and only videos they own or may edit.
- Hashtag research uses Claude's own web search, with the video's niche and topic only.

**Bug reports:** `scripts/report.py` writes a report on the user's computer, removes their home folder path and
user name, and prints a link that opens a pre-filled GitHub issue. The user reviews it and clicks Submit
themselves; nothing is sent automatically, and frames, audio or video are never included.

**Third-party data flows:** none.
**Retention:** none on the author's side; everything stays on the user's computer until they delete it.
**Use by under-18s:** not designed for children; the editing itself has no age-specific features.

## Note for the reviewer

The plugin uses no generative AI models: it doesn't generate or alter people's faces, voices or bodies, and makes no
synthetic speech, images or video. It edits footage the user filmed, with FFmpeg. The machine-learning models it runs
locally analyse rather than generate: speech-to-text for the cut list and captions (Whisper), face landmarks to place
masks for skin softening and background blur (MediaPipe), and noise suppression (RNNoise, DeepFilterNet).
Skin softening and "light beautify" are blur and brightness filters inside a face mask, with no reshaping or makeup.
For scripts with AI clips, it writes text prompts the user can paste into an external generator of their choice;
the plugin doesn't call any generator. The animated puppet videos with synthetic voices were split into a separate
plugin, which is not part of this submission.

## Compliance

- Contact email: the address you want reviewers and users to reach (the one in `support.json`, or another).
- Support: GitHub issues at https://github.com/malenaaza/video-editor-skill/issues (templates for bugs and ideas).
- License: MIT (`LICENSE` at the repository root).
- Privacy policy: https://github.com/malenaaza/video-editor-skill/blob/main/PRIVACY.md
