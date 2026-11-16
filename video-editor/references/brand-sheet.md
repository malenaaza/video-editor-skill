# The brand sheet

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

**Brand sheet:** the first time you edit for a brand, check its `Brand sheet:` line in `my-setup.md`. If it's empty or says "not asked yet", ask the user **once**, alongside the Rule 1 questions: "Do you want a brand sheet for this brand? It's one page showing your fonts, colors and caption styles, handy to share with anyone who makes graphics for you." Then write the answer in that brand's section, so you never ask again:
- Yes: ask "What should I base it on?" and let the user pick one or more of these:
  1. **An account to learn from** (Instagram, TikTok, YouTube): study its last 4 or 5 videos frame by frame. Download them with `yt-dlp` into `<work folder>/brand-sheets/<brand>/study/`, for private study only, and measure the fonts (matched by eye, so say it's a close match), title and caption sizes, outlines and placement, colors sampled from the footage, shot length, words per minute, pauses, loudness, and how each video opens, uses cutaways and ends. Borrow only the format, type and pacing. Never reuse that creator's lines, titles or footage, and put a "Keep it yours" section on the sheet that says so. Offer to delete the downloaded videos once the sheet is done.
  2. **A Canva brand kit:** if a Canva connector is available, read the kit with it (list the brand kits, then the kit's colors, fonts and logos). If Canva isn't connected or the kit can't be read, ask the user to export it or send a screenshot. Use the exact hex codes and font names from the kit. If a font isn't free to install, say so and suggest the closest free one.
  3. **The brand's website:** the user gives the link. Read the page and its stylesheets for the main colors, fonts and logo, and its text for the tone of voice. Show the user what you found before using it, because a site can mix several looks. Download the logo only if the user confirms it's theirs to use.
  4. **Only what's saved:** use the settings already in that brand's section.

  When more than one source is chosen, the brand's own sources (Canva kit, website, saved settings) decide the colors, fonts and logos. An account study only supplies format and pacing. If two sources disagree, ask the user which to keep. Save any new colors, fonts or logos to the brand's section too, so the skill and the sheet match.

  Make the sheet a single `index.html` page in `<work folder>/brand-sheets/<brand>/`, with no outside links, so it opens offline. Show the fonts (rendered in the font itself), colors (swatches with hex codes and what each is for), the title, caption and handle or logo styles drawn the way they appear on video, the end card, pacing, and a "Your edit settings" section (speed, loudness, color grade, retouch, blur, zooms, emojis, ending), plus a sample frame from the first video and a "last updated" date. Say on the sheet where each part came from. Mark anything no source covers (for example a title style) "not set yet" and ask about it once. Open the sheet in the browser for the user to check. Write `Brand sheet: <path>` and the sources used in the brand's section.
- No: write `Brand sheet: not wanted (<date>)`.

Whenever a brand setting changes in `my-setup.md`, update that brand's sheet in the same turn and change its "last updated" date.
