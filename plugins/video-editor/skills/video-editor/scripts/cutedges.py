"""Checks every cut in a cut plan by its sound, before the cut is rendered.

  python -I cutedges.py [--plan plan.json] [--fix plan-fixed.json] [--search 0.4]

Word times from a transcript are guesses, often 50 to 100 ms off, so a cut placed on them can land inside a sound.
This looks at the recording itself (the plan's source) around every edge of every kept piece and reports:
  - a piece that STARTS in the middle of a sound: the sound was already going before the cut, so the start of a word
    is clipped, or the tail of a removed word leaks in;
  - a piece that ENDS in the middle of a sound: the end of a word is cut off;
  - a FRAGMENT: a short burst (under 0.12 s) at the very start or end of a piece, cut off from the rest by a gap: a
    leftover of a removed word or a breath;
  - a SLIVER: a piece under 0.12 s, which flashes by;
each with its time in the cut (to listen to) and in the source, and the fix. A cut inside a sound never moves to
"the quietest moment nearby", which can be the soft start of the same word and leave half of it (that happened in
the first test): it finds where the sound starts and stops (within --search seconds) and keeps the word whole when
most of it is inside the piece, or drops it whole when most of it is outside. A fragment's edge moves into the gap
after it. With --fix it writes a new plan with those edges moved, slivers dropped and the offsets recounted; render
from that plan. Clean edges are never moved.

"Loud" and "quiet" are measured against the voice's own level (its loud parts), not a fixed level, so a quiet room
and a loud room are judged alike. Needs numpy and FFmpeg (the speech Python has numpy).
"""
import argparse
import json
import subprocess
import sys
from fractions import Fraction

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

RATE = 16000
HOP = 0.005          # seconds per loudness step
EDGE_IN = 0.02       # seconds inside the piece that must be quiet at an edge
EDGE_OUT = 0.03      # seconds outside the piece looked at for a sound going on across the edge
LOUD = 28.0          # dB under the voice's loud parts still counted as sound
SHORTEST = 0.12      # seconds: a burst or a piece shorter than this is a fragment or a sliver


def source_audio(path):
    """(samples at RATE, mono, float; seconds the audio starts after time 0 of the file)."""
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", path],
                                     capture_output=True, text=True, encoding="utf-8").stdout or "{}")
    sound = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if sound is None:
        sys.exit(f"{path} has no sound to check the cuts against.")
    start = float(sound.get("start_time", 0) or 0)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(RATE),
                          "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768, start


def loudness_db(samples):
    """dB every HOP seconds, and the voice's reference level (its loud parts, the 95th percentile)."""
    step = int(RATE * HOP)
    m = len(samples) // step
    rms = np.sqrt((samples[:m * step].reshape(m, step) ** 2).mean(axis=1)) + 1e-7
    db = 20 * np.log10(rms)
    return db, float(np.percentile(db, 95))


class Sound:
    """Loudness of the recording, read by time in the file (seconds)."""

    def __init__(self, samples, start=0.0):
        self.db, self.ref = loudness_db(samples)
        self.start = start

    def index(self, t):
        return int(round((t - self.start) / HOP))

    def loud(self, t0, t1):
        """True if the stretch has sound in it (its loudest step within LOUD dB of the voice's level)."""
        a, b = max(0, self.index(t0)), min(len(self.db), self.index(t1))
        return b > a and float(self.db[a:b].max()) > self.ref - LOUD

    def quietest(self, t, search):
        """The quietest moment within `search` seconds of t (the middle of the quietest 20 ms)."""
        a, b = max(0, self.index(t - search)), min(len(self.db) - 4, self.index(t + search))
        if b <= a:
            return t
        smooth = np.convolve(self.db, np.ones(4) / 4, mode="same")
        i = a + int(np.argmin(smooth[a:b]))
        return self.start + i * HOP

    def quiet_side(self, t, direction, limit):
        """Walking from t (direction -1 back, +1 on) up to `limit` seconds, the first moment that starts 20 ms of
        quiet, nudged 10 ms into that quiet; None if the sound goes on that long."""
        quiet = self.db < self.ref - LOUD
        i, steps, need = self.index(t), int(limit / HOP), int(0.02 / HOP)
        for k in range(steps):
            j = i + direction * k
            run = quiet[j:j + need] if direction > 0 else quiet[max(0, j - need + 1):j + 1]
            if j < 0 or j >= len(quiet):
                return None
            if len(run) == need and run.all():
                return self.start + (j + direction * 2) * HOP
        return None

    def whole_word(self, t, edge, limit):
        """Where an edge cut inside a sound should go: the sound's end (keep it whole) when most of it is inside the
        piece, its start (drop it whole) when most of it is outside. edge is "start" or "end" of the piece."""
        before, after = self.quiet_side(t, -1, limit), self.quiet_side(t, +1, limit)
        if before is None and after is None:
            return None
        if before is None or after is None:
            return after if before is None else before
        inside, outside = (t - before, after - t) if edge == "end" else (after - t, t - before)
        if edge == "end":
            return after if inside > outside else before
        return before if inside > outside else after

    def burst_at(self, t0, t1, from_end=False):
        """A short burst at one end of [t0, t1): (burst start, burst end, gap end) when the piece opens (or closes)
        on under SHORTEST seconds of sound followed (or preceded) by a quiet gap of at least 40 ms, else None."""
        a, b = max(0, self.index(t0)), min(len(self.db), self.index(t1))
        loud = self.db[a:b] > self.ref - LOUD
        if from_end:
            loud = loud[::-1]
        if not len(loud) or not loud[:max(1, int(0.02 / HOP))].any():
            return None
        first_quiet = np.argmax(~loud) if (~loud).any() else len(loud)
        burst = first_quiet * HOP
        rest = loud[first_quiet:]
        gap = (np.argmax(rest) if rest.any() else len(rest)) * HOP
        if burst < SHORTEST and gap >= 0.04 and rest.any():
            if from_end:
                return (t1 - burst, t1, t1 - burst - gap)
            return (t0, t0 + burst, t0 + burst + gap)
        return None


def check(plan, sound, search=0.4):
    """Problems [{kind, piece, edge, source, cut, fix}] for every edge of every kept piece, where `fix` is the
    source time the edge should move to (None when there is nothing better)."""
    fps = float(Fraction(plan["fps"]))
    frames, offsets = plan["frames"], plan["offsets"]
    problems = []
    for i, ((f0, f1), off) in enumerate(zip(frames, offsets)):
        t0, t1 = f0 / fps, f1 / fps
        cut0, cut1 = off / fps, (off + f1 - f0) / fps
        if t1 - t0 < SHORTEST:
            problems.append({"kind": "sliver", "piece": i, "edge": "both", "source": t0, "cut": cut0, "fix": None})
            continue
        if i > 0 or f0 > 0:
            frag = sound.burst_at(t0, t1)
            if frag:
                problems.append({"kind": "fragment", "piece": i, "edge": "start", "source": t0, "cut": cut0,
                                 "fix": sound.quietest((frag[1] + frag[2]) / 2, (frag[2] - frag[1]) / 2)})
            elif sound.loud(t0 - EDGE_OUT, t0) and sound.loud(t0, t0 + EDGE_IN):
                problems.append({"kind": "starts mid-sound", "piece": i, "edge": "start", "source": t0, "cut": cut0,
                                 "fix": sound.whole_word(t0, "start", search)})
        frag = sound.burst_at(t0, t1, from_end=True)
        if frag:
            problems.append({"kind": "fragment", "piece": i, "edge": "end", "source": t1, "cut": cut1,
                             "fix": sound.quietest((frag[0] + frag[2]) / 2, (frag[0] - frag[2]) / 2)})
        elif sound.loud(t1 - EDGE_IN, t1) and sound.loud(t1, t1 + EDGE_OUT):
            problems.append({"kind": "ends mid-sound", "piece": i, "edge": "end", "source": t1, "cut": cut1,
                             "fix": sound.whole_word(t1, "end", search)})
    return problems


def apply_fixes(plan, problems):
    """A new plan with the edges moved to their quiet moments (snapped to frames, never past a neighbour or across
    the piece), slivers dropped and the offsets and total recounted."""
    fps = Fraction(plan["fps"])
    frames = [list(f) for f in plan["frames"]]
    drop = set()
    for p in problems:
        i = p["piece"]
        if p["kind"] == "sliver":
            drop.add(i)
            continue
        if p["fix"] is None:
            continue
        frame = round(p["fix"] * fps)
        if p["edge"] == "start":
            low = frames[i - 1][1] if i > 0 else 0
            frames[i][0] = min(max(frame, low), frames[i][1] - 1)
        else:
            high = frames[i + 1][0] if i + 1 < len(frames) else frame
            frames[i][1] = max(min(frame, high), frames[i][0] + 1)
    kept = [f for i, f in enumerate(frames) if i not in drop and f[1] > f[0]]
    offsets, total = [], 0
    for f0, f1 in kept:
        offsets.append(total)
        total += f1 - f0
    new = dict(plan)
    new.update(frames=kept, offsets=offsets, total_frames=total)
    new.pop("_fps", None)
    return new


def stamp(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", default="plan.json")
    ap.add_argument("--source", help="the recording the plan cuts (default: the plan's own source)")
    ap.add_argument("--search", type=float, default=0.4, help="how far to look for where a sound starts or stops (s)")
    ap.add_argument("--fix", help="write a plan with the edges moved here (e.g. plan-fixed.json)")
    a = ap.parse_args()
    with open(a.plan, encoding="utf-8") as f:
        plan = json.load(f)
    samples, start = source_audio(a.source or plan["source"])
    sound = Sound(samples, start)
    problems = check(plan, sound, a.search)
    pieces = len(plan["frames"])
    print(f"{pieces} pieces, {2 * pieces - 1} cut edges checked by their sound: {len(problems)} to look at.")
    for p in problems:
        move = ""
        if p["fix"] is not None:
            move = f", quiet {abs(p['fix'] - p['source']) * 1000:.0f} ms {'earlier' if p['fix'] < p['source'] else 'later'}"
        print(f"  {p['kind']}: piece {p['piece'] + 1} {p['edge']}, at {stamp(p['cut'])} in the cut "
              f"({stamp(p['source'])} in the source){move}")
    if a.fix:
        new = apply_fixes(plan, problems)
        with open(a.fix, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=1)
        print(f"Wrote {a.fix}: {len(new['frames'])} pieces, {new['total_frames']} frames. Run cutedges.py on it again "
              "(it should find nothing), then make the filter from it: cutplan.py filter --plan " + a.fix)
    elif problems:
        print("Listen to them, then write a fixed plan with --fix plan-fixed.json.")


if __name__ == "__main__":
    main()
