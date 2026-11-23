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
  `[GRAPHIC]`/`[GRÁFICO]`, `[CLIP]` (the same in both), `[SHORT "Title"]`/`[/SHORT]`). `>` lines are directions to the speaker, never spoken.
- **The opening:** the first line is the hook, said within 5 seconds: the promise or the question, not a greeting.
  The intro (before the first chapter) stays under 30 seconds.
- **Chapters:** 3 to 8, each covering one idea, with short titles (under 40 characters) that viewers would search for.
- **Shorts:** mark 3 to 5 passages, each 30 to 60 seconds when said (about 75 to 150 words in Spanish or English),
  that work with no context: the first line is its own hook, no "as I said before", and it ends on a complete idea.
  Give each a title that works as the Short's hook on screen.
- **Screen recordings and graphics:** a `[SCREEN]` line before the line it illustrates, saying exactly what to show;
  a `[GRAPHIC]` line for a diagram or a list to animate. Switch between the speaker and screen or graphics every 20
  to 40 seconds, so the video keeps moving.
- **In a video about AI, show the prompts:** when the speaker says what they ask an assistant, mark it
  `[GRAPHIC] chat: <app>; prompt "..."; answer "..."` so it becomes an AI chat window (`references/graphics.md`),
  and write the line so it names the asking and the answer ("le pido a Claude que…", "y me dice…").
- **Propose the animated explanations yourself:** don't wait to be asked. In an educational video, look for the
  passages where the speaker explains how something works that can't be filmed: how parts connect (Claude, an MCP
  server and Gmail), how a request goes and comes back, the steps of a process, what talks to what. Mark one to
  three of them per video (not every passage: they lose their effect), each as a `[GRAPHIC]` line with the boxes in
  order, the arrows and the dot's trip, for example
  `[GRAPHIC] explanation: Claude 🤖, Servidor MCP 🔌, Gmail 📧; Claude -> Servidor MCP "pide"; Servidor MCP -> Gmail
  "conecta"; dot: Claude > Gmail > Claude`. Then **write the lines under it so they name each piece once, clearly,
  in the order it should appear** ("Por un lado está Claude. Por otro, un servidor MCP. Claude le pide algo al
  servidor, y este habla con tu Gmail..."): those words are what bring each box in (`say` in `explainer.json`,
  `references/graphics.md`, Animated explanations), so the animation follows the voice with no extra work. Keep a
  passage like that to 10 to 30 seconds and up to 6 boxes.
- **Propose AI clips for atmosphere, never for facts.** A clip made with an AI video generator (Google Flow by
  default, or the `AI clips:` tool in `my-setup.md`) suits what can't be filmed and doesn't need to be exact: a
  visual metaphor (data flowing, a brain made of light, a city of servers), the channel's intro scene, a short
  break in a long talking-head stretch. Never use one for anything the viewer has to read or trust: text, a
  diagram, an app's screen, a real product, a real person, numbers. Those are a `[SCREEN]`, an animated
  explanation, a chat window or a tool card, which are always exact. Mark one to three per video, each on its own
  line before the line it covers: `[CLIP] <file-name>: <prompt>`, for example
  `[CLIP] red-de-luz: slow push-in through a dark space full of glowing threads of light connecting small nodes,
  soft blue and teal light, shallow depth of field, cinematic, 16:9, no text, no people`. The file name is short,
  lowercase, with hyphens, and unique in the video: the user saves the clip under that name. Write the prompt in
  English (generators follow it best), in one sentence that says the subject, the camera move, the light and the
  look, and always ends with the shape (16:9 for YouTube, 9:16 for a vertical-only video), "no text" (generators
  write garbled letters) and "no people" unless a person is the point. End every prompt in a video with the same
  look words, from the brand's `AI clip style:` line when it has one, so the clips match each other. A clip covers
  4 to 8 seconds of voice: write the line under it so that much of it can play over the clip.
- **The end:** the takeaway in one line, then the call to action.

Show the user the script and adjust it with them before they film. Point out the animated explanations you
marked, in one line each ("At 'cómo funciona un MCP' an animation: Claude, the MCP server and Gmail with arrows"), so
they can drop or add one. Do the same for the AI clips ("At 'una red de neuronas' an AI clip: threads of light
connecting nodes"). The first time a script has one, ask once which generator they use, and save it in the
`AI clips:` line of `my-setup.md` (Google Flow has free daily credits). Then ask once, for the brand, whether to
keep a look for every clip (for example "soft blue and teal light, dark background, cinematic"), and save it in the
brand's `AI clip style:` line.

## 2. The shot list

Write `shotlist.md` next to it, for filming in one sitting:
1. **Camera:** every spoken line in order, numbered, with the `>` directions. Remind the user to repeat a line from
   its start when they trip (the last complete take is kept), to film horizontal in 4K with the speaker in the middle
   third if Shorts will be cut (Rule 6), and to pause a second before each line.
   When the user films some parts with a second camera (an iPhone for the hook, the ending or a side view), add
   which camera films each line, `[main]` or `[iPhone]`. Filming at the same time, the `[iPhone]` marks say when to
   have it recording; in separate takes, group the iPhone lines so the phone is set up once. Two or three parts per
   video are plenty. The settings to match are in `references/cameras.md`, Two cameras.
2. **Screen recordings:** every `[SCREEN]` note as a separate short clip to record, with the tips in Rule 6
   (bigger text, Do Not Disturb, nothing private on screen).
3. **Graphics:** the `[GRAPHIC]` notes, made later in the edit.
4. **AI clips to generate:** every `[CLIP]` as a numbered item with its file name, the prompt ready to paste, the
   shape and the length (8 s, the usual longest; it's cut to fit later). Tell the user to make two or three versions
   of each and keep the best, to download it as MP4 at the best quality the plan allows, and to save it in the
   project's `clips/` folder (or next to the recording) under the file name given, for example `red-de-luz.mp4`.
   Two notes, once per video in one line each: when a clip looks real (a realistic person or place), YouTube asks
   for it to be labelled as altered or synthetic content when uploading; and if the channel earns money, check that
   the generator's plan allows commercial use.

**Teleprompter.** Don't assume one. If `my-setup.md` has no `Teleprompter:` line, or it says `not asked yet`, ask
once when you show the first script: "Do you read from a teleprompter when you film? On which camera?" Save
`none`, `on the main camera` or `on every camera`. When they use one, also write `teleprompter.txt`, plain text that
any teleprompter app can open:
- only the words they say, in order, one line per paragraph, with a blank line between lines;
- no markers (`[CHAPTER]`, `[SCREEN]`, `[SHORT]`...) and no numbers: they would be read out;
- the `>` directions on their own line, in capitals and brackets, so they stand out and aren't read: `(LOOK AT THE
  CAMERA, SMILE)`, in the script's language;
- a line `(PAUSE)` where a chapter ends, so there's a natural place to stop and restart.
The teleprompter holds every line the user reads from it. Ask where the second camera points:
- **from the side, while they keep reading the main camera's teleprompter** (the usual way): every line goes in
  `teleprompter.txt`, and an `(IPHONE)` line before each `[iPhone]` passage reminds them to have it recording;
- **at them, as a second front-on angle without a teleprompter:** those lines are said into the iPhone, so put them
  at the top of the shot list to learn instead (they are short);
- **at them, with a teleprompter on each camera:** write `teleprompter-main.txt` and `teleprompter-iphone.txt`.

## 3. After filming: follow the script

Transcribe the camera recording (Rule 3), then in the build folder:

```
python -I <skill>/scripts/scriptcut.py script.md <transcript.json> --cuts cuts.json
```

With a second camera filming at the same time, run this on `angles.mov` (`references/cameras.md`), which has every
line. In separate takes, run it on each camera's recording: the `[iPhone]` lines are expected to show as not said in
the main camera's report, and the other way round, so only report lines missing from both.

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
  **AI clips** (`"kind": "clip"`; the file name is the text before the colon): find each one in `clips/`, and say
  in one line which are missing before going on (the edit can go ahead without them and add them later). Make each
  one match the camera first: `python -I <skill>/scripts/conform.py clips/<name>.mp4 --like <camera recording>`
  (same frame rate, size and colour tags; `references/cameras.md`). Then cut it into the wide edit like a screen
  clip, starting at the words in `before`, for the length of the voice it covers (at most the clip's own length,
  usually 4 to 8 s), with the speaker's voice over it and the clip's own sound left out, unless the user wants it
  quiet underneath. Don't zoom, retouch or blur it, and keep captions on top of it as everywhere else. Look at a
  frame from each placed clip, because a generated clip can carry stray letters or an odd detail: if one does, tell
  the user and offer to drop it or to place a different version.

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
