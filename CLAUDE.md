# Working on this repository

Two kinds of session use this repo. Keep them apart so they never overwrite each other.

- **Using the skill** (editing a video): the skill is read from `~/.claude/skills/video-editor`. Do not change skill files
  during an edit. If something is wrong, say what and where, and fix it as a separate task in the repository.
- **Changing the skill** (this repository): follow the rules below.

## Rules for changing the skill

1. **One place edits at a time.** Before editing, run `git fetch` and `git status`. If the branch is behind, `git pull` first.
   If another session (cloud or local) is working on the same branch, wait or use your own branch.
2. **Each session has its own branch.** A cloud session pushes only to its own `claude/...` branch. A session on the user's
   computer pushes to `local/<topic>`. Never push to a branch another session owns. Changes meet in a pull request, not by
   pushing to the same branch.
3. **The installed skill is the repository, not a copy.** On the user's computer `~/.claude/skills/video-editor` should be a
   link to the `video-editor` folder of a clone of this repository, so changes show up in `git status` and are never lost
   or overwritten. If it is a plain copy, say so and offer to replace it with a link.
4. **Commit small and push often**, so work is never only on one machine.
5. **Tests must pass** before pushing: `python tests/test_skill.py`. Add a test for each new script or setting.
6. **Personal data stays out of the repository:** no videos, audio, transcripts, photos or frames of the user's face,
   `my-setup.md`, or paths that contain a name. The user's settings live in `~/.video-editor/`.
7. **When asked to fix the skill without a specific problem,** read `~/.video-editor/skill-issues.md` on the user's computer
   (open entries, newest first), pick the most useful one, find the cause with the saved frame and the build folder it names,
   fix it, add a test, and set `Status: fixed in <pull request or commit>`. A cloud session can't see that file: the user
   pastes the entry and attaches the frame.
8. Update `CHANGELOG.md` and the docs in `video-editor/references/` in the same change as the code.
