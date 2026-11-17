# The skill moved

The video-editor skill now lives in `plugins/video-editor/skills/video-editor/` and is installed as a Claude Code
plugin. This folder only keeps `VERSION`, so copies installed the old way still learn about new versions.

To switch, say "update my video-editor skill" (or "actualiza mi skill") in Claude Code: it installs the plugin and
removes the old copy, with a backup. Or run:

    claude plugin marketplace add malenaaza/video-editor-skill
    claude plugin install video-editor@malenaaza

Your settings in `~/.video-editor/` are not touched.
