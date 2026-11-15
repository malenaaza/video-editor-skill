# Removing fillers, hums and hidden repeats

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

Read this when the user wants fillers removed, or when handling noise fills the pauses. Cuts found here go into `cuts.json` as `remove` ranges (source seconds, the transcript's clock); then rebuild the plan with `cutplan.py build` (Rule 3). `cutplan.py to-source` and `findfill.py` turn times in the cut back into source times.

- **Fillers:** if the user wants fillers removed, remove every one: "um", "uh", hums, drawn-out "and...", and repeats like "and how... and how". Whisper `medium` leaves most of them out of the transcript, so find them with a second pass with the `small` model and a prompt that invites fillers in the video's language (`<skill>/scripts/filler_prompts.py` has prompts for several languages; add one if needed). Run it on the whole cut, before the first export, not after the user complains:

  ```
  <speech python> -I <skill>/scripts/fillers.py --language <code> audio.wav transcript/fillers.json
  ```

  Map its word times back to source times with `cutplan.py to-source`, then cut from the end of the word before each filler to the start of the word after it. Keep one copy of a repeated word. Pieces between pauses with no words in them are usually hums, so remove those too. Ordinary words that are sometimes fillers ("so", "like", "well") stay when they carry meaning. The two transcripts time words differently, so after cutting, check that no kept word dropped out of the captions, and add those back by hand. Re-run the `small` pass on the finished video to confirm nothing is left. Transcribing shot by shot with `medium` is far too slow.

  Fillers often sit right against the next word with no silence between, so Whisper's times alone cut into words. Helpers:
  - `findfill.py`: maps times in the finished video to edges in the source, from a 10 ms level map. Run from the build folder, where `plan.json` is.
  - `checkcuts.py --language <code> a1 b1 ...`: for each cut, transcribes the removed piece (must be only the filler) and the 2 s before and after joined (every word must be whole). Tighten and recheck until both pass.
  - A drawn-out "and": if the sentence still works, shorten it to about 0.15 s. A filler that the `small` model times as 0.5 s is often a normal word plus the next one, so check the level map first.
- **Fillers glued onto words:** a user can still hear "ehhh" after both passes come back clean, because Whisper merges a filler that touches a word into that word ("y ehh prefiero", a hum before "menos"). Before the first export, run the short-window pass on the cut voice: `<speech python> -I <skill>/scripts/hunt_fillers.py --language <code> cut.wav hunt.json`. It transcribes 6 s windows every 3 s with the filler prompt and without carrying text between windows, and lists each filler and each word longer than 0.6 s. For each hit, map it to the source, read the level map (a filler is a flat, steady stretch), and test the cut as with `checkcuts.py`: the removed piece must transcribe as only the filler, and the joined phrase must keep every word whole. Leave a hit alone if every cut clips a word, and tell the user where it is.
- **Over-long words hide repeats and hums:** Whisper often stretches one word over a repeat, a hum, or the word before it, so the duplicate never shows up in either transcript. Before the first export, list every word longer than about 0.8 s in either transcript (except naturally long words), and check each one:
  1. Re-transcribe those 2–3 s alone with the `small` model and a prompt that invites the suspected repeat or hum.
  2. Read a 50 ms level map for extra syllables or a steady stretch.
  3. If still unclear, run the mouth check below. Closed lips during steady sound means a hum.
  4. Re-transcribing the halves separately with `medium` settles which word is where. Sometimes a suspected hum is just a long word, so check before cutting.

  When you keep the second take of a repeat, move the merged word's caption timing to that take, and make sure caption rescue for words that cross a cut doesn't bring back removed words.
- **Restarts the transcripts miss:** both models smooth over broken words like "deo-, deodorant". Before the first export, re-transcribe each sentence that holds a product or brand name with a prompt that invites the restart, and read the level map for an extra dip in the middle of the word.
- **Speech detector:** when handling noise fills the pauses (hauls, unboxings), silencedetect finds few gaps. Use Silero VAD from faster-whisper (`faster_whisper.vad.get_speech_timestamps`, threshold 0.5, min silence 120 ms; if its audio decoder fails, load the wav with `wave` and numpy) to get the speech regions to keep. Pad them as above, subtract the filler and retake cuts, then trim remaining pauses of 0.2 s or more.
- **Mouth check:** `<face python> -I <skill>/scripts/retouch/mouth.py <video> <face_landmarker.task>`. If the speaker's mouth isn't moving, they aren't saying anything. It measures the inner-lip gap per frame (landmarks 13 and 14, divided by face height so zooms don't change it) and lists stretches over 0.4 s where the mouth stays closed or still. Cut those even if there's sound there, but compare each flag with the transcript first: glossy lips can make the gap read nearly closed during normal speech. Stretches with no face detected (a product covering it, looking away) aren't counted, so check those against the transcripts. Spot-check flagged frames so a short pause mid-sentence isn't cut too tight.
