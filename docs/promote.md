# Making the plugin better known

Ready-to-use text for the places that list Claude Code plugins. All of these have to be done by you, signed in to
GitHub or the site: some refuse anything an agent submits.

## 1. GitHub: description, topics and a release

On the repository page, click the gear next to **About** (top right):

- **Description:** `Claude Code plugin that edits talking-head Reels, TikToks, Shorts and YouTube videos on your own computer: cuts, captions, graphics, voice cleanup, retouch, ready-to-post pack.`
- **Website:** leave empty, or your own site.
- **Topics:** `claude-code` `claude-code-plugin` `claude-skills` `claude` `video-editing` `video-editor` `reels`
  `tiktok` `youtube-shorts` `content-creator` `ffmpeg` `whisper` `captions` `subtitles`
- Tick **Releases** so they show on the page.

Then **Releases → Draft a new release**: tag `v2.21.0` on `main`, title `2.21.0`, and paste:

```
Puppet videos are now their own plugin, and video-editor has a privacy page and a listing icon.

If you make puppet videos, install the new plugin once and restart Claude Code:
/plugin install puppet-video@malenaaza

Since 2.20.0: the "What can you do?" menu shows all the explaining graphics, the instructions Claude reads on
every edit are a fifth shorter, fillers are kept in the transcript however the language is written, and the
Spanish README and skill copy are up to date. Full list in CHANGELOG.md.

Install: /plugin marketplace add malenaaza/video-editor-skill
         /plugin install video-editor@malenaaza
```

Make a release for each future version, so the page shows it's maintained (directories look at that).

## 2. awesome-claude-code

https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml

Only the web form is accepted: no pull request, no command line, and it must be filled in by a person. One
recommendation at a time. The project has been public for more than 14 days and is active, which is the rule.
Their style: say what it does, no sales pitch, no "you", no emojis.

- **Name:** Video Editor for Creators
- **Category:** Plugin (or "Agent Skills", whichever the form offers for a plugin with skills)
- **Link:** https://github.com/malenaaza/video-editor-skill
- **Author:** malenaaza, https://github.com/malenaaza
- **License:** MIT
- **Description:** `Edits talking-head Reels, TikToks, Shorts and YouTube videos locally with FFmpeg and Whisper: removes retakes, pauses and filler words, adds brand-styled captions and animated graphics timed to speech, cleans and levels the voice, softens skin and blurs the background, and exports with a caption, hashtags and cover.`
- **Why it's useful** (if asked): `Turns a raw phone or camera recording into a finished short-form video in one conversation, with every cut and choice shown for approval. Detects the computer's hardware encoder and runs entirely offline after setup.`

## 3. awesome-claude-skills (ComposioHQ)

https://github.com/ComposioHQ/awesome-claude-skills, by pull request. They expect a folder with a `SKILL.md` in their
repository and a line in their README under **Creative & Media**:

```
- [Video Editor for Creators](https://github.com/malenaaza/video-editor-skill) - Edits talking-head Reels, TikToks, Shorts and YouTube videos locally: cuts retakes, pauses and fillers, adds branded captions and graphics, cleans the voice, and exports a ready-to-post pack.
```

The skill needs its scripts, so a copied `SKILL.md` alone wouldn't work. In the pull request, offer the README line
with a link to this repository, and ask whether they accept that for a plugin. Ask Claude in a session on your own
computer to prepare the fork if they want a folder too.

## 4. Directories that may find it by themselves

These index GitHub repositories that have a `.claude-plugin/marketplace.json`, which this one has. Search each for
"video editor" in a week or two; if it isn't there, look for their submit page:

- https://claudemarketplaces.com
- https://claude-plugins.dev
- https://skillselion.com

The topics from step 1 help them find it.

## 5. Posts

Lead with the before/after video at the top of the README, not the list of features. Say plainly what's tested:
it was built on Windows with an Intel laptop; Mac, Linux and NVIDIA/AMD settings are included but untested, and
reports are welcome.

**Reddit, r/ClaudeAI** (or r/ClaudeCode), and the Anthropic Discord:

> **I made a Claude Code plugin that edits my talking-head Reels for me**
>
> I film skincare videos and editing took longer than filming. So I wrote a plugin: I give Claude the raw
> recording, it transcribes it with Whisper, removes retakes, pauses and "ums", adds captions in my brand's style
> and graphics timed to what I say, cleans the voice, and exports vertical and wide versions with a caption and
> hashtags. Everything runs on my laptop with FFmpeg. It shows me the cuts before exporting and never posts for
> me.
>
> Before/after and install: https://github.com/malenaaza/video-editor-skill
>
> Built and tested on Windows with an Intel laptop; Mac/Linux settings are there but untested, so reports are
> very welcome.

**Hacker News**, title `Show HN: A Claude Code plugin that edits talking-head videos locally with FFmpeg`, and
the same text, shorter and more technical: hardware encoder detection, frame-accurate cuts, filler hunting with
several Whisper passes.

**In Spanish** (Instagram, LinkedIn, Spanish-speaking creator and AI groups):

> He hecho un plugin para Claude Code que edita mis Reels: le doy la grabación tal cual y quita las tomas
> repetidas, las pausas y los "eh", pone subtítulos con mi estilo, gráficos al ritmo de lo que digo, limpia la
> voz y me deja el texto y los hashtags listos. Todo en mi ordenador, gratis y en español.
> Antes y después, y cómo instalarlo: https://github.com/malenaaza/video-editor-skill

**A video of your own** is the strongest of all: a Reel showing a raw take and the finished edit side by side,
with "edited by Claude" and the install line in the description.
