# Privacy

This covers the **video-editor** and **puppet-video** plugins in this repository.

## What stays on your computer

Everything you edit. Your videos, their audio, transcripts, frames, masks and finished exports are processed and
saved on your own computer, in the work folder you choose at setup. Your settings (hardware, brands, style choices,
word fixes) are saved in `~/.video-editor/`. Transcription, face tracking, noise removal and the puppet voices run
locally. Nothing is sent to the author, and the author runs no server.

What you write to Claude, and the files Claude reads to help you, go through Claude itself, under Anthropic's own
terms and privacy policy.

## When it connects to the internet

- **Installing tools**, with your OK: Python packages (PyPI), FFmpeg and yt-dlp (your system's package manager),
  Remotion (npm), and for puppet videos Piper voices and Rhubarb Lip Sync.
- **Model files**, downloaded once: speech recognition (Whisper, from Hugging Face), face and hand tracking (Google's
  MediaPipe models), noise removal and, if you make covers with products, the cutout model.
- **Update check**, only if you say yes when asked: at most once a week it reads the skill's version number from
  this repository on GitHub. It sends nothing about you.
- **Downloading a video** only when you give it a link.
- **Hashtags**: Claude searches the web for your video's niche and topic.

## Reports to the author

If you choose to report a problem or suggest an idea, the skill writes the report on your computer, removes your
home folder path and user name, shows it to you, and gives you a link to a pre-filled GitHub issue (or an email).
Nothing is sent unless you send it yourself. Frames, audio and video are never included. GitHub issues are public.

## Contact

Questions: open an issue at https://github.com/malenaaza/video-editor-skill/issues
