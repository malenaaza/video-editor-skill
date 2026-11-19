# Puppet videos: format, voices, installs and tips

Part of the puppet-video skill. `<skill>` is the folder that holds its SKILL.md.

## The dialogue format (`dialogue.md`)

```
# At the café (a comment: lines starting with # aren't said)
[Lola] voice=en_GB-cori-medium look=lola
[Max] voice=en_GB-alba-medium look=max colour=#7FD1AE
Lola: Hi! Could I have a flat white, please? | ¡Hola! ¿Me pones un café con leche, por favor?
> Max: happy
Max: Of course. Anything else? | Claro. ¿Algo más?
> Lola: thinking
Lola: Hmm... a croissant, too. | Mmm... un cruasán también.
> pause 0.5
Max: That's four pounds fifty. | Son cuatro libras con cincuenta.
```

- `[Name]` lines come first: `voice=` a Piper voice name (below); `speaker=` for a voice with several speakers
  (sharvard: `M` or `F`); `look=` `lola`, `max` or `pixel`; `colour=` recolours the character (brand palette).
- `Name: text` is one turn. After ` | `, a translation, shown under the captions with `"showTranslation": true`.
- `> Name: happy` (or `surprised`, `thinking`, `sad`, `neutral`; Spanish `feliz`, `sorprendido/a`, `pensando`,
  `triste`, `normal`) sets that character's expression from their next turn. `> pause 0.8` (or `pausa`) adds
  silence. Any other `>` line is a note and isn't said.
- Write numbers, prices and abbreviations as they should be said ("four pounds fifty", not "£4.50"): the voice
  reads exactly what's written, and the captions show exactly what's written.

## Writing good dialogues

- **Short turns:** one idea per turn, 4 to 15 words. A turn over 2 lines of captions is too long.
- **For students:** a real situation (a café, a hotel, an interview, a doctor), the level asked for (A1: present
  simple and everyday words; B1: past and future, phrasal verbs; C1: idioms, nuance), one teaching point per video
  (a phrase, a structure, a false friend), and the point repeated at least twice in the dialogue. 20 to 45 seconds
  for Reels and TikTok.
- **For explainers (the robot):** the character asks the question the viewer has ("¿Qué es un prompt?") and answers
  in one or two turns, or reacts to the presenter. 10 to 20 seconds inside a longer video.
- **Expressions:** change them at moments that matter (surprise at the twist, thinking before the answer), not on
  every turn.
- **Speed:** `--speed 0.9` for A1–A2 students, 1.0 otherwise; `--gap 0.5` gives listeners more time between turns.

## Voices

Piper voices run on the computer, free. Each has its own license (from its MODEL_CARD on
huggingface.co/rhasspy/piper-voices); `dialogue.py` writes the ones it knows into `credits.txt`, with the credit
line to put in the description when the license asks for one.

| Voice | Language | Sounds | License | Credit needed |
|---|---|---|---|---|
| `es_ES-davefx-medium` | Spanish (Spain) | male | CC0 | no |
| `es_ES-sharvard-medium` (`speaker=M` or `F`) | Spanish (Spain) | male and female | CC BY 3.0 | yes |
| `es_ES-carlfm-x_low` | Spanish (Spain) | male, lower quality | public domain | no |
| `en_GB-cori-medium` | British English | female | CC BY 4.0 | yes |
| `en_GB-alba-medium` | British English (Scottish) | female | CC BY 4.0 | yes |
| `en_GB-northern_english_male-medium` | British English (northern) | male | CC BY-SA 4.0 | yes |

Others exist (en_GB alan, jenny_dioco, vctk, and more), but their licenses point to other pages: read them before
using one, and add it to the table in `dialogue.py` once checked. For a school, a neutral southern English accent
(cori) is a safe default; mention the accent of each voice when offering them.

**Download a voice** into `~/.video-editor/voices/` (two files: `.onnx` and `.onnx.json`):
```
python -m piper.download_voices en_GB-cori-medium --data-dir ~/.video-editor/voices
```
or from huggingface.co/rhasspy/piper-voices, path `<lang>/<lang_COUNTRY>/<name>/<quality>/`.

## Install

- **Piper:** `pip install piper-tts` into the Python the skill uses for speech (the video editor's `<speech python>`),
  or a separate one; pass it with `--piper-python`. Piper is GPL-licensed software that the skill runs as a separate
  program; the voices it makes are covered by each voice's own license above.
- **Rhubarb Lip Sync** (MIT): download the zip for the system from
  github.com/DanielSWolf/rhubarb-lip-sync/releases (Windows, macOS, Linux) and unpack it into
  `~/.video-editor/tools/`. `dialogue.py` finds it there or on the PATH. Without it, mouths open and close with the
  loudness only, which looks rougher; say so if it's missing.
- **Remotion** and the editor's templates: as in the video editor's `references/graphics.md`.

## Timing and look

- `dialogue.py` trims each turn's silence, adds 0.4 s before the first turn, `--gap` between turns, any `pause`, and
  0.8 s at the end, and levels the voice to -14 LUFS.
- Rhubarb runs with the turn's text for English (more accurate) and its phonetic recognizer for other languages.
  Each turn takes about 1 to 2 seconds to analyse.
- In `Puppet.tsx`: vertical videos put the characters' feet at 72% of the height, so captions at `--margin-v` 300
  and a translation under them fit below; two characters face each other, and the one speaking leans in while the
  other looks at them. Blinks come every 3 to 5 seconds, at different moments for each character.
- A new character is a new component in `Puppet.tsx` with the same props (mouth shape, blink, look direction,
  expression) and all nine mouth shapes (`A`–`H`, `X`); add it to `LOOK_COMPONENTS` and to `LOOKS` in
  `dialogue.py`.
