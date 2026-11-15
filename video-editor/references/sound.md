# Sound: voice cleaning, leveling and sound effects

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

## Clean the voice

Background noise (fans, air conditioning, fridge hum, street noise) and mains hum stay under the words unless they're removed. Use `<skill>/scripts/voice/clean_voice.py`, run with any Python that has numpy (the `speech` environment works).

1. **Measure** each original recording, before any cuts, while it still has its pauses: `python -I clean_voice.py measure <original>`. It gives the noise floor, the gap between speech and noise, any mains hum (50 or 60 Hz) and a suggested strength: none (gap 45 dB or more), light, or strong (gap under 30 dB).
2. **Ask once per brand,** the first time a recording needs cleaning, and save the answer in the brand's `Voice cleaning:` line: "Should I remove background noise and polish your voice? **Automatic** (suggested: only when a recording needs it, at the strength it needs), always light, always strong, or never?" Polish is part of it: rumble cut, gentle evening out of loud and quiet words, softer "s" sounds and a little clarity. If the user only wants noise removal, add `--no-polish`.
3. **Clean** the cut voice track, after cuts and speed-up and before leveling: `python -I clean_voice.py clean <voice.wav> <voice-clean.wav> --strength <light|strong> [--hum <50|60>]`, with `--hum` when the measure found hum. With "automatic", skip cleaning when the suggestion is none, but still offer the polish once. The script picks the best engine installed and says which it used. If it reports that an engine made the voice quieter, it already retried more gently or fell back; mention it to the user.
4. **Check:** compare the "Before" and "After" lines it prints: the gap should grow and the hum should be gone. Transcribe the cleaned voice with `medium` and compare it with the transcript of the uncleaned cut: if any word changed or dropped, clean again one step lighter (strong, light, then `--no-polish` or no cleaning) and say so. You can't hear the result, so ask the user to listen to the first cleaned video and say if the voice sounds too processed (hollow, watery, robotic) or still noisy, then save the answer in `Voice cleaning:`.
5. Clean only the voice: sound effects are mixed in afterwards (Sound effects below), and never run cleaning on music.

## Level each voice

If a video mixes voices (an AI voice and the user, an off-camera interviewer), level each one on its own. Use the transcript to mark which time ranges belong to which voice, and run `loudnorm` on each separately (two passes for accuracy), with the brand's loudness target from `my-setup.md` (default `loudnorm=I=-14:TP=-1:LRA=11` for social video). Join them, then verify with `ebur128` that the voices match within about 1 LU. Never cut an off-camera voice's pauses as silence.

## Sound effects

Add these when the user asks; don't ask them to supply sounds.

- **Source:** `<skill>/scripts/sfx/`: `pop.wav`, `whoosh.wav`, `sparkle.wav`, `cash.wav`. They were generated with FFmpeg and are free to use. Don't download music or effects unless the user asks and the license allows it.
- **Where:** `pop` on each emoji and handle pop, `whoosh` just before a zoom or end card (start about 0.15 s early so it peaks on the cut), `sparkle` on the title and handle, `cash` on money moments.
- **Mix:** copy `sfx-mix-example.txt` and change the `adelay` times (milliseconds), the number of `asplit` outputs, the `amix` input count, and `whole_dur`. Volumes of about 0.36 to 0.54 sit under the voice; 0.20 to 0.30 was too quiet in testing. Finish with `alimiter=limit=0.89:level=false`.

```
ffmpeg -i voice-final.wav -i pop.wav -i whoosh.wav -i sparkle.wav -i cash.wav -/filter_complex sfx-mix.txt -map "[a]" -ar 48000 -c:a pcm_s16le voice-sfx.wav
```

- **Build order:** clean the voice and level it first, mix in the effects, then mux with `-c:v copy`.
- **New sounds** with `aevalsrc`: use `gt(t,0.08)` instead of `t>0.08`, which FFmpeg rejects.
- **Check:** confirm loudness with `ebur128` and transcribe the opening with `medium`, with and without effects. Speech must stay the same. You can't hear the mix, so ask the user to listen and say if the effects are too loud or quiet.
