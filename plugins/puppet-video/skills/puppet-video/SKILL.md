---
name: puppet-video
description: Makes short animated videos where illustrated adult characters (drawn in code) say a script with a free voice made on the user's computer, with lip-sync, captions and optional translations. Use when the user wants a video with no one on camera, an animated character or puppet, a dialogue between two characters, a talking robot or helper for an explainer, or a listening or conversation video for language students, in any language (for example "make a puppet video", "vídeo con muñecos", "un diálogo animado para alumnos de inglés", "que lo diga el robot"). Not for editing footage the user filmed: that's the video-editor skill.
---

# Puppet videos

You make short animated videos: one or two characters, drawn in code, say a script with a synthetic voice made on
the user's computer (Piper), with mouth shapes matched to every sound (Rhubarb Lip Sync), blinking, breathing, and
leaning in when they talk. Captions, graphics and the export come from the video-editor skill, a separate plugin
from the same marketplace.

In this file `<skill>` is this folder and `<editor>` is the video-editor skill's folder: the folder of its
`SKILL.md`, as Claude Code loaded it. If it isn't loaded, look for it next to this folder (`<skill>/../video-editor`,
a copy in `~/.claude/skills/` or a clone of the repository), then under `~/.claude/plugins/` (a
`video-editor/skills/video-editor` folder with a `VERSION` file; the highest version if there are several). If
there is none, ask the user to install it, `/plugin install video-editor@malenaaza`, restart Claude Code, and stop
until they have.
Read `<skill>/references/puppet.md` before the first video: it has the dialogue format, the voices and their
licenses, the installs, and the timing and writing tips.

## Before the first video

1. **Setup:** the user's settings are in `~/.video-editor/my-setup.md` (made by the video-editor skill's setup;
   run that first if it's missing). Read its `Puppets:` section; if it isn't there, add it before
   `## Notes from feedback` from `<skill>/puppets-template.md`. If it's empty, install Piper and Rhubarb
   (`references/puppet.md`, Install), and ask once, saving the answers there:
   - the voices for each language (suggest the ones in `references/puppet.md`; play a sample line of each);
   - the characters (lola, a woman; max, a man; pixel, a robot), their clothes colours from the brand's palette,
     and their skin tone and hair if the user wants them to look like their audience;
   - whether to credit the voices in the description (required by some licenses: `credits.txt` says which).
2. **Whose video:** the brand comes from `my-setup.md` (colours, font, logo, end card, call to action). A video
   for a client (for example a school) uses the client's brand and contact details, and is checked by them before
   it's posted.

## Making a video

1. **The script.** Write `dialogue.md` with the user (format in `references/puppet.md`): short turns, one idea
   each, in the right language and variant (`my-setup.md`, `Languages:`). For language students: a real-life
   situation, the level they ask for (A1 to C1), and a translation after " | " on each turn when they want one.
   Show it to the user before making anything.
   **Content that teaches a language is checked by a teacher before posting** (grammar, register, the
   translation). Say so every time, and never present a translation as checked when it isn't.
2. **Voice and mouth shapes:**
   `python -I <skill>/scripts/dialogue.py dialogue.md --piper-python <python with piper-tts> --out-dir puppet`
   writes `puppet/voice.wav`, `puppet/puppet-props.json` and `puppet/credits.txt`. Use `--speed 0.9` for
   beginners. If the user records the lines instead, put them in a folder as `01.wav`, `02.wav`... and add
   `--audio-dir <folder>`.
3. **Listen check:** transcribe `voice.wav` with `<speech python> -I <editor>/scripts/transcribe.py puppet/voice.wav
   puppet/transcript` and compare it with the script. A word the voice got wrong (a name, an English word in a
   Spanish line) is fixed by rewriting it as it sounds in `dialogue.md` and running step 2 again.
4. **Caption words:** `python -I <skill>/scripts/captionwords.py puppet/puppet-props.json --transcript
   <that transcript> --out puppet/words.json`: the script's exact words with the voice's timing (Whisper rewrites
   words, which a language lesson can't show).
5. **Captions:** `python -I <editor>/scripts/captions.py puppet/words.json --on-cut --length <length from the props>
   --width 1080 --height 1920 ...` in the brand's caption style (video-editor Rule 5), with `--margin-v` at least
   300 so they sit under the characters. On the light default backgrounds use dark text (`--text-color`, or
   `"textColor"` in the WordCaptions props) or the box style; white text disappears there. Word highlight captions
   work as in the editor (`--remotion-props`, then the `WordCaptions` template).
6. **Render:** copy `<skill>/scripts/remotion/Puppet.tsx` into the Remotion project's `src` (with the editor's
   templates), register `PuppetComposition` in `src/Root.tsx`, copy `voice.wav` into `public/`, add
   `"audio": "voice.wav"` to the props (plus `bgTop`/`bgBottom` in the brand's colours, `font`, and
   `"showTranslation": true` for students), then
   `npx remotion render src/index.ts Puppet out/puppet.mp4 --props=puppet/puppet-props.json`. Overlay the captions
   with FFmpeg, then a title, logo or end card as in the video editor. Vertical 1080x1920 by default; for YouTube,
   `--size 1920x1080` in step 2 (it sets the props' size).
7. **Check:** look at frames from the start, the middle and the end: the mouth moves only on the character who is
   speaking, the captions don't cover the faces, the translation (if any) matches the line. Finish with the video
   editor's ready-to-post pack (Rule 11), and put the credit lines from `credits.txt` in the description.

A puppet clip inside a YouTube video (the robot asking a beginner's question): make it as above in the video's
size, then cut it into the edit like any other clip.

## Never

- Never make a character that copies an existing one (a famous puppet, a cartoon, a mascot), or use a voice that
  imitates a real person. The three characters here are original; new ones must be too.
- Never publish a voice whose license isn't checked (`credits.txt` says "NOT CHECKED"): read its MODEL_CARD first.
- Never post language teaching material that a teacher hasn't checked.
