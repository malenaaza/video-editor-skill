# My video setup

Filled in by the video-editor skill on first use and saved as `~/.video-editor/my-setup.md`,
outside the skill folder, so updating the skill never deletes it.
The skill reads this file before every edit. Edit it by hand any time, or ask Claude to change it.
Leave a field as `unknown` rather than guessing.

## Computer
Checked on: <date>, with `scripts/detect_setup.py`

- System: <e.g. Windows 11, macOS 15 on Apple M3, Ubuntu 24.04>
- CPU: <name, threads>
- GPU: <name, or none>
- Laptop: <yes / no>. If yes: power mode on battery <e.g. Best power efficiency / Best performance, from `detect_setup.py`>; measured slowdown on battery <e.g. 1.5x for transcription, or not measured>. Check with `detect_setup.py power` before long jobs.
- FFmpeg version: <e.g. 7.1>. Filter files: <`-/filter_complex file.txt` on FFmpeg 7+, `-filter_complex_script file.txt` on older>

## Encoders
- In-between renders, 8-bit: `<args from detect_setup.py, e.g. -c:v h264_nvenc ...>`
- In-between renders, 10-bit: `<args from detect_setup.py>`
- Hardware decoding for light copies: `<e.g. -hwaccel cuda, or none>` (measured on the first Log conversion; goes before `-i`)
- Fallback if those fail: `-c:v libx264 -preset medium -crf 10 -pix_fmt yuv420p` (10-bit: `-c:v libx265 -preset medium -crf 12 -pix_fmt yuv420p10le`)
- Final export (always): `-c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -ac 2 -c:a aac -b:a 320k -movflags +faststart`

## Tools
- Speech Python (openai-whisper, faster-whisper): `<path to python in that venv>`
- Whisper runs on: <cuda / cpu>
- Face Python (mediapipe, opencv): `<path, or not installed>`
- Face model: `<path to face_landmarker.task, or not installed>`
- Hand model: `<path to hand_landmarker.task, or not installed>`
- Cutout Python (rembg, for covers with products): `<path, or not installed>`
- Noise removal: `<path to deep-filter, or not installed>`; RNNoise model `<path to cb.rnnn, or not installed>`
- Remotion project: `<folder, or not installed>`
- Remotion license: <not asked yet / free (individual or up to 3 employees) / company license held>

## Camera and footage
- Cameras / phones: <e.g. iPhone 16 Pro with the Blackmagic Camera app, Sony ZV-E10>
- Shoots Log: <no / Apple Log / S-Log3 / ...>
- LUT for that Log: `<path to the manufacturer's Log-to-Rec.709 .cube file>`
- How to recognise the Log files: <filled in after the first Log clip, e.g. pix_fmt and color tags>

## Folders
- Work folder (never inside iCloud, Dropbox, OneDrive or Google Drive): `<e.g. ~/video-work>`
- Raw footage: `<folder, or "wherever the user points">`
- B-roll folder: `<folder with product photos and clips, logos and graphics, or "B-roll kit next to the video">`
- Finished videos: `<folder, or "next to the original">`

## Updates
- Update check: <not asked yet / weekly / never>: whether to check once a week for a newer version of the skill (`update_skill.py --weekly`; it only contacts GitHub)

## Languages
- Spoken in videos: <e.g. English, Spanish>

## Style defaults
- Remove pauses: <yes / no>
- Remove fillers: <yes / no>
- Speed-up after cutting: <1.0 = none; 1.1 to 1.15 feels brisk for social video>
- Default levels, used unless a brand sets its own (when to apply them is chosen per brand, under Brands):
  - Skin softening: `bilateral=sigmaS=9:sigmaR=0.085`, strength 0.88
  - Teeth whitening: `eq=brightness=0.19:saturation=0.13:contrast=1.08`
  - Background blur: `gblur=sigma=7`
  - Skin mask threshold (`skin_cr_min` in each project's retouch.json): <139, or the value that fit this person's skin>
  - Close-up softening (`close_lo`, `close_hi` in retouch.json): <0.31, 0.40 of the frame height, or the values the user chose>
  - Cover skin: <same as the video (it already has the close-up softening) / one step more>

## Brands
Copy this block for each brand or channel the user makes videos for.

### <Brand or channel name>
- Who it's for: <a business, a personal account...>
- Brand sheet: <not asked yet / path to index.html, and the sources used / not wanted (date)>
- Zooms: <none / alternate 1.00 and a punch-in such as 1.08, only where the head has room>
- Look, color: <natural / gentle boost eq=contrast=1.06:saturation=1.15:gamma=1.02 / not asked yet> (Log footage always gets only its LUT)
- Look, skin softening: <never / only when asked / every video>, level <default from Style defaults, or this brand's own>
- Look, beautify: <off / light / medium / strong>: a soft glow, brighter under-eyes and eye whites, with the matching skin softening (retouch.json `beautify`). No makeup, no reshaping. Keep it off or light for base-product and skincare reviews.
- Look, teeth whitening: <never / only when asked>
- Look, background blur: <never / only when asked / every video>, level <gblur sigma>
- Caption area starts at: <y position, e.g. 1320 on 1080x1920>, so zooms keep the chin above it
- Handle to show: <@handle, or none>, <where on screen, and for how long>
- Colors: <hex codes, and which is the accent>
- Font: <name, and where the font files are>
- Logos: `<paths; copy into the work folder before use>`
- Captions: <style: e.g. white text with black outline, or white on a colored box; case; position>
- Title: <style, length on screen; still, or animated with the TitleCard template: pop-in or typewriter (with or without key clicks)>
- Product tag: <none / ProductTag template: side, position, colors if different from the brand's>
- Product pop-in: <off / on>: the product's B-roll photo (cut out) or clip pops in beside the speaker when named (ProductPop template); with name and price <yes / no>; sound <pop / none>
- End card: <layout, contact details>
- Usual call to action: <what the viewer should do at the end, e.g. "Link in bio"; or "ask every time">
- Cover: <plain frame / with products (CoverCard)>; products <around the face / in a row>, <may overlap face and hair / kept clear>; title <above the head / below the face / none>; on the cover <nothing else / names / prices / numbers>
- Product photos: <where to get them, in order: own photos, websites the user named (e.g. cultbeauty.co.uk, sephora.com), video frames; and the date the user was told about shop photo rights>
- Loudness: <e.g. loudnorm=I=-14:TP=-1:LRA=11>
- Voice cleaning: <not asked yet / automatic / always light / always strong / never>; polish <on / off>; notes from listening
- Default platforms: <Reels, TikTok, Shorts, YouTube...>
- Niche and hashtags: <niche and audience, e.g. skincare for over-40s in Spain; core hashtags per platform, and the date they were checked>
- Other rules: <e.g. no zooms, always soften skin, one export only>

## Notes from feedback
Dated one-line notes of what the user asked to change, so it's never asked twice.
Record only what the user said, not a guess at why.

- <date>: <note>
