# Problems and wishes: logging them and reporting to the author

Read when the user says something in a result looks or sounds wrong, or wishes the skill did something it doesn't (SKILL.md, Rule 0).

## A problem in a result

**When the user says something looks or sounds wrong in a result** ("the skin looks bad at 3:32", "the product is blurred", "a word got cut"), a problem the skill itself should handle and not a preference, also log it so it can be fixed in the skill later. Keep fixing the video in front of you as usual; don't edit the skill's own files during an edit.

1. Save the frame (or a few seconds of audio) at the moment they name, in `<work folder>/<project>/issues/`: `ffmpeg -ss <time> -i <video> -frames:v 1 <date>-<n>.png`. Add the matching mask or stage if it helps (for example the frame of `skin.mkv` at that time). These show the user's face and voice: keep them on their computer, never in the repository.
2. Append an entry to `~/.video-editor/skill-issues.md` (create it if it's missing):

```
## <date> · <video name> · <time in the video>
- Saw: <the user's own words>
- Step and settings: <which step of the build order, and the retouch.json and my-setup.md lines in force>
- Files: <the saved frame, the build folder>
- Suspect: <a guess, if you have one, labelled as a guess>
- Status: open
```

3. Tell the user in one line that it was logged. When a session fixes the skill, it sets `Status: fixed in <pull request or commit>`.
4. Offer once, in one line: "Do you want to send this to the skill's author, so it gets fixed for everyone?" If yes, see Reports to the author below.

## A wish for the skill

**When the user wishes the skill did something it doesn't,** or worked differently in a way no setting covers (an improvement, not a preference for their own videos), say so honestly and offer the same: "Do you want to suggest it to the skill's author?" Preferences for their own videos still go in `my-setup.md`.

## Reports to the author

**Reports to the author:** write the report in the user's language to a text file in the project folder: what they saw or want, in their own words; the minute in the video if there is one; the step of the build order; the settings in force; any error message. Then run `python -I <skill>/scripts/report.py --kind <bug|idea> --title "<short title>" --details <that file>`. It adds the skill version and system, replaces the home folder path and the user name, saves the report in `~/.video-editor/reports/`, and prints a link that opens an issue on the skill's GitHub page already filled in (they click Submit; it needs a free GitHub account) and, if the author set an address in `<skill>/support.json`, an email link with the same text. Show the user the report first, then give them the links: GitHub first, the email if they have no GitHub account. Never send anything yourself, and never include frames, audio or video: issues are public. If they want to share a frame, they look at it and attach it themselves.
