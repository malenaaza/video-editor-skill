# Script first (YouTube and longer videos)

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

Read this when the user asks for a script, or brings one, for a video they're going to film. The script is the plan
for everything that follows: Claude writes it with markers, the user films it, `scriptcut.py` keeps the right take
of every line, and the markers become the chapters and the Shorts.

## 1. Write the script

Ask only what's missing: the topic, who it's for, the length (8 to 12 minutes is typical for a YouTube tutorial),
and the call to action. Write in the language and variant in `my-setup.md` (`Languages:`), for example Spanish from
Spain ("vídeo", "ordenador", "vosotros"), in the brand's voice (Rule 5). Research any fact, tool, price or feature you
mention, and don't state what you couldn't check.

Save it as `script.md` in the project folder (never overwrite an existing one), in this format:

```
# Edité mis vídeos con IA: así funciona

Hola, soy Malena y hoy os enseño cómo edito mis vídeos con IA.

## [CHAPTER] Qué hace la skill
[SCREEN] Claude Code: escribir "edita este vídeo para Reels" y esperar el resultado
[SHORT "La IA que me ahorra dos horas"]
Le pido a Claude que quite las pausas y los errores.

Y en dos minutos tengo el vídeo listo.
[/SHORT]

## [CHAPTER] El resultado
> mirar a cámara, sonreír
Este es el resultado final. ¿Qué os parece?
```

- **One paragraph per spoken line,** with a blank line between. Short sentences, said the way the speaker talks, not
  written prose: if a line is hard to say in one breath, split it.
- **Markers on their own lines,** in English or Spanish (`[CHAPTER]`/`[CAPÍTULO]`, `[SCREEN]`/`[PANTALLA]`,
  `[GRAPHIC]`/`[GRÁFICO]`, `[SHORT "Title"]`/`[/SHORT]`). `>` lines are directions to the speaker, never spoken.
- **The opening:** the first line is the hook, said within 5 seconds: the promise or the question, not a greeting.
  The intro (before the first chapter) stays under 30 seconds.
- **Chapters:** 3 to 8, each covering one idea, with short titles (under 40 characters) that viewers would search for.
- **Shorts:** mark 3 to 5 passages, each 30 to 60 seconds when said (about 75 to 150 words in Spanish or English),
  that work with no context: the first line is its own hook, no "as I said before", and it ends on a complete idea.
  Give each a title that works as the Short's hook on screen.
- **Screen recordings and graphics:** a `[SCREEN]` line before the line it illustrates, saying exactly what to show;
  a `[GRAPHIC]` line for a diagram or a list to animate. Switch between the speaker and screen or graphics every 20 to
  40 seconds, so the video keeps moving.
- **The end:** the takeaway in one line, then the call to action.

Show the user the script and adjust it with them before they film.

## 2. The shot list

Write `shotlist.md` next to it, for filming in one sitting:
1. **Camera:** every spoken line in order, numbered, with the `>` directions. Remind the user to repeat a line from
   its start when they trip (the last complete take is kept), to film horizontal in 4K with the speaker in the middle
   third if Shorts will be cut (Rule 6), and to pause a second before each line.
2. **Screen recordings:** every `[SCREEN]` note as a separate short clip to record, with the tips in Rule 6
   (bigger text, Do Not Disturb, nothing private on screen).
3. **Graphics:** the `[GRAPHIC]` notes, made later in the edit.

## 3. After filming: follow the script

Transcribe the camera recording (Rule 3), then in the build folder:

```
python -I <skill>/scripts/scriptcut.py script.md <transcript.json> --cuts cuts.json
```

It keeps the last take that says at least 80% of each line, removes the other takes and the false starts (two or
more words, then a restart), and writes `script-report.md`. Read the report and tell the user, briefly:
- **lines not said** (they record them, or you rewrite around them);
- **incomplete takes** (check the line still makes sense);
- **talk not in the script:** it's kept until the user decides. An ad-lib can be the best moment; a "this I'll
  record again" aside should go. Add the ones to drop to `cuts.json` as `remove` ranges, or run again with
  `--drop-unscripted` when none should stay.

Then the edit goes on as usual: `cutplan.py build` with that `cuts.json`, the fillers passes (Rule 3), retouch,
captions. `scriptcut.py` also wrote:
- `chapters.json`: run `chapters.py chapters.json` once `captions.json` exists (Rule 11, Chapters);
- `shorts.json`: the Shorts, for `shorts.py` (below);
- `edit-notes.json`: where each screen recording and graphic goes (before which words). Place the zoomed screen
  clips (`screen.py`, Rule 6) and the graphics there, while the speaker's voice continues over them where it fits.

Without a script, Claude can still write `shorts.json` after reading the transcript of the finished video: 3 to 5
moments that stand alone, each with a title, a phrase where it starts (`say`) and one where it ends (`until`).

## 4. The Shorts

On the finished long video **without** captions or titles (they're made again for the vertical size):

```
python -I <skill>/scripts/shorts.py shorts.json --video <wide video without captions> --captions captions.json
```

For each Short it writes `shorts/short-N/` with its times, its words (for vertical captions with
`captions.py --on-cut`) and `steps.txt`, the commands in order: cut the piece, reframe it to vertical
(`reframe.py`), captions, the hook title and a closing line pointing to the full video ("Vídeo completo en mi
canal"), and the final export. Follow the steps, check a frame from the start, the middle and the end of each Short,
and give each its own ready-to-post pack (Rule 11). A Short under 15 s or over 60 s is flagged: adjust its phrases.
