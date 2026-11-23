# Several videos at once

Read this only when the user brings **two or more videos to edit in the same request** ("edit these three", a folder of
recordings), or when the user accepts the one-line batch offer in SKILL.md ("Offer a batch once, at the start"). One video at a time is the normal flow and nothing here changes it: don't offer a batch when the user says there is only one video.

The user stays the director. A batch only runs the usual build order for each video side by side; every judgment call
(cut plan, openings and endings, extras, the final export) still waits for them.

## Before starting

1. **Ask everything once, up front, in one message,** for all the videos together: brand, platform, openings and
   endings, extras, fillers (Rule 1 and the extras suggestions). Offer the saved defaults first. Agents can't ask the
   user anything mid-run, so a question left out here becomes a guess.
2. **One project folder per video** (Rule 2), each with its own `project.md`, a copy of its original, and its own
   `plan.json` and renders. Two videos never share a working file.
3. **Run the checks that need the user once, not per video:** first-time setup, the footage check for a new camera,
   and the weekly update check. Do them before any agent starts.

## Running

- **Two videos at a time at most.** Transcription, retouch masks and renders use the same CPU or GPU, and more
  jobs at once usually make each one slower. Before the first batch on a computer, say so and offer to time two videos
  to choose a number. Never go above what `my-setup.md` and the Power section of `references/setup.md` allow.
- **One agent per video.** Give each agent: the video's folder, the answers from step 1, the path to `<skill>`, the
  line "follow SKILL.md up to the cut plan and the draft export, then stop and report", and the instruction to write
  only inside its own project folder. Use agents on a smaller model (Haiku) only for mechanical work: probing clips,
  collecting reports, running the export checks. Cut decisions stay with the main session's model.
- **Agents never write shared files.** `~/.video-editor/my-setup.md`, `~/.video-editor/skill-issues.md` and the skill
  folder are changed by the main session only, one at a time. An agent that finds a problem returns it as text.
- **A failed video stops alone.** Report its error and carry on with the others.

## Review and finish

1. When the agents report, show **all cut plans and draft exports in one list**, with each video's name, the same
   short questions as a single edit (Rule 3), and the checks from Rule 10.
2. The user approves or changes each video. Changes go back to that video's agent.
3. Only then run the final export and the ready-to-post pack for each (Rules 6 and 11), two at a time.
4. The main session then writes any feedback notes to `my-setup.md` and logs problems to `skill-issues.md` (Rule 0),
   and checks that a change asked for on one video didn't contradict what was done on another.

If agents aren't available in this session, or the user prefers it, edit the videos one after another with the same
answers collected in step 1.
