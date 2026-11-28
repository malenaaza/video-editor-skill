# A brand's defaults: zooms and look

Read the first time a brand's `Zooms:` or `Look:` lines in `my-setup.md` are empty (SKILL.md, Rule 5).

1. If the brand's `Zooms:` line is empty, ask **once**: "Between shots, should I keep the picture still (straight cuts), or add small punch-in zooms (about 8%) every other shot for energy? I'll skip any zoom that would cut off your head." Save the answer in `Zooms:`. If they choose zooms, follow the zoom check in SKILL.md, Rule 10.
2. If the brand's `Look:` lines are empty, ask **once**, after transcription so you have their footage. These are hard to judge from words, so show before/after frames from their own video, side by side, each labeled:
   - **Color:** natural (no grade), or a gentle boost (`eq=contrast=1.06:saturation=1.15:gamma=1.02`) for footage that looks dull indoors. Skip this for Log footage, which gets only its LUT (SKILL.md, Rule 6).
   - **Skin softening:** never, only when asked, or on every video. Show it on a face close-up at the default level.
   - **Beautify:** off, light, medium or strong (a bit more smoothing, a soft glow, brighter under-eyes and eye whites; no makeup, no reshaping). Show a frame at each level. Suggest `off` or `light` if the brand reviews base products or skincare (`references/retouch.md`).
   - **Teeth whitening:** never, or only when asked.
   - **Background blur:** never, only when asked, or on every video. Show the default `gblur=sigma=7`.

   Ask in one message, for example: "Here's how your video looks with each option. For [brand], which should I use by default? (1) Color: natural or boosted. (2) Skin softening: never, on every video, or only when you ask. (3) Beautify: off, light, medium or strong. (4) Teeth whitening: never or only when you ask. (5) Background blur: never, on every video, or only when you ask." Save the answers in the brand's `Look:` lines. Defaults set to "every video" are applied without asking again; "only when asked" waits for the user. If they want more or less of something, adjust one step at a time and save the new level.

   Show frames on a small sample (a few seconds, or single frames) rather than rendering the whole video. Building masks for the full video is slow, so don't run it before they've chosen.
