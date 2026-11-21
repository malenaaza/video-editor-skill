"""Joins the voice clips of a video, levels them to match, and reaches a loudness target that
`loudnorm` can't: a quiet voice with clicks or breaths.

Found in a five-clip edit: the raw voice was about -32 LUFS with peaks near 0 dB (the clicks), and
`loudnorm` stopped at -13 LUFS because it won't raise the gain past what its true-peak limit allows.
The recipe that reached -11: a gain per clip so the clips match, then one big gain for the whole
voice, with a fast limiter that takes the clicks down instead.

  python -I leveljoin.py out.wav clip1.wav clip2.wav ... [--target -11] [--limit 0.84]
                         [--durations 73.92 43.21 ...] [--rate 48000]

1. Measures each clip's integrated loudness (EBU R128) and gives it the gain that brings it to the
   average of the clips, so no clip sticks out.
2. Joins them. Give --durations (the length of each clip's picture, seconds) to pad or trim each
   clip's voice to exactly that, so picture and sound stay in sync at every join.
3. Applies the gain that brings the whole voice to --target LUFS, then the limiter
   (alimiter limit=0.84, attack 3 ms, release 40 ms), and measures the result. The gain is adjusted
   up to four times until the result is within 0.3 LU of the target.
It writes the filter it used to leveljoin-filter.txt, and prints each clip's loudness and gain, the
final loudness and the true peak. If the target isn't reached (the limiter is already working hard),
it says so; a quieter target, or a cleaner recording, is the honest answer. Clean the voice first
(clean_voice.py) and level after it. Only the voice goes through this: mix sound effects afterwards.
"""
import argparse
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")


def run(cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)


def measure(path):
    err = run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    loudness = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    peak = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", err)
    if not loudness:
        sys.exit(f"Could not measure {path} (too short, or no audio).")
    return float(loudness[-1]), (float(peak[-1]) if peak and peak[-1] != "-inf" else None)


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout.strip())


def write_filter(path, clips, gains, durations, rate, total_gain, limit):
    lines = []
    for k, (gain, dur) in enumerate(zip(gains, durations)):
        lines.append(f"[{k}:a]aresample={rate},volume={gain:.1f}dB,apad,atrim=0:{dur:.6f},asetpts=PTS-STARTPTS[a{k}];")
    joined = "".join(f"[a{k}]" for k in range(len(clips)))
    lines.append(f"{joined}concat=n={len(clips)}:v=0:a=1,volume={total_gain:.1f}dB,"
                 f"alimiter=limit={limit}:attack=3:release=40:level=disabled[a]")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--target", type=float, default=-14.0, help="integrated loudness in LUFS (default -14)")
    ap.add_argument("--limit", type=float, default=0.84, help="limiter ceiling, linear (0.84 = -1.5 dBFS)")
    ap.add_argument("--durations", type=float, nargs="+", help="length of each clip's picture, seconds")
    ap.add_argument("--rate", type=int, default=48000)
    ap.add_argument("--filter-file", default="leveljoin-filter.txt")
    a = ap.parse_args()
    if a.durations and len(a.durations) != len(a.clips):
        sys.exit("--durations needs one length per clip.")

    levels = [measure(c)[0] for c in a.clips]
    ref = sum(levels) / len(levels)
    gains = [round(ref - lv, 1) for lv in levels]
    durations = a.durations or [duration(c) for c in a.clips]
    for c, lv, g in zip(a.clips, levels, gains):
        print(f"{c}: {lv:.1f} LUFS, gain {g:+.1f} dB")
    inputs = [x for c in a.clips for x in ("-i", c)]
    total = a.target - ref
    final, peak = None, None
    for attempt in range(4):
        write_filter(a.filter_file, a.clips, gains, durations, a.rate, total, a.limit)
        # The graph is passed as text: -filter_complex_script is gone in FFmpeg 8 and later, and -/filter_complex
        # needs 7, so a file option would break on one side or the other. The file stays, to read or reuse.
        with open(a.filter_file, encoding="utf-8") as f:
            graph = f.read()
        run(["ffmpeg", "-nostdin", "-hide_banner", "-y", *inputs, "-filter_complex", graph, "-map", "[a]",
             "-ar", a.rate, "-c:a", "pcm_s16le", a.out])
        new, peak = measure(a.out)
        print(f"try {attempt + 1}: whole-voice gain {total:+.1f} dB -> {new:.1f} LUFS" + (f", true peak {peak:.1f} dBFS" if peak is not None else ""))
        if final is not None and abs(new - final) < 0.1 and abs(new - a.target) > 0.3:
            final = new
            break  # more gain no longer raises the loudness: the limiter is holding it
        final = new
        if abs(new - a.target) <= 0.3:
            break
        total += a.target - new
    print(f"Wrote {a.out}: {final:.1f} LUFS (target {a.target:g})" + (f", true peak {peak:.1f} dBFS" if peak is not None else ""))
    if peak is not None and peak > -1.0:
        print(f"The true peak is {peak:.1f} dBFS, above the -1 dBFS most platforms like to see (the limiter holds the "
              "sample peaks at its ceiling, and the true peak can sit a little higher). Lower --limit (0.8) if you want headroom.")
    if abs(final - a.target) > 0.5:
        print("The target wasn't reached: the limiter is holding the peaks. Take the target down a little, or clean "
              "the voice first. Say how far off it is.")


if __name__ == "__main__":
    main()
