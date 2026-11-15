# Log footage

Part of the video-editor skill. `<skill>` is the folder that holds SKILL.md; rule numbers refer to SKILL.md.

**Log footage** looks grey and flat until it's converted with the camera maker's LUT (path in `my-setup.md`).

- **Spotting it:** Log files often carry no tag that says "Log". Apple Log from the iPhone (Apple's camera or the Blackmagic Camera app) shows `yuv422p10le`, `bt2020` primaries, `bt2020nc` matrix and `color_transfer=unknown` in `ffprobe -show_entries stream=pix_fmt,color_primaries,color_transfer,color_space`, and a frame looks washed out with low contrast. Don't apply a Log LUT to HDR video (`color_transfer=arib-std-b67` HLG, or `smpte2084` PQ) or normal `bt709` footage: they aren't Log, and the LUT would wreck them. If unsure, show the user a frame with and without the LUT and ask. Once confirmed, save how to recognize that camera's Log files in `my-setup.md`.
- **Convert first, then edit:** Log is usually recorded as huge ProRes files (about 6 GB per minute in 4K) that decode slowly. For Reels, TikTok, Shorts and other social clips, do this without asking: before any other step, convert each Log clip once into a light 10-bit copy with the LUT already applied, and do everything else on that copy (transcription, cuts, masks, retouch, export). Never touch the original. Save the copy in the video's work folder as `<original name>-709.mp4`, using the chain below plus `-map 0:v:0 -map 0:a:0 <10-bit in-between encoder from my-setup.md> -c:a copy -map_metadata 0 -movflags +faststart`.
  - For **YouTube** videos, ask first: "Convert to a light copy first (faster, no visible loss in testing), or edit straight from the original (slower, keeps every bit)?" YouTube is often watched in 4K on big screens, so the user decides there. If they choose the original, apply the LUT chain in the first render of each step instead, and keep in-between renders 10-bit.
  - Tested on 20.7 s of iPhone Apple Log ProRes HQ 4K, with Intel Quick Sync `hevc_qsv -global_quality 10`: conversion took 16.5 s, and the file went from 2.0 GB to 174 MB (12x smaller). Against converting the ProRes directly it measured SSIM 0.987, with no visible difference in a 100% face crop. Higher quality settings didn't measure any better. Other hardware encoders at their saved near-lossless setting should be similar; on the first conversion, compare one face crop against the original and say so if anything is visibly lost.
  - **Hardware decoding:** reading that copy back was 4x faster with hardware decoding (`-hwaccel qsv` before `-i`, 3.4 s against 11.4 s on the CPU). On the first conversion, time reading the copy with the decoder that matches the saved encoder (`-hwaccel cuda` for NVIDIA, `qsv` for Intel, `d3d11va` for AMD on Windows, `videotoolbox` on Mac) against no `-hwaccel`. If it's faster, save it in `my-setup.md` and put it before `-i` in every FFmpeg command that reads the copy.
  - Masks and face tracking also work much better on converted footage.
- **How:** convert to RGB with the file's own matrix first; letting FFmpeg guess gave a slightly blue, cool picture. On Windows, paths break `lut3d`, so copy the `.cube` file into the work folder and use the bare filename. For Apple Log:

```
-vf "scale=in_color_matrix=bt2020:in_range=tv:out_range=pc,format=gbrp16le,lut3d=<lut>.cube:interp=tetrahedral,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p10le,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv,<rest of the chain>"
```

  For other cameras, use the matrix in the file's `color_space` tag and check the LUT maker's notes on which input it expects.
- **No extra grade on Log footage** unless the user asks: the official LUT alone usually gives natural skin, and a saturation boost on top looked worse in testing. The brand's color choice in `my-setup.md` is for normal footage.
