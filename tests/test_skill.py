"""Tests the skill's scripts on a small generated clip. No real footage or Whisper needed.

Run: python tests/test_skill.py
Needs Python 3.10+, FFmpeg, ffprobe and numpy. The colour key test also needs OpenCV and is
skipped without it. The face-tracking scripts (masks, mouth check) and the Whisper scripts
are only compiled here, not run.
"""
import json
from fractions import Fraction
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "plugins" / "video-editor" / "skills" / "video-editor"
SCRIPTS = ROOT / "scripts"
PUPPET = REPO / "plugins" / "video-editor" / "skills" / "puppet-video"
FPS = 30

WORDS = [(" Hola", 0.5, 1.0), (" amigas,", 1.0, 1.5),      # first take, removed in cuts.json
         (" Hola", 2.5, 3.0), (" amigos.", 3.0, 3.5),
         (" Hoy", 4.2, 4.5), (" glo", 4.5, 4.7), (" serum", 4.7, 5.0),
         (" es", 7.0, 7.3), (" genial.", 7.3, 8.0)]
TONES = [(0.5, 1.5), (2.5, 3.5), (4.2, 5.0), (7.0, 8.0)]


def run(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(f"{' '.join(str(c) for c in cmd)}\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def script(name, *args, cwd):
    return run([sys.executable, "-I", SCRIPTS / name, *args], cwd=cwd)


def filter_flag():
    version = re.search(r"ffmpeg version n?(\d+)", run(["ffmpeg", "-version"]))
    return "-/filter_complex" if version and int(version.group(1)) >= 7 else "-filter_complex_script"


def probe_audio(path):
    """(channels, sample rate, duration) of an audio file."""
    out = run(["ffprobe", "-v", "error", "-show_entries", "stream=channels,sample_rate:format=duration", "-of", "json",
               path])
    info = json.loads(out)
    s = info["streams"][0]
    return int(s["channels"]), int(s["sample_rate"]), float(info["format"]["duration"])


def probe(path, cwd):
    out = run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
               "stream=codec_type,nb_read_frames,duration", "-of", "json", path], cwd=cwd)
    streams = {s["codec_type"]: s for s in json.loads(out)["streams"]}
    return int(streams["video"]["nb_read_frames"]), float(streams["video"]["duration"]), float(streams["audio"]["duration"])


class SkillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="video-editor-test-"))
        gate = "+".join(f"between(t,{a},{b})" for a, b in TONES)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=540x960:r={FPS}:d=12",
             "-f", "lavfi", "-i", f"aevalsrc='0.3*sin(2*PI*220*t)*({gate})+0.0003*random(0)':s=48000:d=12",
             "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "src.mp4"], cwd=cls.dir)
        words = [{"word": w, "start": s, "end": e} for w, s, e in WORDS]
        (cls.dir / "tr.json").write_text(json.dumps({"language": "es", "segments": [{"words": words}]}), "utf-8")
        (cls.dir / "cuts.json").write_text(json.dumps({"remove": [[0.3, 1.9, "first take"]]}), "utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def build(self, *extra, out="plan.json"):
        text = script("cutplan.py", "build", "src.mp4", "tr.json", "--cuts", "cuts.json", "--out", out, *extra, cwd=self.dir)
        return json.loads((self.dir / out).read_text("utf-8")), text

    def test_01_every_script_compiles(self):
        for path in [*SCRIPTS.rglob("*.py"), *(PUPPET / "scripts").rglob("*.py")]:
            py_compile.compile(str(path), doraise=True)

    def test_02_plan_removes_pauses_and_listed_cuts(self):
        plan, _ = self.build()
        frames = plan["frames"]
        self.assertEqual(len(frames), 3)
        self.assertGreaterEqual(frames[0][0] / FPS, 1.9, "the removed first take is still in the cut")
        # every kept word is inside a kept piece, with the lead-in the skill asks for
        for _, s, e in WORDS[2:]:
            self.assertTrue(any(f0 / FPS <= s + 0.01 and e - 0.01 <= f1 / FPS for f0, f1 in frames), (s, e))
        # 0.5 s is kept after the last word, and nothing after that
        self.assertAlmostEqual(frames[-1][1] / FPS, 8.5, delta=0.07)
        self.assertEqual(plan["total_frames"], sum(b - a for a, b in frames))
        self.assertEqual(plan["offsets"][0], 0)

    def test_03_natural_pace_keeps_short_pauses(self):
        tight, _ = self.build()
        natural, _ = self.build("--keep-pause", "0.3", out="plan-natural.json")
        self.assertGreater(natural["total_frames"], tight["total_frames"])

    def test_04_protect_stops_a_pause_cut(self):
        (self.dir / "cuts-protect.json").write_text(json.dumps(
            {"remove": [[0.3, 1.9]], "protect": [[3.5, 4.2, "keep this pause"]]}), "utf-8")
        script("cutplan.py", "build", "src.mp4", "tr.json", "--cuts", "cuts-protect.json", "--out", "plan-protect.json", cwd=self.dir)
        plan = json.loads((self.dir / "plan-protect.json").read_text("utf-8"))
        self.assertTrue(any(f0 / FPS <= 3.5 and f1 / FPS >= 4.2 for f0, f1 in plan["frames"]))

    def test_05_cut_renders_with_matching_picture_and_sound(self):
        for speed in ("1.0", "1.1"):
            plan, _ = self.build("--speed", speed)
            script("cutplan.py", "filter", cwd=self.dir)
            run(["ffmpeg", "-v", "error", "-y", "-i", "src.mp4", filter_flag(), "cut-filter.txt", "-map", "[v]",
                 "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "pcm_s16le", "cut.mov"], cwd=self.dir)
            frames, video, audio = probe("cut.mov", self.dir)
            self.assertAlmostEqual(frames, plan["total_frames"] / float(speed), delta=1)
            self.assertAlmostEqual(video, audio, delta=1.5 / FPS)

    def test_06_times_convert_both_ways(self):
        self.build("--speed", "1.1")
        out = script("cutplan.py", "to-output", "4.6", "1.0", cwd=self.dir)
        self.assertIn("source 1.000 -> removed", out)
        cut_time = float(re.search(r"source 4\.600 -> cut ([\d.]+)", out).group(1))
        back = script("cutplan.py", "to-source", f"{cut_time}", cwd=self.dir)
        self.assertAlmostEqual(float(re.search(r"source ([\d.]+)", back).group(1)), 4.6, delta=0.01)

    def test_07_captions_follow_the_cut(self):
        plan, _ = self.build("--speed", "1.1")
        (self.dir / "fix.json").write_text(json.dumps({"glo serum": "Glow Serum"}), "utf-8")
        script("captions.py", "tr.json", "--font", "DejaVu Sans", "--width", "540", "--height", "960", "--size", "40",
               "--margin-v", "260", "--fix", "fix.json", "--upper", cwd=self.dir)
        caps = json.loads((self.dir / "captions.json").read_text("utf-8"))
        text = " ".join(c["text"] for c in caps)
        self.assertEqual(text, "HOLA AMIGOS. HOY GLOW SERUM ES GENIAL.")
        self.assertNotIn("AMIGAS", text, "a word from the removed take is in the captions")
        length = plan["total_frames"] / FPS / 1.1
        last = 0
        for c in caps:
            self.assertGreaterEqual(c["start"], last - 0.001, "captions overlap")
            self.assertGreater(c["end"], c["start"])
            self.assertLessEqual(c["end"], length + 0.01)
            last = c["end"]
        ass = (self.dir / "captions.ass").read_text("utf-8-sig")
        self.assertEqual(ass.count("Dialogue:"), len(caps))
        if " ass " in run(["ffmpeg", "-hide_banner", "-filters"]):
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=black:s=540x960:d=1", "-vf",
                 "ass=captions.ass", "-frames:v", "1", "cap.png"], cwd=self.dir)
            self.assertGreater((self.dir / "cap.png").stat().st_size, 500)

    def test_08_filler_edges_from_the_plan(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy not installed")
        self.build()
        build = self.dir / "build"
        build.mkdir(exist_ok=True)
        shutil.copy(self.dir / "plan.json", build / "plan.json")
        run(["ffmpeg", "-v", "error", "-y", "-i", "src.mp4", "-ac", "1", "audio.wav"], cwd=self.dir)
        out = script("findfill.py", "1.2", "1.5", "cut", cwd=build)
        a, b = json.loads(out.strip().splitlines()[-1])[0]
        self.assertAlmostEqual(a, 4.2, delta=0.05)  # the edges of the tone that holds that moment
        self.assertAlmostEqual(b, 5.0, delta=0.05)

    def test_09_filter_files_run(self):
        for name in ("skin", "teeth", "strong", "spots", "bg"):
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=gray:s=540x960:r={FPS}:d=0.5",
                 "-pix_fmt", "gray", "-c:v", "ffv1", f"{name}.mkv"], cwd=self.dir)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=540x960:r={FPS}:d=0.5",
             "-c:v", "libx264", "-preset", "ultrafast", "clean.mp4"], cwd=self.dir)
        masks = ["-i", "skin.mkv", "-i", "teeth.mkv", "-i", "strong.mkv", "-i", "spots.mkv"]
        for name, extra in (("retouch.txt", []), ("retouch-blur.txt", ["-i", "bg.mkv"])):
            run(["ffmpeg", "-v", "error", "-y", "-i", "clean.mp4", *masks, *extra, filter_flag(),
                 SCRIPTS / "retouch" / name, "-map", "[v]", "-frames:v", "5", "-c:v", "libx264", "-preset", "ultrafast",
                 "out.mp4"], cwd=self.dir)
        # the sound effect mix example, with the four bundled sounds
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=15.8333:r=48000", "voice.wav"], cwd=self.dir)
        sfx = [x for n in ("pop", "whoosh", "sparkle", "cash") for x in ("-i", SCRIPTS / "sfx" / f"{n}.wav")]
        run(["ffmpeg", "-v", "error", "-y", "-i", "voice.wav", *sfx, filter_flag(), SCRIPTS / "sfx" / "sfx-mix-example.txt",
             "-map", "[a]", "-ar", "48000", "-c:a", "pcm_s16le", "mix.wav"], cwd=self.dir)

    def test_10_retouch_settings(self):
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import settings
        here = os.getcwd()
        os.chdir(self.dir)
        try:
            self.assertEqual(settings.load()["skin_cr_min"], 139)
            self.assertEqual(settings.load()["region_grow"], [1.35, 1.1])
            Path("retouch.json").write_text(json.dumps({"skin_cr_min": 132}), "utf-8")
            loaded = settings.load()
            self.assertEqual((loaded["skin_cr_min"], loaded["skin_cr_max"]), (132, 185))
            Path("retouch.json").write_text(json.dumps({"skin_min": 1}), "utf-8")
            with self.assertRaises(SystemExit):
                settings.load()
            Path("retouch.json").unlink()
        finally:
            os.chdir(here)
        try:
            import cv2  # noqa: F401
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV not installed: colour keys not tested")
        frame = np.zeros((4, 4, 3), np.uint8)
        frame[:2] = (0, 0, 255)   # red, in BGR
        frame[2:] = (255, 0, 0)   # blue
        red = {"name": "red top", "hue": [170, 7], "sat": [131, None]}
        mask = settings.key_mask(frame, [red])
        self.assertTrue(mask[:2].all() and not mask[2:].any())
        self.assertFalse(settings.key_mask(frame, []).any())

    def test_11_edge_face_geometry(self):
        try:
            import numpy as np
            sys.path.insert(0, str(SCRIPTS / "retouch"))
            import facetrack
        except ImportError:
            self.skipTest("mediapipe or numpy not installed")
        frame = np.arange(4 * 10 * 3, dtype=np.uint8).reshape(4, 10, 3)
        right = facetrack.mirrored(frame, "right", 5)
        self.assertEqual(right.shape, (4, 15, 3))
        self.assertTrue((right[:, 10] == frame[:, 9]).all() and (right[:, 14] == frame[:, 5]).all())
        left = facetrack.mirrored(frame, "left", 5)
        self.assertTrue((left[:, 4] == frame[:, 0]).all() and (left[:, 5:] == frame).all())
        nose = lambda x: np.array([[0, 0], [x, 0]], np.float32)  # landmark 1 is the nose tip
        self.assertTrue(facetrack.plausible(nose(1000), 960, "right", 480))
        self.assertFalse(facetrack.plausible(nose(200), 960, "right", 480))  # face centre far from that edge
        self.assertTrue(facetrack.plausible(nose(480 + 20), 960, "left", 480))
        self.assertFalse(facetrack.plausible(nose(480 + 800), 960, "left", 480))

    # ---- ported from a five-clip edit -------------------------------------------------------

    def _wav(self, name, x, rate):
        import wave

        import numpy as np
        w = wave.open(str(self.dir / name), "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
        w.close()

    def _numpy(self):
        try:
            import numpy
        except ImportError:
            self.skipTest("numpy not installed")
        return numpy

    def test_20_long_cut_filter_uses_several_selects(self):
        pieces = [[i * 3, i * 3 + 2] for i in range(100)]  # 100 pieces: more than one select of 40 terms
        (self.dir / "big.json").write_text(json.dumps({
            "source": "src.mp4", "fps": "30", "speed": 1.0, "audio_offset": 0.0, "sample_rate": 48000,
            "frames": pieces, "offsets": [i * 2 for i in range(100)], "total_frames": 200, "removed": []}), "utf-8")
        script("cutplan.py", "filter", "--plan", "big.json", "--out", "big-filter.txt", cwd=self.dir)
        text = (self.dir / "big-filter.txt").read_text("utf-8")
        self.assertIn("split=3", text)
        self.assertLessEqual(max(len(line.split("+")) for line in text.splitlines() if "select=" in line), 40)
        run(["ffmpeg", "-v", "error", "-y", "-i", "src.mp4", filter_flag(), "big-filter.txt", "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "pcm_s16le", "big.mov"], cwd=self.dir)
        frames, video, audio = probe("big.mov", self.dir)
        self.assertEqual(frames, 200)
        self.assertAlmostEqual(video, audio, delta=2 / FPS)

    def test_21_quiet_words_are_not_cut_as_pauses(self):
        np = self._numpy()
        sr = 48000
        t = np.arange(int(7 * sr)) / sr
        gate = lambda a, b: ((t >= a) & (t < b)).astype(float)
        x = (0.3 * np.sin(2 * np.pi * 220 * t) * (gate(0.5, 1.5) + gate(4.0, 5.0))
             + 0.004 * np.sin(2 * np.pi * 200 * t) * gate(2.5, 3.1) + 0.0003 * np.random.RandomState(0).rand(len(t)))
        self._wav("whisper.wav", x, sr)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=320x240:r={FPS}:d=7", "-i", "whisper.wav",
             "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", "whisper.mp4"], cwd=self.dir)
        words = [(" uno", 0.5, 1.5), (" y", 2.5, 2.7), (" ya", 2.7, 2.9), (" est\u00e1", 2.9, 3.1), (" fin", 4.0, 5.0)]
        (self.dir / "tr-whisper.json").write_text(json.dumps({"segments": [{"words": [
            {"word": w, "start": s, "end": e} for w, s, e in words]}]}), "utf-8")
        script("cutplan.py", "build", "whisper.mp4", "tr-whisper.json", "--out", "plan-whisper.json", cwd=self.dir)
        plan = json.loads((self.dir / "plan-whisper.json").read_text("utf-8"))
        self.assertTrue(any(f0 / FPS <= 2.51 and 3.09 <= f1 / FPS for f0, f1 in plan["frames"]),
                        "the whispered words were cut as a pause")
        self.assertLess(plan["total_frames"] / FPS, 4.5, "the pauses around them were not removed")

    def test_22_drops_keep_picture_and_voice_in_sync(self):
        np = self._numpy()
        sr = 48000
        t = np.arange(int(9 * sr)) / sr
        gate = lambda a, b: ((t >= a) & (t < b)).astype(float)
        x = 0.2 * np.sin(2 * np.pi * 220 * t) * gate(0.5, 1.5) + 0.2 * np.sin(2 * np.pi * 330 * t) * gate(2.5, 3.5)
        x += 0.15 * np.sin(2 * np.pi * 150 * t) * gate(3.9, 4.4) + 0.2 * np.sin(2 * np.pi * 200 * t) * gate(5.0, 6.2)
        x += 0.2 * np.sin(2 * np.pi * 260 * t) * gate(7.4, 8.4) + 0.0005 * np.random.RandomState(1).randn(len(t))
        self._wav("drops-voice.wav", x, sr)
        (self.dir / "drops.txt").write_text("F 3.9 4.4 hum\nV 5.0 6.2 held\nN 1.5 2.5 pause to keep\n", "utf-8")
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=320x240:r={FPS}:d=9", "-c:v", "libx264",
             "-preset", "ultrafast", "drops-src.mp4"], cwd=self.dir)
        out = script("drops.py", "drops-voice.wav", "--fps", str(FPS), cwd=self.dir)
        self.assertIn("held sounds: 1 drops", out)
        info = json.loads((self.dir / "drops.json").read_text("utf-8"))
        kinds = [d["kind"] for d in info["drops"]]
        self.assertEqual(kinds.count("F"), 1)
        self.assertEqual(kinds.count("V"), 1)
        self.assertFalse(any(d["kind"] == "P" and 1.5 <= d["start"] <= 2.5 for d in info["drops"]), "the N range was trimmed")
        run(["ffmpeg", "-v", "error", "-y", "-i", "drops-src.mp4", filter_flag(), "drops-video.txt", "-map", "[v]",
             "-c:v", "libx264", "-preset", "ultrafast", "dropped.mp4"], cwd=self.dir)
        counted = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries",
                       "stream=nb_read_frames", "-of", "csv=p=0", "dropped.mp4"], cwd=self.dir)
        frames = int(counted.strip())
        self.assertEqual(frames, info["new_frames"])
        import wave
        w = wave.open(str(self.dir / "voice-dropped.wav"))
        self.assertAlmostEqual(w.getnframes() / w.getframerate(), frames / FPS, delta=0.002)
        listing = script("drops.py", "drops-voice.wav", "--fps", str(FPS), "--list-pauses", cwd=self.dir)
        self.assertIn("quiet stretches", listing)

    def test_23_captions_from_the_cut_voice_and_after_drops(self):
        words = [(" muy", 0.0, 0.3), (" buenos", 0.3, 0.7), (" d\u00edas", 0.7, 1.1), (" a", 1.1, 1.2), (" todos", 1.2, 1.6),
                 (" um", 2.0, 2.4), (" los", 2.4, 2.7), (" amigos.", 2.7, 3.2)]
        (self.dir / "cut-voice.json").write_text(json.dumps({"segments": [{"words": [
            {"word": w, "start": s, "end": e} for w, s, e in words]}]}), "utf-8")
        (self.dir / "drops-info.json").write_text(json.dumps({"frame": 1 / 30, "old_frames": 120, "new_frames": 105, "drops": [
            {"kind": "F", "start": 2.0, "len": 0.4, "frames": [60, 71], "note": "um"},
            {"kind": "P", "start": 3.4, "len": 0.1, "frames": [102, 104], "note": "pause"}]}), "utf-8")
        common = ["--on-cut", "--font", "DejaVu Sans", "--width", "540", "--height", "960", "--max-words", "4",
                  "--dangling", "es", "--length", "4"]
        script("captions.py", "cut-voice.json", *common, "--drops", "drops-info.json", "--two-lines", "10", cwd=self.dir)
        caps = json.loads((self.dir / "captions.json").read_text("utf-8"))
        text = [c["text"] for c in caps]
        self.assertNotIn("um", " ".join(text).split(), "the removed filler is in the captions")
        self.assertFalse(any(t.endswith(" a") for t in text), "a caption ends on a small word")
        los = next(w for c in caps for w in c["words"] if w[2] == "los")
        self.assertAlmostEqual(los[0], 2.4 - 0.4, delta=0.01)  # moved up by the filler that was cut before it
        self.assertAlmostEqual(caps[-1]["words"][-1][1], 3.2 - 0.4, delta=0.01)
        self.assertIn("\\N", (self.dir / "captions.ass").read_text("utf-8-sig"))
        # two clips: the second clip's times are shifted by the first one's length
        script("captions.py", "cut-voice.json", "cut-voice.json", "--on-cut", "--durations", "4", "3", "--font", "DejaVu Sans",
               "--out", "two.ass", "--width", "540", "--height", "960", cwd=self.dir)
        two = json.loads((self.dir / "two.json").read_text("utf-8"))
        self.assertAlmostEqual(two[-1]["words"][-1][1], 4 + 3.2, delta=0.01)

    def test_24_held_sounds_found_and_speech_left_alone(self):
        np = self._numpy()
        sr = 16000
        t = np.arange(int(6 * sr)) / sr
        x = np.zeros_like(t)
        held = 0.2 * np.sin(2 * np.pi * 200 * t) + 0.12 * np.sin(2 * np.pi * 400 * t) + 0.08 * np.sin(2 * np.pi * 1200 * t)
        x += held * ((t >= 1.0) & (t < 1.7))
        for k, f in enumerate([300, 900, 500, 1800, 700, 2400, 400, 1500, 600, 2000, 350]):  # a new sound every 80 ms
            m = (t >= 3.0 + k * 0.08) & (t < 3.08 + k * 0.08)
            x[m] = 0.2 * np.sin(2 * np.pi * f * t[m]) + 0.1 * np.sin(2 * np.pi * 2.5 * f * t[m])
        x += 0.0003 * np.random.RandomState(0).randn(len(t))
        self._wav("held.wav", x, sr)
        out = script("heldsounds.py", "held.wav", cwd=self.dir)
        starts = [float(m) for m in re.findall(r"^V ([\d.]+) ", out, re.M)]
        self.assertEqual(len(starts), 1, out)
        self.assertAlmostEqual(starts[0], 1.0, delta=0.1)

    def test_25_level_and_join_reaches_the_target(self):
        np = self._numpy()
        sr = 48000
        for name, secs, amp, clicks in (("lv-a.wav", 6, 0.02, [1.0, 3.3, 4.1]), ("lv-b.wav", 4, 0.05, [2.2])):
            t = np.arange(int(secs * sr)) / sr
            x = amp * np.sin(2 * np.pi * 180 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t))
            x += amp * 0.1 * np.random.RandomState(len(name)).randn(len(t))
            for c in clicks:
                x[int(c * sr):int(c * sr) + 20] = 0.9  # clicks near full scale, which stops loudnorm
            self._wav(name, x, sr)
        out = script("voice/leveljoin.py", "leveled.wav", "lv-a.wav", "lv-b.wav", "--target", "-14", "--durations", "6", "4", cwd=self.dir)
        reached = float(re.search(r"Wrote leveled.wav: (-?[\d.]+) LUFS", out).group(1))
        self.assertAlmostEqual(reached, -14, delta=0.5)
        import wave
        w = wave.open(str(self.dir / "leveled.wav"))
        self.assertAlmostEqual(w.getnframes() / w.getframerate(), 10.0, delta=0.01)

    def test_26_transcription_engines_share_one_interface(self):
        self._numpy()
        sys.path.insert(0, str(SCRIPTS))
        import asr

        class Word:
            def __init__(self, word, start, end):
                self.word, self.start, self.end = word, start, end

        class Segment:
            text = " eh vale"
            words = [Word(" eh", 0.1, 0.4), Word(" vale", 0.5, 0.9)]

        class Faster:  # the shape of faster_whisper.WhisperModel.transcribe
            def transcribe(self, audio, **kwargs):
                assert kwargs["word_timestamps"] and kwargs["condition_on_previous_text"] is False
                return iter([Segment()]), None

        class Openai:  # the shape of whisper's model.transcribe
            def transcribe(self, audio, **kwargs):
                return {"text": " eh vale", "segments": [{"words": [
                    {"word": " eh", "start": 0.1, "end": 0.4}, {"word": " vale", "start": 0.5, "end": 0.9}]}]}

        silence = [0.0] * 16000
        for engine, model in (("faster", Faster()), ("openai", Openai())):
            text, found = asr.transcribe(model, engine, silence, "es", "Eh, mmm.", words=True)
            self.assertEqual(text, "eh vale")
            self.assertEqual(found, [(0.1, 0.4, "eh"), (0.5, 0.9, "vale")])

    def test_27_crown_setting_is_checked(self):
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import settings
        here = os.getcwd()
        os.chdir(self.dir)
        try:
            Path("retouch.json").write_text(json.dumps({"crown": {"grow": [1.45, 1.30], "raise": 0.36}}), "utf-8")
            self.assertEqual(settings.load()["crown"]["raise"], 0.36)
            Path("retouch.json").write_text(json.dumps({"crown": {"grow": [1.45]}}), "utf-8")
            with self.assertRaises(SystemExit):
                settings.load()
            Path("retouch.json").unlink()
        finally:
            os.chdir(here)

    def test_30_beautify_presets_and_overrides(self):
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import settings
        here = os.getcwd()
        os.chdir(self.dir)
        try:
            Path("retouch.json").write_text(json.dumps({"beautify": "light", "skin_strength": 0.3}), "utf-8")
            loaded = settings.load()
            self.assertEqual((loaded["glow"], loaded["skin_strength"]), (0.012, 0.3))  # the file wins over the preset
            Path("retouch.json").write_text(json.dumps({"beautify": "heavy"}), "utf-8")
            with self.assertRaises(SystemExit):
                settings.load()
            Path("retouch.json").write_text(json.dumps({"beautify": "off"}), "utf-8")
            self.assertEqual(settings.load()["glow"], 0.0)
            Path("retouch.json").unlink()
        finally:
            os.chdir(here)

    def test_31_beautify_filter_runs(self):
        folder = self.dir / "beauty"
        folder.mkdir(exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=320x240:r={FPS}:d=0.5", "-c:v", "libx264",
             "-preset", "ultrafast", "retouched.mp4"], cwd=folder)
        for name in ("skin", "undereye", "eyewhite"):
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=gray:s=320x240:r={FPS}:d=0.5", "-pix_fmt", "gray",
                 "-c:v", "ffv1", f"{name}.mkv"], cwd=folder)
        (folder / "retouch.json").write_text(json.dumps({"beautify": "off"}), "utf-8")
        self.assertIn("Nothing to add", script("retouch/beautify.py", cwd=folder))
        self.assertFalse((folder / "beautify.txt").exists())
        (folder / "retouch.json").write_text(json.dumps({"beautify": "medium"}), "utf-8")
        out = script("retouch/beautify.py", cwd=folder)
        self.assertIn("glow, under, white", out)
        run(["ffmpeg", "-v", "error", "-y", "-i", "retouched.mp4", "-i", "skin.mkv", "-i", "undereye.mkv", "-i", "eyewhite.mkv",
             filter_flag(), "beautify.txt", "-map", "[v]", "-frames:v", "5", "-c:v", "libx264", "-preset", "ultrafast",
             "beautified.mp4"], cwd=folder)
        (folder / "retouch.json").write_text(json.dumps({"glow": 0.02}), "utf-8")
        script("retouch/beautify.py", cwd=folder)
        self.assertNotIn("undereye", (folder / "beautify.txt").read_text("utf-8"))  # only the extras that are on

    def test_32_eye_masks_sit_where_they_should(self):
        try:
            import cv2  # noqa: F401
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV not installed")
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import beauty
        pts = np.full((478, 2), 50.0, np.float32)
        for k, eye in enumerate(beauty.EYES):
            cx = 60.0 + 100 * k
            for j, i in enumerate(beauty.EYE_OUTLINE[k]):              # the eye opening: an ellipse
                angle = 2 * np.pi * j / len(beauty.EYE_OUTLINE[k])
                pts[i] = (cx + 20 * np.cos(angle), 60 + 5 * np.sin(angle))
            for j, i in enumerate(eye["lower"]):                        # then the lower lid, left to right
                pts[i] = (cx - 20 + 5 * j, 64 - 0.15 * (j - 4) ** 2 + 2)
            pts[eye["corners"][0]], pts[eye["corners"][1]] = (cx - 20, 60), (cx + 20, 60)
            pts[eye["iris"][0]] = (cx, 60)
            for j, i in enumerate(eye["iris"][1:]):
                pts[i] = (cx + 4 * np.cos(j * np.pi / 2), 60 + 4 * np.sin(j * np.pi / 2))
        shape = (120, 260)
        under = beauty.under_eye(pts, shape)
        self.assertGreater(int(under[72, 60]), 100)            # just below the first eye
        self.assertLess(int(under[60, 60]), 10)                # not inside the eye (a faint soft edge is fine)
        self.assertEqual(int(under[10, 60]), 0)                # nothing far above
        self.assertGreater(int(under[72, 160]), 100)           # the second eye too
        frame = np.full((120, 260, 3), 200, np.uint8)
        luma = np.full(shape, 200, np.float32)
        luma[56:64, 50:70] = 40                                # a dark iris
        white = beauty.eye_whites(frame, luma, pts, shape)
        self.assertEqual(white.shape, shape)
        self.assertEqual(int(white[60, 60]), 0)                # the iris is never whitened
        big = pts.copy()                                       # a close-up: an eye 24 px high, as real whites are
        for k in range(2):
            for j, i in enumerate(beauty.EYE_OUTLINE[k]):
                angle = 2 * np.pi * j / len(beauty.EYE_OUTLINE[k])
                big[i] = (60.0 + 100 * k + 20 * np.cos(angle), 60 + 12 * np.sin(angle))
        luma = np.full(shape, 200, np.float32)
        luma[56:64, 50:70] = 40
        luma[58:62, 72:76] = 150                               # a grey spot in the white (3/4 as bright): evened, not skipped
        luma[55:57, 78:84] = 40                                # a lash lying over the white: left alone
        white = beauty.eye_whites(frame, luma, big, shape)
        self.assertGreater(int(white[60, 74]), 200)            # the whole white is covered, spots and shadows too
        self.assertGreater(int(white[64, 72]), 200)
        self.assertEqual(int(white[56, 81]), 0)                # but not a lash
        self.assertEqual(int(white[60, 60]), 0)                # still never the iris

    # ---- updating the skill for people who don't use Git ------------------------------------

    def _release_zip(self, version="2.0.0"):
        """A ZIP shaped like GitHub's download of the repository, built from this working tree."""
        import zipfile
        archive = self.dir / "release.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("video-editor-skill-main/CHANGELOG.md", "# Changelog\n\n## newest\n- something new\n")
            for path in ROOT.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts and path.name != "my-setup.md":
                    rel = path.relative_to(REPO).as_posix()
                    data = (version + "\n").encode() if path.name == "VERSION" else path.read_bytes()
                    z.writestr("video-editor-skill-main/" + rel, data)
        return archive

    def _installed_copy(self, name, version="1.0.0"):
        home = self.dir / name
        skill = home / "video-editor"
        shutil.copytree(ROOT, skill, ignore=shutil.ignore_patterns("__pycache__", "my-setup.md"))
        (skill / "VERSION").write_text(version + "\n", "utf-8")
        return home, skill

    def _update(self, skill, home, *args, check=True):
        cmd = [sys.executable, "-I", SCRIPTS / "update_skill.py", "--skill-dir", skill, "--source", self._release_zip(),
               "--backup-dir", home / "backups", "--settings-dir", home / "settings", *args]
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8")
        if check and r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return r

    def test_34_update_backs_up_replaces_and_keeps_settings(self):
        home, skill = self._installed_copy("upd1")
        (skill / "my-setup.md").write_text("# my settings\n", "utf-8")       # where older versions kept it
        (skill / "references" / "log.md").write_text("changed by hand\n", "utf-8")
        out = self._update(skill, home).stdout
        self.assertIn("1.0.0 -> 2.0.0", out)
        self.assertEqual((skill / "VERSION").read_text("utf-8").strip(), "2.0.0")
        self.assertNotEqual((skill / "references" / "log.md").read_text("utf-8"), "changed by hand\n")
        backups = list((home / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "references" / "log.md").read_text("utf-8"), "changed by hand\n")  # nothing lost
        self.assertEqual((home / "settings" / "my-setup.md").read_text("utf-8"), "# my settings\n")   # settings moved out
        self.assertFalse((skill / "my-setup.md").exists())
        self.assertIn("can't tell", out)            # first install by this script: no record of what was changed by hand
        self.assertIn("something new", out)          # the changelog is shown
        # the next update knows what was changed by hand
        (skill / "references" / "log.md").write_text("changed again\n", "utf-8")
        again = self._update(skill, home, "--force").stdout
        self.assertIn("references/log.md", again)
        self.assertEqual(len(list((home / "backups").iterdir())), 2)

    def test_35_update_does_nothing_when_current_and_reports_with_check(self):
        home, skill = self._installed_copy("upd2", version="2.0.0")
        out = self._update(skill, home).stdout
        self.assertIn("up to date", out)
        self.assertFalse((home / "backups").exists())
        old_home, old_skill = self._installed_copy("upd3", version="1.0.0")
        self.assertIn("An update is available", self._update(old_skill, old_home, "--check").stdout)
        self.assertEqual((old_skill / "VERSION").read_text("utf-8").strip(), "1.0.0")  # --check changes nothing

    def test_37_weekly_check_is_quiet_unless_there_is_news(self):
        home, skill = self._installed_copy("upd5", version="1.0.0")
        first = self._update(skill, home, "--weekly").stdout
        self.assertIn("newer version", first)
        self.assertEqual(self._update(skill, home, "--weekly").stdout.strip(), "")        # checked today: silent
        stamp = home / "settings" / "last-update-check"
        stamp.write_text("0", "utf-8")                                                      # a long time ago
        self.assertIn("newer version", self._update(skill, home, "--weekly").stdout)
        current_home, current = self._installed_copy("upd6", version="2.0.0")
        self.assertEqual(self._update(current, current_home, "--weekly").stdout.strip(), "")  # up to date: silent
        self.assertEqual((skill / "VERSION").read_text("utf-8").strip(), "1.0.0")            # a check changes nothing
        self.assertFalse((home / "backups").exists())

    def test_70_a_linked_clone_is_told_to_git_pull(self):
        # a developer's setup: the skill sits deep inside a Git clone (plugins/video-editor/skills/video-editor)
        home = self.dir / "dev"
        clone = home / "clone"
        skill = clone / "plugins" / "video-editor" / "skills" / "video-editor"
        shutil.copytree(ROOT, skill, ignore=shutil.ignore_patterns("__pycache__", "my-setup.md"))
        (skill / "VERSION").write_text("1.0.0\n", "utf-8")
        (clone / ".git").mkdir()
        weekly = self._update(skill, home, "--weekly").stdout
        self.assertIn("newer version", weekly)
        self.assertIn("git pull", weekly)
        self.assertIn(str(clone), weekly)                     # names the clone, not the skill folder inside it
        check = self._update(skill, home, "--check").stdout
        self.assertIn("git pull", check)
        self.assertNotIn("plugin marketplace add", check)     # not offered the move to the plugin
        refused = self._update(skill, home, check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("git pull", refused.stderr)
        self.assertEqual((skill / "VERSION").read_text("utf-8").strip(), "1.0.0")  # nothing replaced
        self.assertFalse((home / "backups").exists())
        # a plain copy is not told to git pull
        plain_home, plain = self._installed_copy("plain", version="1.0.0")
        self.assertNotIn("git pull", self._update(plain, plain_home, "--weekly").stdout)

    def test_71_work_folder_check(self):
        def folder(*args, env=None):
            e = {k: v for k, v in os.environ.items() if not k.lower().startswith("onedrive")}
            e.update(env or {})
            return subprocess.run([sys.executable, "-I", str(SCRIPTS / "detect_setup.py"), "folder", *map(str, args)],
                                  capture_output=True, text=True, encoding="utf-8", env=e)
        plain = self.dir / "work" / "plain"
        r = folder(plain)
        self.assertIn("OK", r.stdout)
        self.assertNotIn("NOT OK", r.stdout)
        self.assertFalse(plain.exists())                                   # it creates nothing
        for name, service in (("OneDrive - Company", "OneDrive"), ("Dropbox", "Dropbox"),
                              ("iCloudDrive", "iCloud"), ("Google Drive", "Google Drive")):
            r = folder(self.dir / name / "video")
            self.assertIn("NOT OK", r.stdout)
            self.assertIn("inside " + service, r.stdout)
        data = json.loads(folder(self.dir / "Dropbox" / "x", "--json").stdout)
        self.assertEqual(data["synced_service"], "Dropbox")
        self.assertFalse(data["ok"])
        synced = self.dir / "odroot"
        data = json.loads(folder(synced / "videos", "--json", env={"OneDrive": str(synced)}).stdout)
        self.assertEqual(data["synced_service"], "OneDrive")               # found through the OneDrive variable
        suggested = json.loads(folder("--json").stdout)
        self.assertTrue(suggested["suggested"])
        self.assertTrue(suggested["path"].endswith("video-work"))
        skill = (ROOT / "SKILL.md").read_text("utf-8")
        self.assertIn("detect_setup.py folder", skill)                     # the setup asks for and checks the folder
        self.assertIn("working files", skill)

    def test_72_pixelate_other_faces(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy not installed")
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import pixelfaces
        # two faces move across 40 frames; the small one is lost for 3 frames; a 2-frame blip is not a face
        frames = []
        for n in range(40):
            row = [[100 + n, 100, 300 + n, 300]]                       # the speaker, 200 px
            if not 15 <= n < 18:
                row.append([700 - n, 120, 780 - n, 200])               # someone else, 80 px
            if n in (5, 6):
                row.append([10, 10, 30, 30])                           # a blip
            frames.append(row)
        tracks = pixelfaces.build_tracks(frames, max_lost=10)
        self.assertEqual(len(tracks), 2)
        speaker = pixelfaces.pick_speaker(tracks)
        other = [t for t in tracks if t["id"] != speaker][0]
        self.assertEqual(len(tracks[speaker]["boxes"]) if tracks[0]["id"] == speaker else len(tracks[1]["boxes"]), 40)
        self.assertEqual(len(other["boxes"]), 37)
        filled = pixelfaces.fill_track(other["boxes"], 40, gap=5, hold=2)
        self.assertFalse(numpy.isnan(filled[16]).any())                 # the lost frames are bridged
        self.assertLess(filled[16][0], filled[14][0])                   # and the box keeps moving
        self.assertFalse(numpy.isnan(filled[0]).any())                  # held before the first sighting
        long_gap = pixelfaces.fill_track({0: [0, 0, 10, 10], 20: [0, 0, 10, 10]}, 40, gap=5, hold=0)
        self.assertTrue(numpy.isnan(long_gap[10]).all())                # a long loss is not guessed at
        squares = pixelfaces.tiles(1280, 720)                           # small faces: the frame is searched in squares too
        self.assertEqual([s[2] for s in squares], [720] * len(squares))
        self.assertTrue(all(0 <= x and x + s <= 1280 and 0 <= y and y + s <= 720 for x, y, s in squares))
        self.assertEqual(max(x for x, y, s in squares) + 720, 1280)       # the last square reaches the edge
        self.assertGreater(len(pixelfaces.tiles(1280, 720, thorough=True)), 4 * len(squares))
        self.assertEqual(len(pixelfaces.tiles(1080, 1920)), 3)            # a vertical video: three squares down
        merged = pixelfaces.merge_boxes([[100, 100, 200, 200], [105, 98, 198, 205], [600, 100, 650, 150]])
        self.assertEqual(len(merged), 2)                                 # one face seen twice is kept once
        grown = pixelfaces.mask_frame([[10, 10, 50, 50]], 200, 100, 16)  # snapped out to whole squares
        self.assertTrue((grown[0:64, 0:64] == 255).all())
        self.assertEqual(int(grown.sum()) // 255, 64 * 64)
        # the whole chain on a real video: a mask from the tracks, applied with the command build prints
        work = self.dir / "pix"
        work.mkdir()
        src = work / "clean.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=2",
                        "-pix_fmt", "yuv420p", str(src)], check=True)
        boxes = {str(n): [60.0, 60.0, 180.0, 200.0] for n in range(50)}
        far = {str(n): [420.0, 80.0, 500.0, 170.0] for n in range(50)}
        (work / "pixelfaces.json").write_text(json.dumps({
            "video": "clean.mp4", "width": 640, "height": 360, "fps": 25.0, "frames": 50, "speaker": 0,
            "tracks": [{"id": 0, "boxes": boxes}, {"id": 1, "boxes": far}]}), "utf-8")
        run = lambda *args: subprocess.run([sys.executable, "-I", str(SCRIPTS / "retouch" / "pixelfaces.py"), *args],
                                          cwd=work, capture_output=True, text=True, encoding="utf-8")
        built = run("build", "clean.mp4")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertTrue((work / "pixmask.mkv").exists())
        graph = re.search(r'-filter_complex "([^"]+)"', built.stdout).group(1)
        block = int(re.search(r"pixelize=w=(\d+)", graph).group(1))
        gray = lambda *args: numpy.frombuffer(subprocess.run(
            ["ffmpeg", "-v", "error", *args, "-frames:v", "1", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
            cwd=work, capture_output=True, check=True).stdout, numpy.uint8).reshape(360, 640)
        a = gray("-i", "clean.mp4", "-i", "pixmask.mkv", "-filter_complex", graph, "-map", "[v]")
        b = gray("-i", "clean.mp4")
        squares = gray("-i", "clean.mp4", "-vf", f"pixelize=w={block}:h={block}")
        mask = gray("-i", "pixmask.mkv")
        self.assertTrue((mask[60:200, 60:180] == 0).all())                    # nothing is pixelated on the speaker
        self.assertTrue((a[mask == 0] == b[mask == 0]).all())                 # outside the mask: the source, bit for bit
        self.assertTrue((a[mask == 255] == squares[mask == 255]).all())       # inside: fully pixelated, none of the original
        self.assertFalse((a[80:170, 420:500] == b[80:170, 420:500]).all())    # and it did change
        # a 10-bit render stays 10-bit
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "clean.mp4", "-pix_fmt", "yuv420p10le", "ten.mkv"],
                       cwd=work, check=True)
        ten = run("build", "ten.mkv").stdout
        self.assertIn("yuva420p10le", ten)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "ten.mkv", "-i", "pixmask.mkv", "-filter_complex",
                        re.search(r'-filter_complex "([^"]+)"', ten).group(1), "-map", "[v]", "-frames:v", "2",
                        "ten-out.mkv"], cwd=work, check=True)
        # a bad pixel_extra is refused
        (work / "retouch.json").write_text(json.dumps({"pixel_extra": [{"start": 1}]}), "utf-8")
        self.assertNotEqual(run("build", "clean.mp4").returncode, 0)
        self.assertIn("pixelfaces.py", (ROOT / "SKILL.md").read_text("utf-8"))

    def test_73_second_camera_matches_the_main_one(self):
        sys.path.insert(0, str(SCRIPTS))
        import conform
        cam = {"width": 1920, "height": 1080, "fps": Fraction(25), "variable": False, "pix_fmt": "yuv420p",
               "transfer": "bt709", "primaries": "bt709", "matrix": "bt709", "rate": 48000, "channels": 2}
        phone = dict(cam, fps=Fraction(30), variable=True, transfer="arib-std-b67", primaries="bt2020",
                     matrix="bt2020nc", rate=44100, channels=1, width=3840, height=2160)
        notes, vf, af, tags = conform.plan(cam, phone)
        self.assertIn("tonemap", vf)                                     # HDR to SDR
        self.assertIn("fps=25", vf)
        self.assertIn("scale=1920:1080", vf)
        self.assertEqual(af, "aresample=48000")
        self.assertEqual(tags["color_trc"], "bt709")
        self.assertEqual(len(notes), 4)
        notes, vf, _, tags = conform.plan(cam, phone, zscale=False)      # no zscale: said, not hidden
        self.assertNotIn("tonemap", vf)
        self.assertTrue(any("NOT converted" in n for n in notes))
        wobbly = dict(cam, variable=True)                                # same rate, but variable: made constant
        notes, vf, _, _ = conform.plan(cam, wobbly)
        self.assertEqual(len(notes), 1)
        self.assertIn("constant", notes[0])
        self.assertEqual(conform.plan(cam, dict(cam))[0], [])            # already the same: nothing to do
        upright = dict(cam, width=1080, height=1920)
        self.assertIn("crop=1920:1080", conform.plan(cam, upright)[1])
        self.assertIn("pad=1920:1080", conform.plan(cam, upright, fit="pad")[1])
        # on real files
        work = self.dir / "conform"
        work.mkdir()
        ff = lambda *args: subprocess.run(["ffmpeg", "-v", "error", "-y", *args], cwd=work, check=True)
        ff("-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=2", "-f", "lavfi", "-i", "sine=f=440:r=48000:d=2",
           "-ac", "2", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-c:a", "aac", "main.mp4")
        ff("-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=2", "-f", "lavfi", "-i", "sine=f=440:r=44100:d=2",
           "-ac", "1", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-color_primaries", "bt2020",
           "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc", "-c:a", "aac", "phone.mov")
        run = lambda *args: subprocess.run([sys.executable, "-I", str(SCRIPTS / "conform.py"), *args], cwd=work,
                                          capture_output=True, text=True, encoding="utf-8")
        checked = run("phone.mov", "--like", "main.mp4", "--check")
        self.assertIn("30 -> 25", checked.stdout)
        self.assertFalse((work / "phone-conformed.mov").exists())        # --check writes nothing
        made = run("phone.mov", "--like", "main.mp4")
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        out = conform.probe(str(work / "phone-conformed.mov"))
        self.assertEqual((out["width"], out["height"], out["fps"], out["rate"], out["channels"]), (640, 360, 25, 48000, 2))
        self.assertFalse(out["variable"])
        self.assertAlmostEqual(out["duration"], 2.0, delta=0.15)
        if conform.has_filter("zscale"):
            self.assertEqual(out["transfer"], "bt709")
            luma = subprocess.run(["ffmpeg", "-v", "error", "-i", "phone-conformed.mov", "-frames:v", "1", "-pix_fmt",
                                   "gray", "-f", "rawvideo", "-"], cwd=work, capture_output=True, check=True).stdout
            mean = sum(luma) / len(luma)
            self.assertTrue(30 < mean < 220, mean)                       # tone mapped, not black or blown out
        self.assertIn("nothing to change", run("main.mp4", "--like", "main.mp4").stdout)
        self.assertNotEqual(run("main.mp4", "--like", "phone.mov", "--out", "main.mp4").returncode, 0)  # never overwrites

    def test_74_teleprompter_is_asked_not_assumed(self):
        setup = (ROOT / "setup-template.md").read_text("utf-8")
        self.assertIn("Teleprompter: <not asked yet", setup)
        self.assertIn("Second camera: <not asked yet", setup)               # how they film with two cameras: asked too
        self.assertIn("Ask once how they film", (ROOT / "references" / "cameras.md").read_text("utf-8"))
        script = (ROOT / "references" / "script.md").read_text("utf-8")
        self.assertIn("Don't assume one", script)
        self.assertIn("teleprompter.txt", script)
        self.assertIn("teleprompter-iphone.txt", script)               # one file per camera when both have one
        self.assertIn("from the side, while they keep reading", script)  # a side angle still reads every line

    def test_75_second_camera_at_the_same_time(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed")
        import wave
        work = self.dir / "sync"
        work.mkdir()

        def speechy(seconds, seed):                                   # syllable-like bursts, like speech
            r = np.random.default_rng(seed)
            n = int(seconds * 48000)
            env, t = np.zeros(n), 0
            while t < n:
                length = int(r.uniform(.08, .25) * 48000)
                env[t:t + length] = np.hanning(length)[:len(env[t:t + length])] * r.uniform(.3, 1)
                t += length + int(r.uniform(.05, .4) * 48000)
            return env * (np.sin(2 * np.pi * np.cumsum(r.uniform(120, 220, n)) / 48000) + .3 * r.standard_normal(n)) * .3

        def save(name, x):
            with wave.open(str(work / name), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(48000)
                w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

        main = speechy(20, 1)
        save("main.wav", main)
        other_mic = lambda x: np.convolve(x, np.ones(8) / 8, mode="same") * .5 + .01 * np.random.default_rng(2).standard_normal(len(x))
        save("phone.wav", other_mic(main[int(6.3 * 48000):int(14.3 * 48000)]))            # starts at 6.3 s
        save("early.wav", other_mic(np.concatenate([speechy(1, 5), main[:5 * 48000]])))   # started 1 s before the main one
        save("other.wav", speechy(8, 99))                                                  # another take altogether
        ff = lambda *args: subprocess.run(["ffmpeg", "-v", "error", "-y", *args], cwd=work, check=True)
        ff("-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=20", "-i", "main.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", "main.mp4")
        for name, colour, seconds in (("phone", "red", 8), ("early", "green", 6), ("other", "blue", 8)):
            ff("-f", "lavfi", "-i", f"color=c={colour}:s=320x180:r=25:d={seconds}", "-i", f"{name}.wav", "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", f"{name}.mp4")
        run = lambda *args: subprocess.run([sys.executable, "-I", str(SCRIPTS / "syncclip.py"), *args], cwd=work,
                                          capture_output=True, text=True, encoding="utf-8")
        found = run("find", "main.mp4", "phone.mp4", "early.mp4", "other.mp4")
        self.assertEqual(found.returncode, 0, found.stdout + found.stderr)
        angles = json.loads((work / "angles.json").read_text("utf-8"))["angles"]
        offsets = {a["clip"]: a["offset"] for a in angles}
        self.assertAlmostEqual(offsets["phone.mp4"], 6.3, delta=0.01)      # found to the frame and better
        self.assertAlmostEqual(offsets["early.mp4"], -1.0, delta=0.01)     # a clip that started first
        self.assertNotIn("other.mp4", offsets)                             # another take is not trusted
        self.assertIn("NOT SURE", found.stdout)
        phone = next(a for a in angles if a["clip"] == "phone.mp4")
        self.assertAlmostEqual(phone["from"], 7.32, delta=0.001)           # the margin, rounded inwards to whole frames
        built = run("build", "main.mp4")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)

        def colour_at(t):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", "angles.mov", "-frames:v", "1",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], cwd=work, capture_output=True).stdout
            return np.frombuffer(raw, np.uint8).reshape(-1, 3).mean(axis=0)
        self.assertGreater(colour_at(10)[0], 200)                          # the iPhone's picture in its stretch
        self.assertLess(colour_at(7.24)[0], 200)                           # the main camera's just before it
        self.assertLess(colour_at(16)[0], 200)                             # and after it
        self.assertGreater(colour_at(2)[1], 100)                           # the early clip, from 0 s on
        pcm = lambda f: subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-map", "0:a", "-f", "s16le", "-"], cwd=work,
                                       capture_output=True).stdout
        self.assertEqual(pcm("angles.mov"), pcm("main.mp4"))               # the main camera's sound, untouched
        ff("-f", "lavfi", "-i", "color=c=red:s=640x360:r=25:d=8", "-i", "phone.wav", "-c:v", "libx264", "-shortest", "big.mp4")
        (work / "big.json").write_text(json.dumps({"main": "main.mp4", "angles": [
            {"clip": "big.mp4", "offset": 6.3, "from": 7, "to": 9}]}), "utf-8")
        refused = run("build", "main.mp4", "--angles", "big.json", "--out", "x.mov")
        self.assertNotEqual(refused.returncode, 0)                         # a clip of another size: conform first
        self.assertIn("conform.py", refused.stderr)

    def test_76_animated_explanation(self):
        sys.path.insert(0, str(SCRIPTS))
        import explainer
        said = ("os enseño cómo funciona un MCP . Por un lado está Claude . Y por otro un servidor MCP . "
                "Claude le pide algo al servidor . y este habla con tu Gmail . y vuelve con la respuesta . y así de fácil").split()
        t, words = 40.0, []
        for w in said:
            if w == ".":
                t += 0.5
                continue
            words.append([round(t, 2), round(t + 0.3, 2), w])
            t += 0.35
        captions = [{"start": words[i][0], "end": words[min(i + 5, len(words) - 1)][1],
                     "text": " ".join(x[2] for x in words[i:i + 6]), "words": words[i:i + 6]} for i in range(0, len(words), 6)]
        when = lambda word: next(w[0] for w in words if w[2] == word)
        spec = {"title": "Cómo funciona un MCP", "start_say": "os enseño", "end_say": "y así de fácil",
                "nodes": [{"id": "claude", "label": "Claude", "icon": "🤖", "say": "está Claude"},
                          {"id": "mcp", "label": "Servidor MCP", "say": "un servidor MCP"},
                          {"id": "gmail", "label": "Gmail", "say": "tu Gmail"},
                          {"id": "drive", "label": "Drive", "say": "tu Drive"}],             # never said
                "links": [{"from": "claude", "to": "mcp", "label": "pide", "say": "le pide"},
                          {"from": "mcp", "to": "gmail", "label": "conecta", "say": "habla con"}],
                "flows": [{"path": ["claude", "mcp", "gmail", "mcp", "claude"], "say": "y vuelve"}]}
        style = {"font": "sans-serif", "fontFile": "", "background": "#1B1033", "background2": "#0E2A47",
                 "accentColor": "#FF4F8B", "lineColor": "#FFFFFF"}
        props, start, timeline, problems, mode = explainer.build_props(spec, captions, 1920, 1080, 25, style)
        self.assertEqual((start, mode), (when("os"), "row"))
        frames = {n["id"]: n["frame"] for n in props["nodes"]}
        self.assertEqual(frames["claude"], round((when("está") - start - explainer.LEAD) * 25))  # a beat before it's named
        self.assertEqual(frames["drive"], frames["gmail"] + round(explainer.GAP * 25))  # not said: just after the one before
        self.assertTrue(any("tu Drive" in p for p in problems))
        link = props["links"][1]
        self.assertGreaterEqual(link["frame"], frames["gmail"])                       # never before its boxes
        self.assertGreaterEqual(props["flows"][0]["frame"], max(frames[i] for i in ("claude", "mcp", "gmail")))  # after its path
        said_end = words[[w[2] for w in words].index("así") - 1][0]                 # "y así de fácil" starts at its "y"
        self.assertAlmostEqual(props["seconds"], said_end - start, delta=0.01)       # ends where the end phrase is said
        colours = [n["color"] for n in props["nodes"]]
        self.assertEqual(len(set(colours)), len(colours))                            # each box its own colour
        self.assertEqual(explainer.readable_text("#FF4F8B"), "#FFFFFF")              # white on pink and violet...
        self.assertEqual(explainer.readable_text("#7C5CFF"), "#FFFFFF")
        self.assertEqual(explainer.readable_text("#22C3A6"), "#1A1A1A")              # ...dark on light teal and amber
        self.assertEqual(explainer.readable_text("#FFB020"), "#1A1A1A")
        boxes = sorted(props["nodes"], key=lambda n: n["x"])
        for n in boxes:                                                               # inside the frame
            self.assertTrue(0 <= n["x"] - n["w"] / 2 and n["x"] + n["w"] / 2 <= 1920 and 0 <= n["y"] - n["h"] / 2)
        for a, b in zip(boxes, boxes[1:]):                                            # room for an arrow and its label
            self.assertGreater((b["x"] - b["w"] / 2) - (a["x"] + a["w"] / 2), props["fontSize"] * 2)
        for l in props["links"]:                                                      # arrows start and end outside the boxes
            a = next(n for n in props["nodes"] if n["id"] == l["from"])
            self.assertGreater(abs(l["x1"] - a["x"]), a["w"] / 2)
        tall, _, _, _, tall_mode = explainer.build_props(spec, captions, 1080, 1920, 25, style)
        self.assertEqual(tall_mode, "column")
        self.assertEqual(tall["labelSide"], "right")
        self.assertEqual(len({n["x"] for n in tall["nodes"]}), 1)                     # one column, centred
        with self.assertRaises(ValueError):                                           # an arrow to a box that isn't there
            explainer.build_props(dict(spec, links=[{"from": "claude", "to": "slack"}]), captions, 1920, 1080, 25, style)
        with self.assertRaises(ValueError):                                           # too many boxes to read
            explainer.build_props(dict(spec, nodes=[{"id": str(i), "label": str(i)} for i in range(7)], links=[], flows=[]),
                                  captions, 1920, 1080, 25, style)
        # the template draws exactly what the script writes
        tsx = (SCRIPTS / "remotion" / "Explainer.tsx").read_text("utf-8")
        default_props = next(l for l in tsx.splitlines() if "defaultProps=" in l)
        self.assertIn("nodes: [], links: [], flows: []", default_props)            # sample boxes would leak into videos
        for key in list(props["nodes"][0]) + list(props["links"][0]) + list(props["flows"][0]):
            self.assertRegex(tsx, rf"\b{key}\??:", key)
        for key in props:
            if key not in ("nodes", "links", "flows"):
                self.assertRegex(tsx, rf"\b{key}\??:", key)
        (self.dir / "ex.json").write_text(json.dumps(spec, ensure_ascii=False), "utf-8")
        (self.dir / "ex-caps.json").write_text(json.dumps(captions, ensure_ascii=False), "utf-8")
        out = script("explainer.py", "ex.json", "--captions", "ex-caps.json", "--out", "ex-props.json",
                     "--sounds", "ex-sfx.wav", "--size", "1920x1080", "--fps", "25", cwd=self.dir)
        self.assertIn("box \"Claude\"", out)
        self.assertIn("remotion render", out)
        self.assertTrue((self.dir / "ex-props.json").exists())
        # sound effects timed to the picture: a pop per box, a whoosh per arrow, the dot's trip and arrivals
        events = explainer.sound_events(props)
        kinds = [k for _, k in events]
        self.assertEqual(kinds.count("box"), len(props["nodes"]))
        self.assertEqual(kinds.count("arrow"), len(props["links"]))
        self.assertEqual(kinds.count("arrive"), 1)
        self.assertEqual(kinds.count("reach"), len(props["flows"][0]["points"]) - 2)
        pop = next(t for t, k in events if k == "box")
        self.assertAlmostEqual(pop, props["nodes"][0]["frame"] / 25, places=3)        # on the box's frame
        flow = props["flows"][0]
        arrive = next(t for t, k in events if k == "arrive")
        self.assertAlmostEqual(arrive, (flow["frame"] + flow["frames"]) / 25, places=3)  # when the dot gets home
        subtle_count = sum(1 for _, k in events if k in explainer.SOUND_STYLES["subtle"])
        self.assertEqual(subtle_count, len(props["nodes"]) + 1)                       # subtle: a pop per box, one sparkle
        self.assertNotIn("arrow", explainer.SOUND_STYLES["subtle"])                   # never a whoosh under the arrows
        import wave
        import array
        whoosh_wav = self.dir / "whoosh-test.wav"
        explainer.write_sounds([(1.0, "arrow")], 2.0, str(whoosh_wav), style="lively")
        with wave.open(str(whoosh_wav)) as w:
            mixed = array.array("h", w.readframes(w.getnframes()))
        loudest = max(range(len(mixed)), key=lambda i: abs(mixed[i])) // 2 / 48000
        self.assertAlmostEqual(loudest, 1.0, delta=0.005)                             # its loudest moment on its cause
        wav = self.dir / "ex-sfx.wav"
        self.assertTrue(wav.exists())                                                 # written by the run above
        with wave.open(str(wav)) as w:
            self.assertEqual(w.getframerate(), 48000)
            self.assertAlmostEqual(w.getnframes() / 48000, props["seconds"], delta=0.05)  # as long as the graphic
            samples = array.array("h", w.readframes(w.getnframes()))
        loud = lambda sec: max(abs(v) for v in samples[int(sec * 48000) * 2:int((sec + 0.1) * 48000) * 2])
        self.assertGreater(loud(pop), 1000)                                           # a pop where the box appears
        self.assertLess(loud(0.2), 50)                                                # silence before anything happens
        guide = (ROOT / "references" / "script.md").read_text("utf-8")
        self.assertIn("Propose the animated explanations yourself", guide)          # proposed when writing, not asked for
        self.assertIn("name each piece once", guide)                                  # so the voice brings each box in

    def test_77_parakeet_engine(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed")
        sys.path.insert(0, str(SCRIPTS))
        import asr
        import asrcompare
        # Parakeet's pieces of words: a leading space starts a word, punctuation stays with its word
        tokens = [" H", "ola", ",", " ho", "y", " os", " en", "se", "ño"]
        times = [0.0, 0.24, 0.32, 0.48, 0.56, 0.72, 0.96, 1.04, 1.2]
        words = asr.parakeet_words(tokens, times, offset=10.0, end=2.5)
        self.assertEqual([w[2] for w in words], ["Hola,", "hoy", "os", "enseño"])
        self.assertEqual(words[0][0], 10.0)                                       # offset of the piece added
        self.assertEqual(words[0][1], 10.48)                                      # ends where the next word starts
        self.assertAlmostEqual(words[-1][1], 11.8)                                # 0.6 s after its last piece: the pause isn't part of it
        gap = asr.parakeet_words([" a", " b"], [0.0, 5.0])
        self.assertEqual(gap[0][1], 0.6)                                          # a word before a long pause stops at 0.6 s
        # long audio is cut at a quiet moment, never inside speech
        rate = 16000
        rng = np.random.default_rng(0)
        audio = (rng.standard_normal(150 * rate) * 0.3).astype(np.float32)
        audio[52 * rate:int(52.4 * rate)] = 0                                     # a pause at 52 s
        pieces = asr.quiet_splits(audio, rate, longest=60)
        self.assertEqual(pieces[0][0], 0)
        self.assertEqual(pieces[-1][1], len(audio))
        self.assertTrue(all(b - a <= 60 * rate for a, b in pieces))
        self.assertTrue(52 * rate <= pieces[0][1] <= 52.4 * rate)                 # the first cut falls in the pause
        # where speech really starts, measured on the sound, and how far an engine's word starts are from it
        voice = np.zeros(6 * rate, np.float32)
        voice[int(0.5 * rate):2 * rate] = 0.3
        voice[int(3.0 * rate):5 * rate] = 0.3
        self.assertEqual(asrcompare.speech_starts(voice, rate), [0.5, 3.0])
        errors = asrcompare.start_error([0.55, 2.9, 4.0], [0.5, 3.0])
        self.assertEqual([round(e, 2) for e in errors], [0.05, -0.1])
        self.assertNotIn("este", asrcompare.FILLERS)                              # an ordinary word too
        for name in ("hear.py", "checkcuts.py", "hunt_fillers.py"):               # every script that picks an engine offers it
            self.assertIn('"parakeet"', (SCRIPTS / name).read_text("utf-8"))
        self.assertIn('choices=["whisper", "parakeet"]', (SCRIPTS / "transcribe.py").read_text("utf-8"))
        self.assertIn("Transcription engine:", (ROOT / "setup-template.md").read_text("utf-8"))

    def test_78_export_check(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy not installed")
        work = self.dir / "chk"
        work.mkdir()
        ff = lambda *args: subprocess.run(["ffmpeg", "-v", "error", "-y", *args], cwd=work, check=True)
        tag = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"   # as the final export does
        tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
        ff("-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=4", "-f", "lavfi", "-i", "sine=f=300:r=48000:d=4",
           "-vf", tag, "-c:v", "libx264", "-pix_fmt", "yuv420p", *tags, "-c:a", "aac", "clean.mp4")
        # a plain jump cut (one picture, then another) is not a flash
        ff("-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=2", "-f", "lavfi", "-i", "smptebars=s=320x180:r=25:d=2",
           "-f", "lavfi", "-i", "sine=f=300:r=48000:d=4", "-filter_complex", f"[0:v][1:v]concat=n=2:v=1:a=0,{tag}[v]",
           "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", *tags, "-c:a", "aac", "jump.mp4")
        ff("-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=4", "-f", "lavfi", "-i", "sine=f=300:r=48000:d=3.5",
           "-vf", "drawbox=enable='between(n,40,42)':color=black:t=fill,drawbox=enable='eq(n,70)':color=white:t=fill",
           "-af", "volume=enable='between(t,2,2.6)':volume=0", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-c:a", "pcm_s16le", "bad.mov")
        run = lambda *args: subprocess.run([sys.executable, "-I", str(SCRIPTS / "checkexport.py"), *args], cwd=work,
                                          capture_output=True, text=True, encoding="utf-8")
        for good in ("clean.mp4", "jump.mp4"):
            r = run(good)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("FAIL", r.stdout)
            self.assertNotIn("WARN", r.stdout)
        bad = run("bad.mov")
        self.assertEqual(bad.returncode, 1)                                       # never delivered
        self.assertIn("black picture from 0:01.60", bad.stdout)                   # 3 black frames from frame 40
        self.assertIn("flash at 0:02.80 (frame 70)", bad.stdout)                  # the stray frame
        self.assertIn("picture 4.00 s but sound 3.50 s", bad.stdout)
        self.assertIn("digital silence from 0:02.0", bad.stdout)
        self.assertIn("colour tags missing", bad.stdout)
        self.assertIn("setparams=color_primaries=bt709", bad.stdout)               # advice that works on every FFmpeg
        self.assertIn("setparams=color_primaries=bt709", (ROOT / "SKILL.md").read_text("utf-8"))  # the export tags it
        self.assertTrue((work / "bad-check.txt").exists())
        sys.path.insert(0, str(SCRIPTS))
        import checkexport
        said = lambda words: {"segments": [{"words": [{"start": i * 0.4, "word": " " + w} for i, w in enumerate(words)]}]}
        lost = checkexport.missing_words(said(["hola", "hoy", "os", "enseño", "algo"]), said(["hola", "os", "enseño", "algo"]))
        self.assertEqual(lost, [(0.4, "hoy")])                                    # a word clipped at a cut

    def test_79_cut_edges_by_their_sound(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed")
        sys.path.insert(0, str(SCRIPTS))
        import cutedges
        rate = cutedges.RATE
        x = np.random.default_rng(1).standard_normal(10 * rate).astype(np.float32) * 0.001     # room noise

        def word(a, b):
            n = int((b - a) * rate)
            x[int(a * rate):int(a * rate) + n] += 0.3 * np.sin(2 * np.pi * 220 * np.arange(n) / rate) * np.hanning(n) ** 0.3
        for a in (0.5, 1.1, 1.7, 3.2, 4.1, 5.0, 6.0):
            word(a, a + 0.3)
        word(3.0, 3.06)                                                           # a fragment of a removed word
        sound = cutedges.Sound(x)

        def plan_of(pieces):
            offsets, total = [], 0
            for a, b in pieces:
                offsets.append(total)
                total += b - a
            return {"fps": "25", "frames": pieces, "offsets": offsets, "total_frames": total}
        # 0-1.24 ends inside the word 1.1-1.4 (mostly outside); 3.00-3.64 opens on the fragment; 4.04-4.60 is clean;
        # 4.84-5.24 starts in silence and ends inside 5.0-5.3, mostly inside; 7.0-7.04 is a sliver
        plan = plan_of([[0, 31], [75, 91], [101, 115], [121, 131], [175, 176]])
        problems = cutedges.check(plan, sound)
        found = {(p["piece"], p["edge"]): p for p in problems}
        self.assertEqual(found[(0, "end")]["kind"], "ends mid-sound")
        self.assertLess(found[(0, "end")]["fix"], 1.1)                            # most of the word is outside: dropped whole
        self.assertEqual(found[(1, "start")]["kind"], "fragment")
        self.assertTrue(3.06 <= found[(1, "start")]["fix"] <= 3.2)                # the start moves into the gap after it
        self.assertNotIn((2, "start"), found)                                     # clean edges are left alone
        self.assertNotIn((2, "end"), found)
        self.assertGreater(found[(3, "end")]["fix"], 5.3)                         # mostly inside: kept whole
        self.assertEqual(found[(4, "both")]["kind"], "sliver")
        fixed = cutedges.apply_fixes(plan, problems)
        self.assertEqual(len(fixed["frames"]), 4)                                 # the sliver is gone
        self.assertEqual(fixed["offsets"][1], fixed["frames"][0][1] - fixed["frames"][0][0])  # offsets recounted
        self.assertEqual(fixed["total_frames"], sum(b - a for a, b in fixed["frames"]))
        self.assertEqual(cutedges.check(fixed, sound), [])                        # nothing left to fix

    def test_80_hook_check(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed")
        sys.path.insert(0, str(SCRIPTS))
        import hookcheck
        rate = 16000
        picture = np.full(96 * 54, 120.0) + np.random.default_rng(0).standard_normal(96 * 54) * 30
        black = np.zeros(96 * 54)
        quiet_then_speech = np.concatenate([np.zeros(int(0.2 * rate)), 0.3 * np.ones(int(0.3 * rate))])
        speech_at_once = 0.3 * np.ones(int(0.5 * rate))
        caps = lambda start, words: [{"start": start, "end": start + 1, "words": words}]
        good_words = [(0.2, 0.5, "Tres"), (0.5, 0.8, "errores"), (0.8, 1.2, "que"), (3.5, 3.8, "luego")]
        fails, warns, opening = hookcheck.check(picture, quiet_then_speech, good_words, caps(0.2, good_words), sfx=[2.0])
        self.assertEqual((fails, warns), ([], []))
        self.assertEqual(opening, "Tres errores que")                              # the first 3 seconds, to judge
        late = [(1.2, 1.5, "Hola")]
        fails, warns, _ = hookcheck.check(picture, np.zeros(rate), late, caps(2.0, late))
        self.assertTrue(any("before the first word" in w for w in warns))           # silence before speaking
        self.assertTrue(any("nothing written on screen" in w for w in warns))       # nothing to read with the sound off
        _, warns, _ = hookcheck.check(picture, np.zeros(rate), late, caps(2.0, late), title_at=0.3)
        self.assertFalse(any("nothing written" in w for w in warns))                # a title counts
        bad = [(0.0, 0.3, "Hola")]
        fails, warns, _ = hookcheck.check(black, speech_at_once, bad, caps(0.0, bad), sfx=[0.1])
        self.assertTrue(any("first frame is black" in f for f in fails))
        self.assertTrue(any("clipped" in f for f in fails))
        self.assertTrue(any("lands on the first word" in w for w in warns))
        mix = self.dir / "sfx-mix.txt"
        mix.write_text("[1:a]adelay=2350|2350,volume=0.4[s0];[2:a]adelay=120|120[s1]", "utf-8")
        self.assertEqual(hookcheck.sfx_times(str(mix)), [0.12, 2.35])

    def test_81_ai_chat_window(self):
        sys.path.insert(0, str(SCRIPTS))
        import chatwindow
        said = "Mirad esto . Le pido a Claude que me resuma este correo . Y me dice lo importante . Así de rápido".split()
        t, words = 10.0, []
        for w in said:
            if w == ".":
                t += 0.6
                continue
            words.append([round(t, 2), round(t + 0.3, 2), w])
            t += 0.32
        captions = [{"start": words[0][0], "end": words[-1][1], "words": words}]
        when = lambda word: next(w[0] for w in words if w[2] == word)
        spec = {"app": "Claude", "start_say": "Le pido a Claude", "end_say": "Así de rápido",
                "messages": [{"role": "user", "text": "Resume este correo en tres puntos", "say": "me resuma"},
                             {"role": "assistant", "text": "Lo importante:\n- Reunión el lunes\n- Falta tu firma", "say": "me dice"},
                             {"role": "user", "text": "Gracias"}]}                       # no phrase: follows the answer
        style = {"theme": "light", "font": "sans-serif", "fontFile": "", "accentColor": "#FF4F8B",
                 "background": "#1B1033", "background2": "#0E2A47"}
        props, start, timeline, problems = chatwindow.build_props(spec, captions, 1920, 1080, 25, style)
        self.assertAlmostEqual(start, when("Le") - chatwindow.LEAD, places=3)
        user, answer, thanks = props["messages"]
        self.assertEqual(user["typeFrom"], round((when("me") - start - chatwindow.LEAD) * 25))   # a beat before it's said
        self.assertAlmostEqual(user["typeTo"] - user["typeFrom"], len(user["text"]) / 22 * 25, delta=1)  # 22 letters a second
        self.assertGreater(user["sent"], user["typeTo"])                                 # sent after the last letter
        self.assertGreaterEqual(answer["from"], user["sent"])                            # never answers before it's asked
        self.assertEqual(answer["answer"] - answer["from"], round(0.8 * 25))             # thinks, then answers
        self.assertGreater(thanks["typeFrom"], answer["answer"])                         # the next prompt follows the answer
        self.assertGreater(props["seconds"], (thanks["sent"] - 0) / 25)                  # long enough to read everything
        self.assertTrue(any("made longer" in p for p in problems))
        clicks = chatwindow.click_times(props)
        first, last = user["typeFrom"] / 25, user["sent"] / 25
        self.assertTrue(first <= clicks[0] and any(abs(c - last) < 0.001 for c in clicks))  # typing, then "enter"
        self.assertTrue(all(not (answer["answer"] / 25 < c < answer["answer"] / 25 + 1) for c in clicks))  # answers are silent
        with self.assertRaises(ValueError):
            chatwindow.build_props(dict(spec, messages=[{"role": "bot", "text": "x"}]), captions, 1920, 1080, 25, style)
        tsx = (SCRIPTS / "remotion" / "ChatWindow.tsx").read_text("utf-8")
        default_props = next(l for l in tsx.splitlines() if "defaultProps=" in l)
        self.assertIn("messages: []", default_props)                                    # no sample chat leaks in
        self.assertIn('warm: {', tsx)                                                   # the Claude-like theme exists
        self.assertIn('"warm"', (SCRIPTS / "chatwindow.py").read_text("utf-8"))           # and can be chosen
        self.assertIn("really answered", (SCRIPTS / "chatwindow.py").read_text("utf-8"))  # the answer is the real one
        for key in list(props) + list(user) + list(answer):
            self.assertRegex(tsx, rf"\b{key}\??:", key)                                # every prop is one it reads
        wav = self.dir / "chat-sfx.wav"
        chatwindow.write_clicks(props, str(wav))
        import wave
        with wave.open(str(wav)) as w:
            self.assertAlmostEqual(w.getnframes() / w.getframerate(), props["seconds"], delta=0.05)

    def test_82_tool_cards(self):
        sys.path.insert(0, str(SCRIPTS))
        import toolcards
        said = ("Hoy uso Claude con Gmail y noción para organizarme . " + "bla " * 20 + ". Claude me ayuda mucho . "
                + "bla " * 50 + ". Y vuelvo a Claude").split()
        t, words = 2.0, []
        for w in said:
            if w == ".":
                t += 0.5
                continue
            words.append([round(t, 2), round(t + 0.25, 2), w])
            t += 0.3
        flat = toolcards.flat_words([{"start": 0, "end": 1, "words": words}])
        tools = [{"name": "Claude", "logo": "logos/claude.png"}, {"name": "Gmail"}, {"name": "Notion", "say": ["noción"]}]
        groups = toolcards.plan_groups(tools, flat)
        self.assertEqual(len(groups), 2)
        first, second = groups
        self.assertEqual([i for _, i in first["cards"]], [0, 1, 2])                # named in a row: one stacked group
        claude = next(w[0] for w in words if w[2] == "Claude")
        self.assertAlmostEqual(first["cards"][0][0], claude - toolcards.LEAD, places=3)  # a beat before the word
        self.assertGreater(second["start"], first["start"] + 20)                  # the repeat 8 s later is skipped
        self.assertEqual([i for _, i in second["cards"]], [0])
        props = toolcards.group_props(first, tools, 1080, 1920, 25, {"accentColor": "#FF4F8B", "font": "x", "fontFile": ""})
        self.assertEqual(props["cards"][0]["logo"], "logos/claude.png")
        self.assertEqual(props["cards"][0]["frame"], 0)
        self.assertGreater(props["cards"][2]["frame"], props["cards"][1]["frame"])   # each on its own word
        # a card due while the group before is still showing waits for it to leave
        crowded = toolcards.plan_groups([{"name": "A"}, {"name": "B"}],
                                        [(1.0, "a"), (3.0, "b")], stack=1.5, hold=2.5)
        self.assertGreaterEqual(crowded[1]["start"], crowded[0]["end"] + toolcards.EXIT)
        tsx = (SCRIPTS / "remotion" / "ToolCard.tsx").read_text("utf-8")
        self.assertIn("cards: []", next(l for l in tsx.splitlines() if "defaultProps=" in l))
        for key in list(props) + list(props["cards"][0]):
            self.assertRegex(tsx, rf"\b{key}\??:", key)
        wav = self.dir / "pops.wav"
        toolcards.write_pops([0.5, 1.0], 2.0, str(wav))
        import wave
        with wave.open(str(wav)) as w:
            self.assertAlmostEqual(w.getnframes() / w.getframerate(), 2.0, delta=0.01)

    def test_83_web_page_numbers_before_after(self):
        sys.path.insert(0, str(SCRIPTS))
        import overlays
        said = ("Mirad esta noticia . Bajamos un poco . Y aquí está el titular . Con IA voy un cuarenta por ciento más "
                "rápido , ahorro tres horas y tengo el doble de ideas . Antes escribía esto y ahora lo pido así . Y fin").split()
        t, words = 1.0, []
        for w in said:
            if w in (".", ","):
                t += 0.5
                continue
            words.append([round(t, 2), round(t + 0.25, 2), w])
            t += 0.3
        caps = [{"start": 0, "end": 1, "words": words}]
        when = lambda word: next(w[0] for w in words if w[2] == word)
        # a web page: a box far down the page scrolls it into view first
        page = {"image": "pages/p.png", "imageWidth": 1440, "imageHeight": 2600, "url": "x.example",
                "start_say": "Mirad", "scroll": [{"to": 0.1, "say": "Bajamos"}],
                "highlight": [{"box": [50, 1490, 1340, 75], "say": "el titular"}]}
        timer = overlays.Timer(page, caps)
        body, last, timeline = overlays.browser_props(page, timer, 25, public=str(self.dir), width=1920, height=1080)
        box = body["boxes"][0]
        self.assertEqual(box["frame"], round((when("el") - timer.start - overlays.LEAD) * 25))
        stop = next(s for s in body["scroll"] if s["frame"] == box["frame"])     # the page scrolls to the box
        win_w, view_h = overlays.browser_view(1920, 1080)
        scale = win_w / 1440
        seen = stop["to"] * (2600 * scale - view_h)
        self.assertTrue(seen <= 1490 * scale and (1490 + 75) * scale <= seen + view_h)  # the box is in view
        plain = dict(page, highlight=[{"box": [50, 100, 600, 60], "say": "el titular"}], scroll=[])
        body2, _, _ = overlays.browser_props(plain, overlays.Timer(plain, caps), 25, public=str(self.dir))
        self.assertEqual(len(body2["scroll"]), 1)                                  # already in view: no extra scroll
        tsx = (SCRIPTS / "remotion" / "BrowserPage.tsx").read_text("utf-8")
        self.assertIn("p.width * 0.8", tsx)                                       # the window sizes overlays.py assumes
        self.assertIn("p.height * 0.84", tsx)
        self.assertIn("s * 1.4", tsx)
        # numbers: each tile on its own phrase, Spanish formatting, 2 to 4 tiles
        stats = {"start_say": "Con IA", "tiles": [{"value": 40, "suffix": " %", "label": "más rápido", "say": "un cuarenta"},
                                                  {"value": 1250.5, "decimals": 1, "label": "palabras", "say": "tres horas"}]}
        st_timer = overlays.Timer(stats, caps)
        body, _, timeline = overlays.stats_props(stats, st_timer, 25)
        self.assertLess(body["tiles"][0]["frame"], body["tiles"][1]["frame"])
        self.assertEqual(overlays.number_text(1250.5, 1), "1.250,5")
        self.assertEqual(overlays.number_text(40, 0, "", " %"), "40 %")
        with self.assertRaises(ValueError):
            overlays.stats_props(dict(stats, tiles=stats["tiles"][:1]), overlays.Timer(stats, caps), 25)
        # before and after: the sweep on its phrase
        ba = {"start_say": "Antes escribía", "reveal_say": "ahora lo pido", "before": {"label": "Antes", "text": "Escribe un post"},
              "after": {"label": "Después", "text": "Escribe un post de 150 palabras"}}
        ba_timer = overlays.Timer(ba, caps)
        body, _, _ = overlays.beforeafter_props(ba, ba_timer, 25)
        self.assertEqual(body["reveal"], round((when("ahora") - ba_timer.start - overlays.LEAD) * 25))
        with self.assertRaises(ValueError):
            overlays.beforeafter_props(dict(ba, after={}), overlays.Timer(ba, caps), 25)
        for name, props in (("StatTiles", ("tiles", "value", "decimals", "prefix", "suffix", "label", "frame")),
                            ("BeforeAfter", ("before", "after", "reveal", "revealFrames", "label", "text", "image")),
                            ("BrowserPage", ("image", "url", "pageWidth", "pageHeight", "scroll", "boxes", "to"))):
            tsx = (SCRIPTS / "remotion" / f"{name}.tsx").read_text("utf-8")
            for key in props:
                self.assertRegex(tsx, rf"\b{key}\??:", f"{name}: {key}")
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            Image = None
        if Image is not None:                                                     # a rough box is fitted to what's inside
            shot = self.dir / "shot.png"
            im = Image.new("RGB", (1440, 600), "white")
            ImageDraw.Draw(im).rectangle([61, 196, 909, 233], fill="black")       # a heading's ink
            im.save(shot)
            self.assertEqual(overlays.fit_box(str(shot), [50, 190, 1340, 75]), [61, 196, 849, 38])
            self.assertIsNone(overlays.fit_box(str(shot), [1000, 400, 300, 100]))  # nothing inside: left as given
        tsx = (SCRIPTS / "remotion" / "BrowserPage.tsx").read_text("utf-8")
        self.assertIn("4000px rgba", tsx)                                          # the rest of the page dims
        png = self.dir / "tiny.png"
        png.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d49484452") + (1440).to_bytes(4, "big") + (2600).to_bytes(4, "big"))
        self.assertEqual(overlays.png_size(str(png)), (1440, 2600))              # a screenshot's size from its header

    def test_84_reusable_word_fixes(self):
        sys.path.insert(0, str(SCRIPTS))
        import wordfixes
        saved = self.dir / "personal-fixes.json"
        self.assertEqual(wordfixes.read(str(saved)), {})                                  # no list yet: nothing
        self.assertIsNone(wordfixes.add("cupillon", "goupillon", str(saved)))
        self.assertIsNone(wordfixes.add("sefora", "Sephora", str(saved)))
        self.assertEqual(wordfixes.add("Cupillon", "Goupillon", str(saved)), "goupillon")  # replaced, case ignored
        self.assertEqual(sorted(wordfixes.read(str(saved)).values()), ["Goupillon", "Sephora"])
        for bad in (("", "x"), ("x", ""), ("Hola", "hola")):                             # nothing to fix: refused
            with self.assertRaises(ValueError):
                wordfixes.add(*bad, path=str(saved))
        self.assertEqual(saved.read_text("utf-8").count("cupillon") + saved.read_text("utf-8").count("Cupillon"), 1)
        # the video's own pair wins over the saved one
        merged = wordfixes.load({"sefora": "SEPHORA"}, str(saved))
        self.assertEqual(merged["sefora"], "SEPHORA")
        self.assertIn("cupillon", [k.lower() for k in merged])
        # a vocabulary for Whisper: the right spellings once each, capped; Parakeet gets none
        words = {"a": "Sephora", "b": "sephora", "c": "Glow Serum|", "d": "goupillon"}
        self.assertEqual(wordfixes.vocabulary(words), "Sephora, Glow Serum, goupillon")
        self.assertEqual(len(wordfixes.vocabulary({str(i): f"w{i}" for i in range(100)}, limit=40).split(", ")), 40)
        self.assertEqual(wordfixes.hint_for("whisper", None, words), "Sephora, Glow Serum, goupillon")
        self.assertEqual(wordfixes.hint_for("whisper", "mi prompt", words), "mi prompt")   # an explicit prompt wins
        self.assertIsNone(wordfixes.hint_for("parakeet", None, words))
        self.assertIsNone(wordfixes.hint_for("whisper", None, {}))
        self.assertTrue(wordfixes.remove("CUPILLON", str(saved)))
        self.assertFalse(wordfixes.remove("cupillon", str(saved)))
        # captions: the saved list is applied to a video with no --fix, and can be left out
        (self.dir / "tr2.json").write_text(json.dumps({"segments": [{"words": [
            {"word": " Mi", "start": 0.0, "end": 0.2}, {"word": " cupillon", "start": 0.2, "end": 0.7},
            {"word": " de", "start": 0.7, "end": 0.8}, {"word": " Sefora.", "start": 0.8, "end": 1.4}]}]}), "utf-8")
        wordfixes.add("cupillon", "goupillon", str(saved))
        wordfixes.add("sefora", "Sephora", str(saved))
        common = ["captions.py", "tr2.json", "--font", "DejaVu Sans", "--width", "540", "--height", "960", "--size", "40",
                  "--margin-v", "260", "--on-cut", "--length", "2", "--personal-fixes", str(saved), "--out", "p.ass"]
        out = script(*common, cwd=self.dir)
        caps = json.loads((self.dir / "p.json").read_text("utf-8"))
        self.assertEqual(" ".join(c["text"] for c in caps), "Mi goupillon de Sephora.")
        self.assertIn("saved word fixes", out)
        self.assertAlmostEqual(caps[0]["words"][1][0], 0.2, places=2)                       # the word keeps its time
        script(*common, "--no-personal-fixes", cwd=self.dir)
        caps = json.loads((self.dir / "p.json").read_text("utf-8"))
        self.assertEqual(" ".join(c["text"] for c in caps), "Mi cupillon de Sefora.")       # switched off
        (self.dir / "own.json").write_text(json.dumps({"sefora": "SEPHORA"}), "utf-8")
        script(*common, "--fix", "own.json", cwd=self.dir)
        caps = json.loads((self.dir / "p.json").read_text("utf-8"))
        self.assertEqual(" ".join(c["text"] for c in caps), "Mi goupillon de SEPHORA.")      # the video's own wins
        cli = lambda *a: subprocess.run([sys.executable, "-I", str(SCRIPTS / "wordfixes.py"), *a], cwd=self.dir,
                                       capture_output=True, text=True, encoding="utf-8")
        self.assertIn('"cupillon" -> "goupillon"', cli("list", "--file", str(saved)).stdout)
        self.assertNotEqual(cli("add", "solo", "--file", str(saved)).returncode, 0)          # two words needed
        for name in ("SKILL.md",):
            self.assertIn("wordfixes.py", (ROOT / name).read_text("utf-8"))                  # the instructions mention it

    def test_85_freckles_calmed_not_removed(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV or numpy not installed")
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import settings
        import spots
        h, w = 700, 900
        luma = np.full((h, w), 190, np.float32) + np.random.default_rng(0).normal(0, 1.5, (h, w)).astype(np.float32)
        brow = np.zeros((h, w), np.uint8)
        cv2.ellipse(brow, (450, 200), (150, 22), 0, 0, 360, 255, -1)         # the brow's outline
        cv2.ellipse(luma, (450, 200), (150, 12), 0, 0, 360, 80, -1)          # its dark hairs
        for x in (330, 400, 470, 540):
            cv2.line(luma, (x, 170), (x + 12, 182), 100, 2)                  # single hairs poking out above it
        for x, y in ((340, 290), (420, 305), (500, 285), (445, 235), (200, 450)):
            cv2.circle(luma, (x, y), 5, 140, -1)                             # freckles; (445, 235) is just under the brow
        cv2.circle(luma, (700, 400), 8, 70, -1)                              # a mole: bigger and much darker
        luma[300:340, 580:700] = 90                                          # an eye
        near = lambda m, x, y: float(m[y - 2:y + 3, x - 2:x + 3].max())
        keep = spots.brow_hair_keep(luma, brow, 14, 700)
        self.assertGreater(near(keep, 450, 200), 0.9)                         # the brow's hairs stay sharp
        self.assertGreater(near(keep, 336, 176), 0.9)                         # and so do the strays above it
        self.assertLess(near(keep, 445, 235), 0.1)                            # a freckle under it is skin, not a hair
        old = cv2.GaussianBlur(luma, (0, 0), 10) - luma > 14                  # the old rule took it for one
        zone = cv2.dilate(brow, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))) > 0
        old_keep = cv2.dilate(((old & zone).astype(np.uint8)) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        self.assertGreater(near(old_keep, 445, 235), 0)
        skin = np.ones((h, w), np.float32)
        exclude = np.zeros((h, w), bool)
        exclude[300:340, 580:700] = True
        exclude |= (cv2.dilate(brow, np.ones((25, 25), np.uint8)) > 0) | (keep > 0.2)
        mask = spots.spot_mask(luma, skin, exclude, 700)
        for x, y in ((340, 290), (420, 305), (500, 285), (445, 235), (200, 450)):
            self.assertGreater(near(mask, x, y), 0.9, (x, y))                  # every freckle is in the spot mask
        for x, y, what in ((700, 400, "mole"), (450, 200, "brow"), (640, 320, "eye"), (100, 600, "skin")):
            self.assertLess(near(mask, x, y), 0.05, what)                      # the mole, brow, eye and plain skin are not
        far = spots.spot_mask(luma, skin, exclude, 120)                        # a small, distant face: a 10 px dot isn't a freckle
        self.assertLess(near(far, 340, 290), 0.1)
        self.assertEqual(spots.spot_mask(np.full((h, w), 190, np.float32), skin, exclude, 700).max(), 0)  # nothing to find
        # the settings
        self.assertEqual((settings.DEFAULTS["spot_calm"], settings.DEFAULTS["spot_contrast"]), (0, 14))
        here = os.getcwd()
        try:
            os.chdir(self.dir)
            Path("retouch.json").write_text(json.dumps({"spot_calm": 1.4}), "utf-8")
            with self.assertRaises(SystemExit):
                settings.load()
            Path("retouch.json").write_text(json.dumps({"spot_calm": 0}), "utf-8")
            self.assertEqual(settings.load()["spot_calm"], 0)
            Path("retouch.json").unlink()
        finally:
            os.chdir(here)
        # the filter calms a freckle by about half, and leaves a mole alone (the mask says where)
        work = self.dir / "freckles"
        work.mkdir()
        frame = np.full((960, 540, 3), (150, 170, 215), np.uint8)
        for x, y in ((150, 300), (260, 420)):
            cv2.circle(frame, (x, y), 6, (95, 120, 170), -1)
        cv2.circle(frame, (300, 700), 9, (50, 70, 110), -1)
        ycc = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        full = spots.spot_mask(ycc[..., 0].astype(np.float32), np.ones((960, 540), np.float32), np.zeros((960, 540), bool), 700)

        def gray_video(name, plane):
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "540x960", "-r", "25",
                                  "-i", "-", "-c:v", "ffv1", name], cwd=work, stdin=subprocess.PIPE)
            for _ in range(3):
                p.stdin.write(plane.tobytes())
            p.stdin.close()
            p.wait()
        gray_video("skin.mkv", np.full((960, 540), 200, np.uint8))
        gray_video("teeth.mkv", np.zeros((960, 540), np.uint8))
        gray_video("strong.mkv", np.zeros((960, 540), np.uint8))
        gray_video("spots.mkv", (full * 0.55 * 255).astype(np.uint8))
        raw = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "540x960", "-r", "25",
                                "-i", "-", "-c:v", "libx264", "-crf", "0", "-pix_fmt", "yuv444p", "clean.mp4"],
                               cwd=work, stdin=subprocess.PIPE)
        for _ in range(3):
            raw.stdin.write(frame.tobytes())
        raw.stdin.close()
        raw.wait()
        run(["ffmpeg", "-v", "error", "-y", "-i", "clean.mp4", "-i", "skin.mkv", "-i", "teeth.mkv", "-i", "strong.mkv",
             "-i", "spots.mkv", filter_flag(), SCRIPTS / "retouch" / "retouch.txt", "-map", "[v]", "-frames:v", "1",
             "-pix_fmt", "yuv444p", "-c:v", "libx264", "-crf", "0", "out.mp4"], cwd=work)

        def contrast(path, x, y):
            data = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-vf", "format=gray", "-f",
                                   "rawvideo", "-"], cwd=work, capture_output=True).stdout
            a = np.frombuffer(data, np.uint8).reshape(960, 540).astype(float)
            return a[100:140, 100:140].mean() - a[y, x]
        before, after = contrast("clean.mp4", 150, 300), contrast("out.mp4", 150, 300)
        self.assertTrue(0.3 * before < after < 0.7 * before, (before, after))      # about half the contrast, not gone
        self.assertGreater(contrast("out.mp4", 300, 700), 0.9 * contrast("clean.mp4", 300, 700))  # the mole is untouched
        text = (SCRIPTS / "retouch" / "retouch-blur.txt").read_text("utf-8")
        self.assertIn("[4:v]format=gray[pm]", text)                               # spots are input 4 ...
        self.assertIn("[5:v]format=gray[bm]", text)                               # ... and the background mask moves to 5

    def test_38_the_skill_loads_when_asked_to_update_it(self):
        head = (ROOT / "SKILL.md").read_text("utf-8").split("---")[1]
        description = head.split("description:", 1)[1].lower()
        for phrase in ("update", "actualiza", "version"):
            self.assertIn(phrase, description)

    def test_39_reports_remove_personal_details_and_build_links(self):
        sys.path.insert(0, str(SCRIPTS))
        import report
        home, user = "C:\\Users\\maria", "maria"
        details = "Saw: the skin is not soft at 3:32.\nFile: C:\\Users\\maria\\video-work\\clip\\skin.mkv\nAsked by Maria."
        title, body, links = report.build("bug", "Skin not softened", details,
                                          {"github_repo": "owner/repo", "email": ""}, home=home, user=user)
        self.assertNotIn("maria", body.lower())
        self.assertIn("~\\video-work", body)
        self.assertIn("Skill version", body)
        self.assertTrue(title.startswith("[Bug] "))
        self.assertIn("https://github.com/owner/repo/issues/new?template=bug.md", links["github"])
        self.assertNotIn("email", links)                        # no address set: no email link
        _, _, with_email = report.build("idea", "Music", "a long idea " * 1000, {"github_repo": "owner/repo", "email": "a@b.c"},
                                        home=home, user=user)
        self.assertTrue(with_email["email"].startswith("mailto:a@b.c?subject="))
        self.assertIn("template=improvement.md", with_email["github"])
        self.assertLess(len(with_email["github"]), 30000)       # very long reports are cut in the link

    def test_36_update_refuses_to_touch_a_repository(self):
        home = self.dir / "upd4"
        clone = home / "clone"
        shutil.copytree(ROOT, clone / "video-editor", ignore=shutil.ignore_patterns("__pycache__"))
        (clone / ".git").mkdir()
        (clone / "video-editor" / "VERSION").write_text("1.0.0\n", "utf-8")
        result = self._update(clone / "video-editor", home, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("git pull", result.stdout + result.stderr)
        self.assertEqual((clone / "video-editor" / "VERSION").read_text("utf-8").strip(), "1.0.0")
        self.assertFalse((home / "backups").exists())

    def test_40_broll_finds_the_product_and_the_moment(self):
        folder = self.dir / "broll" / "kit"
        (folder / "Haus Labs").mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image
            have_pillow = True
            Image.new("RGB", (400, 600), (230, 200, 180)).save(folder / "Glow-Serum_front.jpg")
            Image.new("RGB", (500, 500), (200, 160, 140)).save(folder / "Haus Labs" / "corrector-líquido.png")
            Image.new("RGB", (300, 300), (90, 90, 90)).save(folder / "IMG_2041.jpg")
        except ImportError:
            have_pillow = False
            for name in ("Glow-Serum_front.jpg", "Haus Labs/corrector-líquido.png", "IMG_2041.jpg"):
                (folder / name).write_bytes(b"not decoded without Pillow")
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=360x640:r=30:d=2", "-c:v", "libx264",
             "-preset", "ultrafast", str(folder / "labial rojo swatch.mp4")])
        work = self.dir / "broll"
        out = script("broll.py", "index", "kit", cwd=work)
        index = json.loads((work / "broll-index.json").read_text("utf-8"))
        kinds = {e["file"]: e["kind"] for e in index["files"]}
        self.assertEqual(kinds["labial rojo swatch.mp4"], "clip")
        self.assertEqual(len(kinds), 4)
        self.assertIn("haus", next(e["words"] for e in index["files"] if e["file"].startswith("Haus Labs")))
        self.assertEqual(next(e["words"] for e in index["files"] if e["file"] == "IMG_2041.jpg"), [])  # camera name
        self.assertAlmostEqual(next(e["seconds"] for e in index["files"] if e["kind"] == "clip"), 2.0, delta=0.1)
        self.assertIn("camera names", out)
        if have_pillow:
            self.assertTrue((work / "broll-sheet.png").exists())
        captions = [
            {"start": 0.5, "end": 2.0, "text": "", "words": [[0.5, 0.8, "me"], [0.8, 1.2, "encanta"], [1.2, 1.5, "el"],
                                                            [1.5, 1.8, "Glow"], [1.8, 2.0, "Sérum."]]},
            {"start": 3.0, "end": 4.5, "text": "", "words": [[3.0, 3.2, "y"], [3.4, 3.9, "labiales"], [3.9, 4.3, "rojos,"]]},
            {"start": 5.0, "end": 6.0, "text": "", "words": [[5.2, 5.7, "corrector"], [5.7, 5.8, "de"], [5.8, 6.0, "Haus"]]},
            {"start": 7.0, "end": 8.0, "text": "", "words": [[7.0, 7.4, "otra"], [7.4, 7.6, "vez"], [7.6, 7.9, "glow"],
                                                            [7.9, 8.0, "serum"]]}]
        (work / "captions.json").write_text(json.dumps(captions), "utf-8")
        script("broll.py", "match", "--product", "Glow Serum", "--product", "labial rojo", "--product", "Haus Labs corrector",
               "--product", "Vitamin C", cwd=work)
        found = {m["product"]: m for m in json.loads((work / "broll-matches.json").read_text("utf-8"))}
        self.assertEqual(found["Glow Serum"]["first_mention"], 1.5)               # accents ignored
        self.assertEqual(found["Glow Serum"]["mentions"], [1.5, 7.6])             # every time it's said
        self.assertEqual(found["Glow Serum"]["candidates"][0]["file"], "Glow-Serum_front.jpg")
        self.assertEqual(found["labial rojo"]["first_mention"], 3.4)              # plurals count
        self.assertEqual(found["labial rojo"]["candidates"][0]["kind"], "clip")
        self.assertEqual(found["Haus Labs corrector"]["mention_match"], "partial")  # said in another order
        self.assertEqual(found["Haus Labs corrector"]["candidates"][0]["file"], "Haus Labs/corrector-líquido.png")
        self.assertIsNone(found["Vitamin C"]["first_mention"])
        self.assertEqual(found["Vitamin C"]["candidates"], [])                    # no look-alike suggested

    def test_41_pop_in_goes_beside_the_temple_and_never_over_the_hand(self):
        sys.path.insert(0, str(SCRIPTS))
        import popplace
        W, H = 1080, 1920
        face = {"left": 300, "right": 900, "top": 500, "temple_y": 700}   # more room on the left (300) than right (180)

        def box(props, aspect=1.2, label=0):
            x = props["margin"] if props["side"] == "left" else W - props["margin"] - props["size"]
            return (x, props["top"], x + props["size"], props["top"] + props["size"] * aspect + label)

        props, notes = popplace.place(face, [], W, H, 1.2)
        self.assertEqual(props["side"], "left")
        b = box(props)
        self.assertLessEqual(b[2], face["left"])                          # beside the face, not on it
        self.assertAlmostEqual((b[1] + b[3]) / 2, face["temple_y"], delta=2)  # centred at the temples
        # a hand holding a product up on the left, at temple height: lifted above it, or moved, never over it
        hand = popplace.hand_zone([(80, 1100), (260, 1100), (80, 1300), (260, 1300)], W, H)
        props, notes = popplace.place(face, [hand], W, H, 1.2)
        self.assertIsNotNone(props)
        self.assertFalse(popplace.overlaps(box(props), hand))
        self.assertTrue(notes)                                            # it says what it did
        # hands on both sides, all the way up: no room, so it says to skip
        walls = [(0, 0, 300, H), (900, 0, W, H)]
        props, notes = popplace.place(face, walls, W, H, 1.2)
        self.assertIsNone(props)
        self.assertIn("skip", notes[-1])
        # the name under the picture is dropped when only the picture fits
        tight = [(0, 420, 300, H)]                                        # room for a small picture, not for its name
        props, notes = popplace.place(face, tight, W, H, 1.2, label=True)
        self.assertIsNotNone(props)
        self.assertIsNone(props.get("name", "kept"))
        self.assertFalse(popplace.overlaps(box(props), tight[0]))

    def test_42_white_balance_is_measured_and_corrected(self):
        self._numpy()
        scene = ("color=0x8a8a8a:s=640x360:d=2,drawbox=x=40:y=40:w=200:h=120:color=0xe8e8e8:t=fill,"
                 "drawbox=x=400:y=200:w=180:h=120:color=0xc06040:t=fill")
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", scene, "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p",
             "wb-neutral.mp4"], cwd=self.dir)
        run(["ffmpeg", "-v", "error", "-y", "-i", "wb-neutral.mp4", "-vf", "colorchannelmixer=rr=0.95:gg=1.0:bb=1.07",
             "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", "wb-blue.mp4"], cwd=self.dir)
        last = lambda out: json.loads(out.strip().splitlines()[-1])
        neutral = last(script("balance.py", "wb-neutral.mp4", cwd=self.dir))
        self.assertIsNone(neutral["filter"])
        blue = last(script("balance.py", "wb-blue.mp4", "--check", "wb.png", cwd=self.dir))
        self.assertIn("cool (blue)", blue["cast"])
        self.assertGreater(blue["size_percent"], 4)
        self.assertTrue((self.dir / "wb.png").exists())
        run(["ffmpeg", "-v", "error", "-y", "-i", "wb-blue.mp4", "-vf", blue["filter"], "-c:v", "libx264", "-crf", "12",
             "-pix_fmt", "yuv420p", "wb-fixed.mp4"], cwd=self.dir)
        fixed = last(script("balance.py", "wb-fixed.mp4", cwd=self.dir))
        self.assertLess(fixed["size_percent"], 1.0)                       # the filter brings it back to neutral
        half = last(script("balance.py", "wb-blue.mp4", "--strength", "0.5", cwd=self.dir))
        gains = lambda f: [float(v) for v in re.findall(r"=([\d.]+)", f)]
        for g_half, g_full in zip(gains(half["filter"]), gains(blue["filter"])):
            self.assertAlmostEqual(g_half - 1, (g_full - 1) / 2, delta=0.0002)  # half the change, on every channel
        self.assertEqual(half["half"], half["filter"])
        region = last(script("balance.py", "wb-blue.mp4", "--region", "0.07,0.12,0.30,0.30", cwd=self.dir))  # the white box
        self.assertIn("cool (blue)", region["cast"])

    def test_43_edit_report_in_numbers(self):
        folder = self.dir / "report-edit"
        folder.mkdir(exist_ok=True)
        shutil.copy(self.dir / "src.mp4", folder / "src.mp4")
        shutil.copy(self.dir / "tr.json", folder / "tr.json")
        (folder / "cuts.json").write_text(json.dumps({"remove": [[0.3, 1.9, "first take of the intro"], [4.5, 4.6, "um"]]}), "utf-8")
        script("cutplan.py", "build", "src.mp4", "tr.json", "--cuts", "cuts.json", cwd=folder)
        script("cutplan.py", "filter", cwd=folder)
        run(["ffmpeg", "-v", "error", "-y", "-i", "src.mp4", filter_flag(), "cut-filter.txt", "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "final.mp4"], cwd=folder)
        out = script("editreport.py", "src.mp4", "final.mp4", cwd=folder)
        self.assertRegex(out, r"Length: 12\.0 s -> \d+\.\d s")
        self.assertIn("1 retakes, 1 fillers", out)
        self.assertIn("Pieces kept:", out)
        self.assertRegex(out, r"Loudness: -?\d+\.\d LUFS")
        self.assertIn("540x960", out)
        self.assertTrue((folder / "final-report.txt").exists())
        again = script("editreport.py", "src.mp4", "final.mp4", cwd=folder)  # never overwrites a report
        self.assertIn("final-report-v2.txt", again)

    # ---- the plugin ------------------------------------------------------------------------------

    def test_44_plugin_manifests_match_the_version(self):
        market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text("utf-8"))
        entry = next(p for p in market["plugins"] if p["name"] == "video-editor")
        plugin_root = (REPO / entry["source"]).resolve()
        manifest = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text("utf-8"))
        self.assertEqual(manifest["name"], "video-editor")
        self.assertEqual(plugin_root / "skills" / "video-editor", ROOT)
        self.assertTrue((ROOT / "SKILL.md").exists())
        version = (ROOT / "VERSION").read_text("utf-8").strip()
        self.assertEqual(manifest["version"], version)                                 # the plugin system sees updates
        self.assertEqual((REPO / "video-editor" / "VERSION").read_text("utf-8").strip(), version)  # old installs too

    def test_45_updater_leaves_a_plugin_install_alone(self):
        home = self.dir / "upd-plugin"
        skill = home / ".claude" / "plugins" / "cache" / "malenaaza" / "video-editor" / "2.2.0" / "skills" / "video-editor"
        shutil.copytree(ROOT, skill, ignore=shutil.ignore_patterns("__pycache__"))
        (skill / "VERSION").write_text("1.0.0\n", "utf-8")
        result = self._update(skill, home)
        self.assertIn("plugin", result.stdout)
        self.assertEqual((skill / "VERSION").read_text("utf-8").strip(), "1.0.0")     # nothing replaced
        self.assertFalse((home / "backups").exists())
        check = self._update(skill, home, "--check").stdout
        self.assertIn("/plugin", check)
        self.assertNotIn("--remove-old-copy", check)                                   # no move offered to a plugin

    def test_46_old_copy_is_offered_the_move_and_removed_safely(self):
        home, skill = self._installed_copy("upd-move", version="1.0.0")
        self.assertIn("claude plugin install video-editor@malenaaza", self._update(skill, home, "--check").stdout)
        (skill / "my-setup.md").write_text("# settings\n", "utf-8")
        out = script("update_skill.py", "--remove-old-copy", "--old-copy", skill, "--backup-dir", home / "backups",
                     "--settings-dir", home / "settings", cwd=self.dir)
        self.assertIn("Removed the old copy", out)
        self.assertFalse(skill.exists())
        backup = next((home / "backups").iterdir())
        self.assertEqual((backup / "VERSION").read_text("utf-8").strip(), "1.0.0")        # nothing lost
        self.assertEqual((home / "settings" / "my-setup.md").read_text("utf-8"), "# settings\n")
        clone = self.dir / "upd-move-clone"
        shutil.copytree(ROOT, clone / "video-editor", ignore=shutil.ignore_patterns("__pycache__"))
        (clone / ".git").mkdir()
        refused = subprocess.run([sys.executable, "-I", str(SCRIPTS / "update_skill.py"), "--remove-old-copy", "--old-copy",
                                  str(clone / "video-editor"), "--backup-dir", str(home / "b2")], capture_output=True, text=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertTrue((clone / "video-editor" / "SKILL.md").exists())                 # a developer's clone is never removed

    def test_47_typewriter_clicks_follow_the_letters(self):
        out = script("sfx/typing.py", "--line", "Mi rutina de", "--line", "5 minutos", "--lps", "16", "--start", "0.13",
                     "--out", "typing.wav", cwd=self.dir)
        self.assertIn("9 clicks", out)                     # every other letter, never a space: 17 letters -> 9 clicks
        self.assertIn("typing ends at 1.44 s", out)        # 0.13 + 21 characters / 16
        import wave
        w = wave.open(str(self.dir / "typing.wav"))
        self.assertAlmostEqual(w.getnframes() / w.getframerate(), 1.44 + 0.3, delta=0.01)
        title = (SCRIPTS / "remotion" / "TitleCard.tsx").read_text("utf-8")
        default_props = next(l for l in title.splitlines() if "defaultProps=" in l)
        self.assertNotIn("highlight", default_props)       # a sample highlight would leak into real titles
        self.assertIn('"typewriter"', title)

    def test_48_word_highlight_props_match_the_captions(self):
        words = [("Mi", .2, .35), ("rutina", .35, .75), ("de", .75, .85), ("5", .85, 1.05), ("minutos.", 1.05, 1.5),
                 ("para", 1.65, 1.85), ("una", 1.85, 2.0), ("piel", 2.0, 2.3), ("luminosa", 2.3, 2.9)]
        (self.dir / "wv.json").write_text(json.dumps({"segments": [{"words": [
            {"word": " " + w, "start": s, "end": e} for w, s, e in words]}]}), "utf-8")
        script("captions.py", "wv.json", "--on-cut", "--length", "3", "--font", "DejaVu Sans", "--upper",
               "--no-punctuation", "--two-lines", "12", "--out", "wc.ass", "--remotion-props", "wc-props.json",
               "--accent-color", "#123456", "--fps", "25", "--margin-v", "300", cwd=self.dir)
        caps = json.loads((self.dir / "wc.json").read_text("utf-8"))
        props = json.loads((self.dir / "wc-props.json").read_text("utf-8"))
        self.assertEqual(props["length"], 3)
        self.assertEqual((props["accentColor"], props["fps"], props["bottom"]), ("#123456", 25, 300))
        self.assertEqual(len(props["captions"]), len(caps))
        for c, p in zip(caps, props["captions"]):
            self.assertEqual((c["start"], c["end"]), (p["start"], p["end"]))
            self.assertEqual([w[:2] for w in c["words"]], [w[:2] for w in p["words"]])
            self.assertEqual(" ".join(w[2] for w in p["words"]), c["text"])   # shown as the captions show it
            if len(c["text"]) > 12:                                           # long captions keep their two lines
                self.assertGreater(p["breakAfter"], 0)
        self.assertIn("MINUTOS", [w[2] for p in props["captions"] for w in p["words"]])  # full stop dropped
        tsx = (SCRIPTS / "remotion" / "WordCaptions.tsx").read_text("utf-8")
        default_props = next(l for l in tsx.splitlines() if "defaultProps=" in l)
        self.assertIn("captions: []", default_props)        # sample captions would leak into real videos

    def test_49_a_part_in_black_and_white(self):
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=160x120:r=25:d=4", "-pix_fmt", "yuv420p",
             "colour.mp4"], cwd=self.dir)
        out = script("mono.py", "--part", "1", "2.5", "--fade", "0.3", "--length", "4", cwd=self.dir)
        self.assertIn("from 1.00 to 2.50 s", out)
        chain = (self.dir / "mono.txt").read_text("utf-8").strip()
        stats = run(["ffmpeg", "-v", "error", "-i", "colour.mp4", "-vf",
                     chain + ",signalstats,metadata=print:key=lavfi.signalstats.SATAVG:file=-", "-f", "null", "-"],
                    cwd=self.dir)
        sat = [float(l.split("=")[1]) for l in stats.splitlines() if "SATAVG" in l]
        self.assertEqual(len(sat), 100)
        at = lambda t: sat[round(t * 25)]
        self.assertGreater(min(at(0.2), at(0.9), at(2.6), at(3.6)), 20)      # colour before and after
        self.assertLess(at(1.75), 1)                                          # grey in the middle
        self.assertTrue(1 < at(1.12) < at(0.9))                               # fading, not switched
        # a phrase from the captions, joined parts, and a part past the end
        (self.dir / "captions.json").write_text(json.dumps([
            {"start": 0.0, "end": 1.2, "words": [[0.1, 0.5, "Antes"], [0.5, 1.0, "tenía"]]},
            {"start": 1.2, "end": 3.0, "words": [[1.3, 1.8, "y"], [1.8, 2.6, "ahora"]]}]), "utf-8")
        out = script("mono.py", "--say", "antes", "--until", "Y AHORA", cwd=self.dir)
        self.assertIn("from 0.10 to 2.60 s", out)
        out = script("mono.py", "--part", "1", "2", "--part", "1.5", "3", "--fade", "0", cwd=self.dir)
        self.assertIn("from 1.00 to 3.00 s", out)
        self.assertIn("gte(t,1.000)*lt(t,3.000)", (self.dir / "mono.txt").read_text("utf-8"))  # --fade 0: a hard switch
        bad = subprocess.run([sys.executable, "-I", str(SCRIPTS / "mono.py"), "--part", "3", "5", "--length", "4"],
                             cwd=self.dir, capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("past the end", bad.stderr)

    def test_50_push_in_is_smooth_and_keeps_the_head(self):
        sys.path.insert(0, str(SCRIPTS))
        import pushin
        W, H = 320, 240
        # geometry: room above the head, a close-up, and no room at all
        face = {"centre_x": 160, "centre_y": 120, "head_top": 40, "forehead": 70, "chin": 190, "mouth": 170}
        z, x0, y0, notes = pushin.aim(dict(face, head_top=100), W, H, 1.2)
        self.assertEqual(z, 1.2)
        self.assertGreaterEqual((100 - y0) * z, pushin.HEAD_ROOM - 0.01)
        z, x0, y0, notes = pushin.aim(face, W, H, 1.2)                         # head cut already: keep the forehead
        self.assertTrue(any("close-up" in n for n in notes))
        self.assertGreaterEqual((70 - y0) * z, pushin.HEAD_ROOM - 0.01)
        z, x0, y0, notes = pushin.aim(dict(face, head_top=70, forehead=70), W, H, 1.3, caption_top=200)
        self.assertLess(z, 1.3)                                                # zoom lowered to fit
        self.assertTrue(any("lowered" in n for n in notes))
        self.assertLessEqual((190 - y0) * z, 200.01)
        self.assertGreaterEqual((70 - y0) * z, pushin.HEAD_ROOM - 0.01)
        z, _, _, notes = pushin.aim(dict(face, forehead=30, head_top=30), W, H, 1.2)
        self.assertIsNone(z)                                                   # no room even for 1.04
        # the filter: untouched before, smooth growth, full zoom held, back to the full frame
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
             "color=gray:s=320x240:r=25:d=4,drawbox=x=150:y=110:w=20:h=20:color=white:t=fill", "-pix_fmt", "yuv420p",
             "-c:v", "libx264", "-crf", "1", "sq.mp4"], cwd=self.dir)
        line = pushin.filter_line(W, H, 25, 1.0, 3.6, 1.5, 160 / 3, 40, 1.0, 0.4)  # x0, y0 = centre * (1 - 1/1.5)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "sq.mp4", "-vf", line, "-f", "rawvideo", "-pix_fmt",
                              "gray", "-"], cwd=self.dir, capture_output=True).stdout
        import numpy as np
        frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(float)
        size = np.array([((f - 128).clip(0).sum()) ** 0.5 for f in frames])  # grows with the zoom
        self.assertEqual(len(frames), 100)
        self.assertAlmostEqual(size[10] , size[0], delta=0.5)                 # before the push: the full frame
        self.assertAlmostEqual(size[60] / size[0], 1.5, delta=0.05)           # held at full zoom
        self.assertAlmostEqual(size[95], size[0], delta=0.5)                  # back out at the end
        moving = size[24:52]
        self.assertTrue(np.all(np.diff(moving) > -0.2))                       # never shrinks while moving in
        self.assertLess(np.abs(np.diff(moving, 2)).max(), 2.5)                # no jumps
        ys, xs = np.nonzero(frames[60] > 192)
        self.assertAlmostEqual(xs.mean(), 160, delta=1)                       # moved in on the centre, no drift
        self.assertAlmostEqual(ys.mean(), 120, delta=1)

    def test_51_held_product_zone_reaches_past_the_fingers(self):
        try:
            import cv2  # noqa: F401
        except ImportError:
            self.skipTest("needs OpenCV")
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        from handzone import hand_keep
        import numpy as np
        # a hand at the bottom holding something upwards: wrist low, knuckles above it, fingers higher still
        hand = [(200, 500)] + [(160 + 10 * i, 440 - 4 * i) for i in range(8)] + [(200, 420)] + \
               [(170 + 6 * i, 380 + 3 * i) for i in range(11)]
        shape = (600, 400)
        ring = hand_keep(hand, shape, pad=30, reach=0)
        zone = hand_keep(hand, shape, pad=30, reach=0.4)
        cap = (slice(320, 340), slice(170, 200))                                # above the fingers, where a cap is
        self.assertEqual(ring[cap].max(), 0)                                    # the ring alone misses it
        self.assertEqual(zone[cap].min(), 255)                                  # the stretch keeps it sharp
        self.assertEqual(zone[590:, :].max(), 255 if ring[590:, :].max() else 0)  # no stretch the other way
        self.assertLess(zone.mean(), ring.mean() * 1.8)                         # stays near the hand
        lost = hand_keep(hand, shape, pad=30, reach=0.4, missing=5, grow_lost=6)
        self.assertGreater(lost.mean(), zone.mean())                            # grows while the hand is lost
        self.assertTrue(np.all(lost[zone > 0] == 255))

    def test_52_forced_break_after_a_word_with_a_comma(self):
        words = [("Este", 0.0, 0.3), ("es", 0.3, 0.45), ("el", 0.45, 0.6), ("tono", 0.6, 0.9), ("Hypnotize,", 0.9, 1.34),
                 ("que", 1.44, 1.5), ("es", 1.5, 1.62), ("un", 1.62, 1.76)]
        (self.dir / "fb-voice.json").write_text(json.dumps({"segments": [{"words": [
            {"word": " " + w, "start": s, "end": e} for w, s, e in words]}]}), "utf-8")
        (self.dir / "fb-fix.json").write_text(json.dumps({"hypnotize": "Hypnotize|"}), "utf-8")
        script("captions.py", "fb-voice.json", "--on-cut", "--length", "2", "--font", "DejaVu Sans", "--max-words", "8",
               "--max-chars", "60", "--fix", "fb-fix.json", "--out", "fb-caps.ass", cwd=self.dir)
        caps = [c["text"] for c in json.loads((self.dir / "fb-caps.json").read_text("utf-8"))]
        self.assertEqual(caps, ["Este es el tono Hypnotize,", "que es un"])   # the break holds despite the comma

    def test_53_glow_keeps_the_skin_colour_and_hue(self):
        import numpy as np
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import beautify

        def lab(rgb):  # sRGB (0-255) to CIE Lab, D65
            c = np.asarray(rgb, float) / 255
            c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
            xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
            f = np.cbrt(xyz / [0.95047, 1.0, 1.08883])
            L, a, b = 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])
            return L, np.hypot(a, b), np.degrees(np.arctan2(b, a))

        def through(rgb, vf):
            # a little noise, like real skin, so the average isn't one rounded value
            out = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=0x%02X%02X%02X:s=256x256:d=0.1" % rgb,
                                  "-vf", f"format=yuv444p,noise=alls=6:all_seed=7,{vf},format=rgb24", "-frames:v", "1",
                                  "-f", "rawvideo", "-"],
                                 capture_output=True, check=True).stdout
            return np.frombuffer(out, np.uint8).reshape(-1, 3).mean(0)

        for skin in [(230, 190, 165), (205, 150, 125), (160, 110, 85), (110, 72, 55)]:   # light to deep, rosy to golden
            before = lab(through(skin, "null"))
            for g in (0.012, 0.022, 0.035):                                                # light, medium, strong
                after = lab(through(skin, beautify.glow_filter(g)))
                self.assertGreater(after[0], before[0], (skin, g))                         # lighter
                self.assertGreaterEqual(after[1], before[1] - 0.2, (skin, g))              # not paler or greyer
                self.assertLess(abs(after[2] - before[2]), 1.5, (skin, g))                 # not more orange, not pinker

    def test_54_reframe_holds_still_and_follows(self):
        import numpy as np
        sys.path.insert(0, str(SCRIPTS))
        import reframe
        width, height = 1280, 720
        crop_w = reframe.crop_width(height)
        self.assertEqual(crop_w, 404)
        rng = np.random.default_rng(1)
        times = [i * 0.2 for i in range(60)]                                   # 12 s
        # talking in place: small head movements never move the picture
        still = [(t, 640 + rng.normal(0, 12)) for t in times]
        start, moves, gaps = reframe.plan_path(still, width, crop_w)
        self.assertEqual((moves, gaps), ([], []))
        # a quick lean out and back (0.2 s) is ignored; a real step to the side is followed, eased, once
        lean = [(t, 640 + (90 if 2.0 <= t < 2.2 else 0) + 200 * min(max(t - 6, 0), 1)) for t in times]   # step over 1 s
        start, moves, _ = reframe.plan_path(lean, width, crop_w)
        self.assertEqual(len(moves), 1)
        self.assertGreater(moves[0][1] - moves[0][0], 0.3)                    # eased, not a jump
        self.assertAlmostEqual(reframe.centre_at(11.9, start, moves), 840, delta=1)
        # walking across the room: the face never leaves the picture
        walk = [(t, 300 + max(0.0, min(t - 2, 6)) * 110) for t in times]
        start, moves, _ = reframe.plan_path(walk, width, crop_w)
        for t, x in walk:
            self.assertLess(abs(x - reframe.centre_at(t, start, moves)), crop_w * 0.4, t)
        # a cut to another framing is a cut; the crop stays inside the frame; no face holds still and is listed
        cut = [(t, 300 if t < 4 else (None if t < 6 else 1100)) for t in times]
        start, moves, gaps = reframe.plan_path(cut, width, crop_w)
        self.assertEqual(gaps, [(4.0, 6.0)])
        self.assertEqual(moves[-1][0], moves[-1][1])                           # instant
        self.assertLessEqual(reframe.centre_at(11.9, start, moves), width - crop_w / 2)
        # FFmpeg draws the same path: a box that steps right at 6 s stays in the middle of the vertical video
        box = "overlay=x='if(lt(t,6),600,800)':y=300"   # (drawbox reads t only once, so overlay a red square)
        start, moves, _ = reframe.plan_path([(t, 640 if t < 6 else 840) for t in times], width, crop_w)
        line = reframe.filter_line(height, crop_w, start, moves, 360, 640)
        out = self.dir / "reframed.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=gray:s={width}x{height}:r=10:d=12",
             "-f", "lavfi", "-i", "color=red:s=80x80:r=10:d=12", "-filter_complex", f"[0][1]{box},{line}",
             "-c:v", "libx264", "-preset", "ultrafast", out])
        for t in (3, 11):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", out, "-frames:v", "1", "-f", "rawvideo",
                                  "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
            frame = np.frombuffer(raw, np.uint8).reshape(640, 360, 3).astype(int)
            red = np.where((frame[..., 0] > 150) & (frame[..., 1] < 100))[1]
            self.assertAlmostEqual(red.mean(), 180, delta=12, msg=t)

    def test_55_youtube_chapters(self):
        folder = self.dir / "chapters"
        folder.mkdir(exist_ok=True)
        caps = [{"start": 0.0, "end": 3.0, "words": [[0.5, 1.0, "Hola"], [1.0, 1.5, "a todos"]]},
                {"start": 40.0, "end": 44.0, "words": [[41.2, 41.6, "Vale,"], [41.6, 42.0, "empecemos"]]},
                {"start": 3700.0, "end": 3705.0, "words": [[3701.0, 3701.5, "Resumen"]]}]
        (folder / "captions.json").write_text(json.dumps(caps), "utf-8")

        def chapters(entries, *extra):
            (folder / "ch.json").write_text(json.dumps(entries), "utf-8")
            return script("chapters.py", "ch.json", *extra, cwd=folder)

        out = chapters([{"title": "Intro", "at": 4},                       # moved to 0:00
                        {"title": "Qué es un prompt", "say": "vale empecemos"},
                        {"title": "Resumen", "say": "resumen"}], "--length", "3800", "--ffmetadata", "ch.ffmeta")
        self.assertEqual((folder / "chapters.txt").read_text("utf-8").splitlines(),
                         ["0:00 Intro", "0:41 Qué es un prompt", "1:01:41 Resumen"])
        self.assertIn("Wrote ch.ffmeta", out)
        meta = (folder / "ch.ffmeta").read_text("utf-8")
        self.assertIn("START=41200", meta)
        self.assertIn("END=3800000", meta)
        for bad, reason in [([{"title": "A", "at": 0}, {"title": "B", "at": 50}], "at least 3"),
                            ([{"title": "A", "at": 30}, {"title": "B", "at": 50}, {"title": "C", "at": 90}], "0:00"),
                            ([{"title": "A", "at": 0}, {"title": "B", "at": 5}, {"title": "C", "at": 90}], "10 s"),
                            ([{"title": "A", "at": 0}, {"title": "B", "say": "no se dice"}, {"title": "C", "at": 90}],
                             "not said")]:
            with self.assertRaises(AssertionError, msg=reason) as err:
                chapters(bad)
            self.assertIn(reason, str(err.exception))

    def test_56_screen_zoom_and_stack(self):
        import numpy as np
        sys.path.insert(0, str(SCRIPTS))
        import screen
        folder = self.dir / "screen"
        folder.mkdir(exist_ok=True)
        # what changed: a pointer-sized blip is ignored, a typed line is found
        a = np.zeros((90, 160), np.uint8)
        b = a.copy()
        b[10:13, 20:23] = 200
        self.assertIsNone(screen.change_box(a, b))
        b[40:48, 30:90] = 200
        self.assertEqual(screen.change_box(a, b)[1:], (10, 70, 38))
        # typing along one line is one zoom; a new page zooms back out
        changes = [(2.0, (100, 120, 70, 40)), (2.5, (175, 120, 70, 40)), (3.0, (250, 120, 70, 40)),
                   (5.0, (0, 0, 1280, 720)), (6.0, None)]
        self.assertEqual(screen.plan_zooms(changes, 1280, 720),
                         [{"at": 0.0, "box": "full"}, {"at": 2.0, "box": [100, 120, 220, 40]}, {"at": 5.0, "box": "full"}])
        # the visible area keeps the video's shape, stays inside the frame and never zooms past the limit
        left, top, w = screen.fit_box([600, 340, 40, 20], 1280, 720, max_zoom=2.5)
        self.assertAlmostEqual(w, 512)
        self.assertTrue(0 <= left <= 1280 - w and 0 <= top <= 720 - w * 720 / 1280)
        # FFmpeg draws it: a white line in the middle of the screen fills much more of the frame once zoomed
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=0x303030:s=1280x720:r=10:d=4", "-f", "lavfi",
             "-i", "color=white:s=200x40:r=10:d=4", "-filter_complex", "[0][1]overlay=x=540:y=340,format=yuv420p",
             "-c:v", "libx264", "-preset", "ultrafast", "screen.mp4"], cwd=folder)
        (folder / "zooms.json").write_text(json.dumps([{"at": 0, "box": "full"}, {"at": 1, "box": [540, 340, 200, 40]}]),
                                           "utf-8")
        script("screen.py", "zoom", "screen.mp4", "zooms.json", cwd=folder)
        run(["ffmpeg", "-v", "error", "-y", "-i", "screen.mp4", filter_flag(), "zoom.txt", "-c:v", "libx264",
             "-preset", "ultrafast", "zoomed.mp4"], cwd=folder)

        def white_share(t):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", folder / "zoomed.mp4", "-frames:v", "1",
                                  "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
            return (np.frombuffer(raw, np.uint8) > 200).mean()
        self.assertGreater(white_share(3.0), white_share(0.5) * 4)
        # the vertical layout: screen on top, speaker below, 1080x1920, sound from the camera
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:s=1920x1080:r=10:d=2", "-f", "lavfi",
             "-i", "sine=d=2", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", "camera.mp4"],
            cwd=folder)
        script("screen.py", "stack", "zoomed.mp4", "camera.mp4", "--face-x", "1500", cwd=folder)
        run(["ffmpeg", "-v", "error", "-y", "-i", "zoomed.mp4", "-i", "camera.mp4", filter_flag(), "stack.txt",
             "-map", "[v]", "-map", "[a]", "-t", "2", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
             "stacked.mp4"], cwd=folder)
        out = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "csv=p=0",
                   "stacked.mp4"], cwd=folder)
        self.assertIn("1080,1920", out)
        self.assertIn("audio", out)
        self.assertEqual(screen.panel_crop(1920, 1080, 1080, 960, 1800), (1216, 1080, 704, 0))   # kept inside

    def test_57_youtube_thumbnail_template(self):
        tsx = (SCRIPTS / "remotion" / "Thumbnail.tsx").read_text("utf-8")
        default_props = next(l for l in tsx.splitlines() if "defaultProps=" in l)
        self.assertIn("lines: []", default_props)          # sample words would leak into real thumbnails
        self.assertNotIn("highlight", default_props)
        self.assertIn("width={1280}", tsx)
        self.assertIn("height={720}", tsx)
        face_box = (SCRIPTS / "cover" / "face_box.py").read_text("utf-8")
        for prop in ("bgWidth", "bgHeight", "faceX", "faceY", "faceSize"):   # what the template needs
            self.assertIn(f'"{prop}"', face_box)
            self.assertIn(f"{prop}:", tsx)

    def test_58_script_markers_in_both_languages(self):
        sys.path.insert(0, str(SCRIPTS))
        import scriptcut
        text = "\n".join(["# Título", "", "Hola, soy Malena.", "", "## [CAPÍTULO] Qué hace", '[PANTALLA] abrir "Claude"',
                          '[SHORT "El truco"]', "Le pido a Claude", "que quite las pausas.", "", "Y listo.", "[/SHORT]",
                          "## [CHAPTER] End", "> smile", "[GRAPHIC] a list",
                          "[CLIP] red-de-luz: slow push through glowing threads of light", "Thanks for watching!"])
        lines, chapters, shorts, notes = scriptcut.parse(text)
        self.assertEqual(lines, ["Hola, soy Malena.", "Le pido a Claude que quite las pausas.", "Y listo.",
                                 "Thanks for watching!"])                    # a paragraph is one line; > is not said
        self.assertEqual(chapters, [{"title": "Qué hace", "line": 1}, {"title": "End", "line": 3}])
        self.assertEqual(shorts, [{"title": "El truco", "first": 1, "last": 2}])
        self.assertEqual(notes, [{"kind": "screen", "text": 'abrir "Claude"', "line": 1},
                                 {"kind": "graphic", "text": "a list", "line": 3},
                                 {"kind": "clip", "text": "red-de-luz: slow push through glowing threads of light",
                                  "line": 3}])                               # an AI clip is a note for the edit

    def test_59_script_keeps_the_last_good_take(self):
        folder = self.dir / "script"
        folder.mkdir(exist_ok=True)
        (folder / "script.md").write_text("\n".join([
            "Hola, soy Malena y hoy os enseño cómo edito mis vídeos con IA.", "", "## [CAPÍTULO] Qué hace la skill",
            '[SHORT "La IA que me ahorra horas"]', "Le pido a Claude que quite las pausas y los errores.", "",
            "Y en dos minutos tengo el vídeo listo.", "[/SHORT]", "", "Esta línea no la digo nunca en el vídeo.", "",
            "## [CHAPTER] Resultado", "Este es el resultado final, ¿qué os parece?"]), "utf-8")
        said = ("hola soy malena y hoy | Hola, soy Malena y hoy os enseno como edito mis videos con IA. | le pido a "
                "claude que quite las pausas y los errores | bueno esto lo grabo otra vez porque me he liado | le pido "
                "a cloud que quite las pausas y errores | y en dos minutos tengo el video listo | este es el resultado "
                "final que os parece")
        words, t = [], 0.5
        for w in said.split():
            if w == "|":
                t += 1.5
                continue
            words.append({"word": " " + w, "start": round(t, 2), "end": round(t + 0.3, 2)})
            t += 0.35
        (folder / "tr.json").write_text(json.dumps({"segments": [{"words": words}]}), "utf-8")
        (folder / "cuts.json").write_text(json.dumps({"remove": [[50, 51, "a cough"], [1, 2, "script: old entry"]]}),
                                          "utf-8")
        out = script("scriptcut.py", "script.md", "tr.json", cwd=folder)
        self.assertIn("5 lines: 4 found, 1 not said", out)
        report = (folder / "script-report.md").read_text("utf-8")
        self.assertIn("NOT SAID: Esta línea", report)
        self.assertIn("bueno esto lo grabo otra vez", report)                  # kept, for the user to decide
        cuts = json.loads((folder / "cuts.json").read_text("utf-8"))["remove"]
        self.assertIn([50, 51, "a cough"], cuts)                               # the user's own cuts stay
        self.assertNotIn([1, 2, "script: old entry"], cuts)                    # its own earlier entries are replaced
        labels = [c[2] for c in cuts]
        self.assertIn("script: false start of line 1", labels)
        self.assertIn("script: other take of line 2", labels)
        first_take = next(c for c in cuts if c[2] == "script: other take of line 2")
        self.assertAlmostEqual(first_take[0], 9.75, delta=0.06)               # the first take of line 2 goes
        self.assertLess(first_take[1], 15.15)                                  # and the aside after it is kept
        self.assertEqual(json.loads((folder / "chapters.json").read_text("utf-8")),
                         [{"title": "Intro", "at": 0}, {"title": "Qué hace la skill", "say": "le pido a cloud"},
                          {"title": "Resultado", "say": "este es el resultado"}])
        self.assertEqual(json.loads((folder / "shorts.json").read_text("utf-8")),
                         [{"title": "La IA que me ahorra horas", "say": "le pido a cloud",
                           "until": "tengo el video listo"}])
        script("scriptcut.py", "script.md", "tr.json", "--drop-unscripted", cwd=folder)
        labels = [c[2] for c in json.loads((folder / "cuts.json").read_text("utf-8"))["remove"]]
        self.assertIn("script: not in the script", labels)

    def test_60_script_cut_builds_with_cutplan(self):
        (self.dir / "sc-script.md").write_text("Hola amigos.\n\nHoy glow serum es genial.\n", "utf-8")
        script("scriptcut.py", "sc-script.md", "tr.json", "--cuts", "sc-cuts.json", cwd=self.dir)
        cuts = json.loads((self.dir / "sc-cuts.json").read_text("utf-8"))["remove"]
        self.assertEqual(len(cuts), 1)                                         # "Hola amigas" is the earlier take
        self.assertLess(cuts[0][0], 0.5)
        self.assertLess(cuts[0][1], 2.5)
        script("cutplan.py", "build", "src.mp4", "tr.json", "--cuts", "sc-cuts.json", "--out", "sc-plan.json",
               cwd=self.dir)
        frames = json.loads((self.dir / "sc-plan.json").read_text("utf-8"))["frames"]
        self.assertGreaterEqual(frames[0][0] / FPS, 1.5)                       # the first take is cut

    def test_61_shorts_from_the_long_video(self):
        folder = self.dir / "shorts-test"
        folder.mkdir(exist_ok=True)
        caps, t = [], 0.0
        for w in ("hola a todos " + "palabra " * 40 + "le pido a claude " + "que quite " * 30 + "tengo el vídeo listo "
                  + "adiós").split():
            caps.append({"start": t, "end": t + 0.4, "words": [[round(t, 2), round(t + 0.38, 2), w.upper()]]})
            t += 0.4
        (folder / "captions.json").write_text(json.dumps(caps), "utf-8")
        (folder / "shorts.json").write_text(json.dumps([
            {"title": "El truco", "say": "Le pido a Claude", "until": "tengo el video listo"},
            {"title": "Corto", "say": "hola a todos", "until": "hola a todos"},
            {"title": "Falta", "say": "esto no se dice"}]), "utf-8")
        out = script("shorts.py", "shorts.json", "--video", "long.mp4", cwd=folder)
        rng = json.loads((folder / "shorts" / "short-1" / "range.json").read_text("utf-8"))
        self.assertAlmostEqual(rng["start"], 43 * 0.4 - 0.02, delta=0.03)       # never into the word before
        self.assertAlmostEqual(rng["end"], (43 + 4 + 60 + 4) * 0.4, delta=0.03)  # room, but not into "adiós"
        words = json.loads((folder / "shorts" / "short-1" / "words.json").read_text("utf-8"))["segments"][0]["words"]
        self.assertEqual(words[0]["word"], " LE")
        self.assertAlmostEqual(words[0]["start"], 0.02, delta=0.03)            # moved to start at 0
        self.assertEqual(words[-1]["word"], " LISTO")
        self.assertIn("reframe.py", (folder / "shorts" / "short-1" / "steps.txt").read_text("utf-8"))
        self.assertIn("under 15 s", out)                                       # "Corto"
        self.assertIn("Short 3 skipped", out)

    def test_67_background_already_blurred(self):
        import numpy as np
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import blurcheck
        rng = np.random.default_rng(3)
        sharp = (rng.random((480, 640)) > 0.5).astype(np.float32) * 255   # detail everywhere, face and background
        face = (240, 120, 400, 330)                                          # forehead-to-chin box, mid-frame

        def blur(img, k=15):                                                 # a box blur, k times each way
            out = img.copy()
            for axis in (0, 1):
                out = sum(np.roll(out, s, axis=axis) for s in range(-(k // 2), k // 2 + 1)) / k
            return out
        soft = blur(sharp)
        inner, _ = blurcheck.regions(640, 480, face)
        soft[inner[1]:inner[3], inner[0]:inner[2]] = sharp[inner[1]:inner[3], inner[0]:inner[2]]   # face in focus
        r_sharp, r_soft = blurcheck.ratio(sharp, face), blurcheck.ratio(soft, face)
        self.assertEqual(blurcheck.verdict(r_sharp), "sharp")
        self.assertEqual(blurcheck.verdict(r_soft), "already soft")
        self.assertEqual(blurcheck.verdict(0.5), "a little soft")
        # a close-up with no room beside or above the head has nothing to measure
        self.assertIsNone(blurcheck.ratio(sharp, (5, 5, 635, 475)))

    def test_68_footage_check(self):
        sys.path.insert(0, str(SCRIPTS))
        import footcheck
        # the user's real Blackmagic clip, as ffprobe described it (only the fields the check reads)
        blackmagic = {"format": {"bit_rate": "42000000", "tags": {
            "com.apple.quicktime.software": "Blackmagic Cam 3.5.300023",
            "com.apple.quicktime.model": "Apple iPhone 16 Pro Max Front",
            "com.blackmagic-design.shutterSpeed": "1/613",
            "com.blackmagic-design.camera.lensType": "iPhone 16 Pro Max Front"}},
            "streams": [{"codec_type": "video", "width": 3840, "height": 2160, "r_frame_rate": "24/1",
                         "color_transfer": "bt709", "side_data_list": [{"rotation": 90}]},
                        {"codec_type": "audio", "sample_rate": "16000"}]}
        who, findings = footcheck.check(blackmagic, mains=50, target="wide")
        self.assertEqual((who["app"], who["lens"], who["confirmed"]), ("blackmagic", "front", True))
        found = {f["what"]: f for f in findings}
        self.assertIn("choose 25", found["frame rate"]["fix"])
        self.assertIn("1/50", found["shutter"]["fix"])
        self.assertIn("vertical", found["orientation"]["found"])                 # rotated 90: filmed upright
        self.assertIn("Bluetooth", found["sound"]["fix"])
        self.assertIn("camera", found)
        # a good iPhone recording in Spain: nothing to change; in a 60 Hz country the frame rate is flagged
        iphone = {"format": {"bit_rate": "50000000", "tags": {"com.apple.quicktime.make": "Apple",
                                                              "com.apple.quicktime.model": "iPhone 15"}},
                  "streams": [{"codec_type": "video", "width": 3840, "height": 2160, "r_frame_rate": "25/1"},
                              {"codec_type": "audio", "sample_rate": "48000"}]}
        who, findings = footcheck.check(iphone, mains=50, shorts=True, target="wide")
        self.assertEqual((who["app"], findings), ("apple_camera", []))
        _, findings = footcheck.check(iphone, mains=60)
        self.assertIn("Show PAL Formats", findings[0]["fix"])  # same menu, the fps differs
        self.assertIn("30 fps", findings[0]["fix"])
        # HDR, a 1080p horizontal clip for Shorts, and a squeezed file with no camera details
        hdr = {"format": {"bit_rate": "2000000", "tags": {}},
               "streams": [{"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1",
                            "color_transfer": "arib-std-b67"}, {"codec_type": "audio", "sample_rate": "44100"}]}
        who, findings = footcheck.check(hdr, mains=60, shorts=True)
        self.assertIsNone(who["app"])
        self.assertEqual({f["what"] for f in findings}, {"resolution", "HDR", "quality"})
        # end to end on a real file with Blackmagic-style tags written into it
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=24:d=1", "-f", "lavfi", "-i",
             "sine=d=1:sample_rate=16000", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
             "-movflags", "use_metadata_tags", "-metadata", "com.apple.quicktime.software=Blackmagic Cam 3.5",
             "-metadata", "com.blackmagic-design.shutterSpeed=1/500", "fc.mov"], cwd=self.dir)
        out = script("footcheck.py", "fc.mov", "--mains", "50", cwd=self.dir)
        self.assertIn("Blackmagic Camera app", out)
        self.assertIn("1/50", out)
        self.assertIn("16 kHz", out)

    def test_62_puppet_dialogue_format(self):
        sys.path.insert(0, str(PUPPET / "scripts"))
        import dialogue
        chars, turns = dialogue.parse("\n".join([
            "# a comment", "[Lola] voice=en_GB-cori-medium look=lola", "[Pixel] voice=es_ES-sharvard-medium speaker=F",
            "Lola: Hi! Could I have a flat white? | ¡Hola! ¿Me pones un café?", "> Pixel: sorprendida", "> pausa 0.5",
            "> a note for Claude, not said", "Pixel: ¿Un café?"]))
        self.assertEqual(chars["Pixel"], {"voice": "es_ES-sharvard-medium", "speaker": "F", "look": "max", "colour": None,
                                          "skin": None, "hair": None})
        self.assertEqual(turns[0]["translation"], "¡Hola! ¿Me pones un café?")
        self.assertEqual((turns[1]["expression"], turns[1]["pause_before"]), ("surprised", 0.5))
        for bad in ("Lola: hello", "[Lola] look=lola\nLola: hi", "[Lola] voice=x look=dragon\nLola: hi",
                    "[Lola] voice=x\n> Lola: angry\nLola: hi"):
            with self.assertRaises(ValueError, msg=bad):
                dialogue.parse(bad)

    def test_63_puppet_mouths_from_loudness(self):
        sys.path.insert(0, str(PUPPET / "scripts"))
        import dialogue
        import math
        rate = 48000
        samples = [0] * (rate // 2) + [int(12000 * math.sin(2 * math.pi * 200 * i / rate)) for i in range(rate)] \
            + [0] * (rate // 2)
        cues = dialogue.loudness_cues(samples, rate)
        shape_at = lambda t: next(c["value"] for c in cues if c["start"] <= t < c["end"])
        self.assertEqual(shape_at(0.2), "X")                                     # closed in silence
        self.assertIn(shape_at(1.0), ("C", "D"))                                 # open while it sounds
        self.assertEqual(shape_at(1.8), "X")
        self.assertTrue(all(c["end"] - c["start"] >= 1 / 30 * 1.5 - 1e-9 for c in cues[1:-1]))   # no flicker

    def test_64_puppet_voice_track_and_props(self):
        folder = self.dir / "puppet"
        folder.mkdir(exist_ok=True)
        (folder / "rec").mkdir(exist_ok=True)
        for i, (freq, d) in enumerate([(220, 1.0), (330, 1.5), (440, 0.8)], 1):
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                 f"aevalsrc='0.4*sin(2*PI*{freq}*t)':s=48000:d={d}", "-af", "adelay=200,apad=pad_dur=0.3",
                 f"rec/{i:02d}.wav"], cwd=folder)
        (folder / "d.md").write_text("[Lola] voice=en_GB-cori-medium look=lola\n[Max] voice=x look=max\n"
                                     "Lola: Hello there! | ¡Hola!\nMax: Hi.\n> pause 0.5\nLola: Bye.\n", "utf-8")
        out = script(PUPPET / "scripts" / "dialogue.py", "d.md", "--audio-dir", "rec", "--no-rhubarb", "--gap", "0.4",
                     "--out-dir", "out", cwd=folder)
        self.assertIn("3 turns", out)
        props = json.loads((folder / "out" / "puppet-props.json").read_text("utf-8"))
        turns = props["turns"]
        self.assertEqual([t["speaker"] for t in turns], ["Lola", "Max", "Lola"])
        self.assertAlmostEqual(turns[0]["start"], 0.4, delta=0.01)
        for t, d in zip(turns, (1.0, 1.5, 0.8)):                                 # silence trimmed to a short margin
            self.assertAlmostEqual(t["end"] - t["start"], d + 0.08, delta=0.05)
        self.assertAlmostEqual(turns[1]["start"] - turns[0]["end"], 0.4, delta=0.01)
        self.assertAlmostEqual(turns[2]["start"] - turns[1]["end"], 0.9, delta=0.01)   # gap + pause
        self.assertAlmostEqual(props["length"], turns[2]["end"] + 0.8, delta=0.01)
        _, _, audio = probe_audio(folder / "out" / "voice.wav")
        self.assertAlmostEqual(audio, props["length"], delta=0.05)
        self.assertTrue(all(t["mouth"][0][0] >= t["start"] - 1e-6 for t in turns))
        self.assertEqual(turns[0]["translation"], "¡Hola!")

    def test_65_puppet_captions_use_the_script_words(self):
        props = {"turns": [{"text": "Hmm... a croissant, too.", "start": 1.0, "end": 3.0},
                           {"text": "That's four pounds fifty.", "start": 3.5, "end": 5.5}]}
        heard = {"segments": [{"words": [{"word": " I'm", "start": 1.0, "end": 1.4},
                                         {"word": " a", "start": 1.5, "end": 1.6},
                                         {"word": " croissant", "start": 1.6, "end": 2.2},
                                         {"word": " too.", "start": 2.3, "end": 2.8},
                                         {"word": " That's", "start": 3.5, "end": 3.9},
                                         {"word": " £4.50.", "start": 4.0, "end": 5.4}]}]}
        (self.dir / "pp.json").write_text(json.dumps(props), "utf-8")
        (self.dir / "heard.json").write_text(json.dumps(heard), "utf-8")
        out = script(PUPPET / "scripts" / "captionwords.py", "pp.json", "--transcript", "heard.json", "--out", "pw.json",
                     cwd=self.dir)
        self.assertIn("4 of 8 words matched", out)          # a, croissant, too, That's
        words = json.loads((self.dir / "pw.json").read_text("utf-8"))["segments"][0]["words"]
        self.assertEqual(" ".join(w["word"].strip() for w in words),
                         "Hmm... a croissant, too. That's four pounds fifty.")   # as written, never as heard
        croissant = next(w for w in words if w["word"].strip() == "croissant,")
        self.assertEqual((croissant["start"], croissant["end"]), (1.6, 2.2))     # timed from the transcript
        four, fifty = words[5], words[7]
        self.assertTrue(3.9 <= four["start"] < fifty["start"] <= 5.5)            # the rest spread in between
        self.assertTrue(all(b["start"] >= a["start"] for a, b in zip(words, words[1:])))

    def test_66_puppet_template(self):
        tsx = (PUPPET / "scripts" / "remotion" / "Puppet.tsx").read_text("utf-8")
        default_props = next(l for l in tsx.splitlines() if "defaultProps=" in l)
        self.assertIn("characters: [], turns: []", default_props)               # sample turns would leak
        for shape in "ABCDEFGH":                                                  # every mouth shape is drawn
            self.assertIn(f'case "{shape}":', tsx)
        sys.path.insert(0, str(PUPPET / "scripts"))
        import dialogue
        registered = re.search(r"LOOK_COMPONENTS[^=]*=\s*\{([^}]*)\}", tsx).group(1)
        for look in dialogue.LOOKS:                                               # every look the script accepts exists
            self.assertIn(f"{look}:", registered)
        skill = (PUPPET / "SKILL.md").read_text("utf-8")
        self.assertTrue(skill.startswith("---\nname: puppet-video\n"))
        for path in set(re.findall(r"<skill>/((?:scripts|references)/[\w/.-]+\.\w+)", skill)):
            self.assertTrue((PUPPET / path).exists(), path)
        for path in set(re.findall(r"<editor>/(scripts/[\w/.-]+\.\w+)", skill)):
            self.assertTrue((ROOT / path).exists(), path)

    def test_69_puppet_people_colours(self):
        sys.path.insert(0, str(PUPPET / "scripts"))
        import dialogue
        chars, _ = dialogue.parse("[Max] voice=x look=max color=#2F5D62 skin=#8D5A3B hair=#1E1A18\nMax: Hello.")
        self.assertEqual({k: chars["Max"][k] for k in ("colour", "skin", "hair")},
                         {"colour": "#2F5D62", "skin": "#8D5A3B", "hair": "#1E1A18"})   # color= is accepted too
        for bad in ("skin=brown", "hair=#12345", "colour=red"):                        # a typo fails before rendering
            with self.assertRaises(ValueError, msg=bad):
                dialogue.parse(f"[Max] voice=x look=max {bad}\nMax: Hello.")
        tsx = (PUPPET / "scripts" / "remotion" / "Puppet.tsx").read_text("utf-8")
        self.assertIn("skin={c.skin} hair={c.hair}", tsx)                              # the template uses them
        src = (PUPPET / "scripts" / "dialogue.py").read_text("utf-8")
        self.assertRegex(src, r'"skin": c\["skin"\],\s*"hair": c\["hair"\]')        # and the props carry them

    def test_86_forehead_edge_is_gradual(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV or numpy not installed")
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import feather
        import settings
        h, w, face_h = 1000, 600, 750.0
        base = np.zeros((h, w), np.float32)
        base[300:, :] = 1.0                                   # the face area: its top edge is at row 300
        tone = np.ones((h, w), np.float32)
        tone[:150, :] = 0.0                                   # hair and background above the forehead: not skin-coloured
        keep = np.ones((h, w), np.float32)
        keep[600:640, 200:400] = 0.0                          # something protected (an eye) inside the face

        def edge_width(m):
            col = m[:420, 100]                                # the top edge only (the protected eye is elsewhere)
            rows = np.nonzero((col > 0.1) & (col < 0.9))[0]
            return int(rows.max() - rows.min() + 1) if len(rows) else 0

        old = feather.soft_skin(base, tone, keep, face_h, 0)
        new = feather.soft_skin(base, tone, keep, face_h, 0.04)
        self.assertLess(edge_width(old), 30)                                  # the old edge: a few pixels wide
        self.assertGreater(edge_width(new), 2 * edge_width(old))              # now a forehead's worth
        self.assertGreaterEqual(edge_width(new), 0.5 * 0.04 * face_h * 2)
        self.assertTrue(0.0 <= new.min() and new.max() <= 1.0)
        self.assertEqual(float(new[:150, :].max()), 0.0)                      # hair and background aren't smoothed
        self.assertLess(float(new[620, 300]), 0.05)                           # the protected part stays untouched
        self.assertGreater(float(new[800, 300]), 0.99)                        # deep inside the face: full strength
        self.assertEqual(float(np.abs(old - cv2.GaussianBlur(base * keep, (0, 0), 9)).max()), 0.0)   # 0 = as before
        self.assertEqual(settings.DEFAULTS["forehead_feather"], 0.04)
        with tempfile.TemporaryDirectory() as tmp:
            for value, ok in ((0, True), (0.07, True), (-0.1, False), (0.5, False), ("soft", False)):
                (Path(tmp) / "retouch.json").write_text(json.dumps({"forehead_feather": value}), "utf-8")
                result = subprocess.run([sys.executable, "-I", "-c",
                    f"import sys; sys.path.insert(0, r'{SCRIPTS / 'retouch'}'); import settings; settings.load()"],
                    cwd=tmp, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, ok, f"{value}: {result.stderr[-200:]}")

    def test_87_grain_under_brow_is_smoothed_not_kept_as_hair(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV or numpy not installed")
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import spots
        rng = np.random.default_rng(5)
        h, w = 700, 900
        luma = np.full((h, w), 190, np.float32) + rng.normal(0, 1.5, (h, w)).astype(np.float32)
        brow = np.zeros((h, w), np.uint8)
        cv2.ellipse(brow, (450, 200), (150, 22), 0, 0, 360, 255, -1)
        cv2.ellipse(luma, (450, 200), (150, 12), 0, 0, 360, 80, -1)            # the brow's dark hairs
        for x in (330, 400, 470, 540):
            cv2.line(luma, (x, 170), (x + 12, 182), 100, 2)                    # hairs poking out above it
        patch = np.zeros((h, w), bool)
        patch[224:246, 380:450] = True                                          # a grainy, shimmery patch right under it
        for _ in range(60):
            x, y = int(rng.integers(382, 448)), int(rng.integers(226, 244))
            cv2.circle(luma, (x, y), int(rng.integers(1, 3)), 150, -1)          # specks 2-5 px wide, 40 levels darker
        for face_h in (600, 1200):                                              # the bigger the face, the wider the old band
            keep = spots.brow_hair_keep(luma, brow, 14, face_h)
            self.assertGreater(float(keep[150:215, 320:580].max()), 0.9, face_h)          # the brow's own hairs stay sharp
            self.assertGreater(float(keep[170:182, 334:344].max()), 0.9, face_h)         # and so do the strays above it
            self.assertLess(float(keep[patch].mean()), 0.2, face_h)             # the grain is skin: it gets smoothed
        old = cv2.GaussianBlur(luma, (0, 0), 20) - luma > 14                     # the 2.14.1 rule at face_h 1200
        zone = cv2.dilate(brow, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (43, 43))) > 0
        _, labels, stats, _ = cv2.connectedComponentsWithStats((old & zone).astype(np.uint8), connectivity=8)
        grown = cv2.dilate(brow, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (14, 14))) > 0
        touching = {i for i in np.unique(labels[grown]) if i}
        self.assertTrue(any((labels == i)[patch].any() for i in touching))      # that rule did attach it to the brow
        skin = np.ones((h, w), np.float32)
        exclude = (brow > 0) | (spots.brow_hair_keep(luma, brow, 14, 600) > 0.2)
        mask = spots.spot_mask(luma, skin, exclude, 600, 14)
        self.assertGreater(float(mask[patch].max()), 0.5)                      # the specks reach the spot pass

    def test_88_shimmer_specks_are_calmed_not_reflections(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV or numpy not installed")
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import settings
        import spots
        rng = np.random.default_rng(7)
        h, w = 700, 900
        luma = np.full((h, w), 180, np.float32) + rng.normal(0, 1.0, (h, w)).astype(np.float32)
        patch = np.zeros((h, w), bool)
        patch[230:256, 380:450] = True                                          # a shimmery patch under a brow
        for _ in range(70):
            cv2.circle(luma, (int(rng.integers(382, 448)), int(rng.integers(232, 254))), int(rng.integers(1, 3)), 205, -1)
        cv2.circle(luma, (700, 400), 9, 255, -1)                                # a real reflection: much brighter
        luma[300:340, 100:200] = 215                                            # a broad highlight: not a speck
        skin = np.ones((h, w), np.float32)
        none = np.zeros((h, w), bool)
        bright = spots.spot_mask(luma, skin, none, 700, 8, bright=True)
        self.assertGreater(float(bright[patch].max()), 0.8)                     # the specks reach the mask
        self.assertGreater(float(bright[patch].mean()), 0.1)
        self.assertEqual(float(bright[395:405, 695:705].max()), 0.0)            # a reflection stays as it is
        self.assertEqual(float(bright[310:330, 120:180].max()), 0.0)            # so does a broad highlight
        dark = spots.spot_mask(luma, skin, none, 700, 14)                       # the dark pass ignores bright specks
        self.assertEqual(float(dark[patch].max()), 0.0)
        self.assertEqual((settings.DEFAULTS["shimmer_calm"], settings.DEFAULTS["shimmer_contrast"]), (0.6, 8))
        with tempfile.TemporaryDirectory() as tmp:
            for value, ok in ((0, True), (1, True), (1.5, False), ("a lot", False)):
                (Path(tmp) / "retouch.json").write_text(json.dumps({"shimmer_calm": value}), "utf-8")
                result = subprocess.run([sys.executable, "-I", "-c",
                    f"import sys; sys.path.insert(0, r'{SCRIPTS / 'retouch'}'); import settings; settings.load()"],
                    cwd=tmp, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, ok, f"{value}: {result.stderr[-200:]}")

    def test_89_fast_masks_match_full_frame(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV or numpy not installed")
        sys.path.insert(0, str(SCRIPTS / "retouch"))
        import beauty
        import feather
        import roi
        import spots
        rng = np.random.default_rng(3)

        def scene(h, w, cx, cy, fh):
            frame = np.full((h, w, 3), (150, 170, 210), np.uint8)
            frame = cv2.add(frame, rng.integers(0, 12, (h, w, 3), dtype=np.uint8))
            pts = np.zeros((478, 2), np.float32)
            ang = np.linspace(0, 2 * np.pi, 478, endpoint=False)
            pts[:, 0], pts[:, 1] = cx + 0.38 * fh * np.cos(ang), cy + 0.5 * fh * np.sin(ang)
            for k, eye in enumerate(beauty.EYES):
                ex, ey = cx + (-1 if k == 0 else 1) * 0.17 * fh, cy - 0.08 * fh
                for j, i in enumerate(beauty.EYE_OUTLINE[k]):
                    a = 2 * np.pi * j / len(beauty.EYE_OUTLINE[k])
                    pts[i] = (ex + 0.08 * fh * np.cos(a), ey + 0.03 * fh * np.sin(a))
                for j, i in enumerate(eye["lower"]):
                    pts[i] = (ex - 0.08 * fh + 0.02 * fh * j, ey + 0.03 * fh)
                pts[eye["corners"][0]], pts[eye["corners"][1]] = (ex - 0.08 * fh, ey), (ex + 0.08 * fh, ey)
                pts[eye["iris"][0]] = (ex, ey)
                for j, i in enumerate(eye["iris"][1:]):
                    pts[i] = (ex + 0.025 * fh * np.cos(j * np.pi / 2), ey + 0.025 * fh * np.sin(j * np.pi / 2))
                cv2.circle(frame, (int(ex), int(ey)), int(0.025 * fh), (40, 40, 60), -1)
            luma = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)[..., 0].astype(np.float32)
            for _ in range(int(fh / 4)):                                        # dark and bright specks
                cv2.circle(luma, (int(rng.uniform(cx - 0.3 * fh, cx + 0.3 * fh)), int(rng.uniform(cy - 0.3 * fh, cy + 0.4 * fh))),
                           int(rng.integers(1, 4)), float(rng.choice([150, 215])), -1)
            region = np.zeros((h, w), np.uint8)
            cv2.fillPoly(region, [cv2.convexHull(pts.astype(np.int32))], 255)
            tone = np.ones((h, w), np.float32)
            tone[:max(0, int(cy - 0.6 * fh))] = 0
            brow = np.zeros((h, w), np.uint8)
            cv2.ellipse(brow, (int(cx - 0.17 * fh), int(cy - 0.15 * fh)), (int(0.12 * fh), int(0.02 * fh)), 0, 0, 360, 255, -1)
            cv2.ellipse(luma, (int(cx - 0.17 * fh), int(cy - 0.15 * fh)), (int(0.12 * fh), int(0.01 * fh)), 0, 0, 360, 80, -1)
            return frame, luma, pts, tone, region.astype(np.float32) / 255 * tone, brow

        def both(fn):
            roi.FAST = False
            try:
                ref = np.asarray(fn(), np.float32)
            finally:
                roi.FAST = True
            return ref, np.asarray(fn(), np.float32)

        for h, w, cx, cy, fh in ((1280, 720, 360, 600, 650.0), (1280, 720, 360, 500, 200.0), (1280, 720, 60, 600, 600.0)):
            frame, luma, pts, tone, base, brow = scene(h, w, cx, cy, fh)       # a close-up, a small face, a face at the edge
            keep, none, shape = np.ones((h, w), np.float32), np.zeros((h, w), bool), (h, w)
            for feather_share in (0.04, 0):
                ref, fast = both(lambda: feather.soft_skin(base, tone, keep, fh, feather_share))
                self.assertLess(float(np.abs(ref - fast).max()) * 255, 2.0, (fh, feather_share))   # within 2 levels of 255
            ref, fast = both(lambda: spots.brow_hair_keep(luma, brow, 14, fh))
            self.assertLess(float(np.abs(ref - fast).max()), 0.01, fh)
            mask = feather.soft_skin(base, tone, keep, fh, 0.04)
            for bright, contrast in ((False, 14), (True, 8)):
                ref, fast = both(lambda: spots.spot_mask(luma, mask, none, fh, contrast, bright=bright))
                self.assertLess(float(np.mean((ref > 0.5) != (fast > 0.5))), 0.001, (fh, bright))  # a borderline speck may flip
            for fn in (lambda: beauty.under_eye(pts, shape), lambda: beauty.eye_whites(frame, luma, pts, shape)):
                ref, fast = both(fn)
                self.assertEqual(float(np.abs(ref - fast).max()), 0.0, fh)
        empty = np.zeros((100, 100), np.float32)
        self.assertEqual(float(feather.soft_skin(empty, empty, empty + 1, 80, 0.04).max()), 0.0)   # no face: nothing
        self.assertEqual(float(spots.spot_mask(empty, empty, empty > 0, 80).max()), 0.0)
        self.assertIn("ms a frame", (SCRIPTS / "retouch" / "mask.py").read_text("utf-8"))    # mask.py reports its speed

    def test_90_letters_behind_the_speaker(self):
        try:
            import numpy as np
            from PIL import ImageFont  # noqa: F401
        except ImportError:
            self.skipTest("needs numpy and Pillow")
        font = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
                                 "/System/Library/Fonts/Supplemental/Arial Bold.ttf") if Path(p).exists()), None)
        if not font:
            self.skipTest("no bold font found")
        folder = self.dir / "behind"
        folder.mkdir(exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=gray:s=540x960:r=30:d=3", "-f", "lavfi", "-i",
             "sine=d=3", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
             "retouched.mp4"], cwd=folder)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=white:s=270x480:r=30:d=3", "-vf",   # half size
             "drawbox=x=135:y=0:w=135:h=480:color=black:t=fill,format=gray", "-c:v", "ffv1", "bgmask.mkv"], cwd=folder)
        (folder / "captions.json").write_text(json.dumps([{"start": 0.5, "end": 2.5, "text": "la inteligencia artificial",
            "words": [[0.5, 0.7, "la"], [0.7, 1.4, "inteligencia"], [1.4, 2.5, "artificial"]]}]), "utf-8")
        out = script("behindtext.py", "HOLA|IA", "--say", "inteligencia artificial", "--font", font, "--color",
                     "#FF0000", "--fade", "0", cwd=folder)
        self.assertIn("from 0.70 to 2.50 s", out)                              # to the end of that caption
        self.assertIn("scaled to 540x960", out)
        run(["ffmpeg", "-v", "error", "-y", "-i", "retouched.mp4", "-i", "bgmask.mkv", "-loop", "1", "-framerate", "30",
             "-i", "behindtext.png", filter_flag(), "behindtext.txt", "-map", "[v]", "-map", "0:a?", "-c:v", "libx264",
             "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "copy", "behind.mp4"], cwd=folder)
        frames = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                      "stream=nb_read_frames", "-of", "csv=p=0", "behind.mp4"], cwd=folder)
        self.assertEqual(int(frames.strip()), 90)                              # no frame lost or added

        def red_at(t):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", "behind.mp4", "-frames:v", "1", "-f",
                                  "rawvideo", "-pix_fmt", "rgb24", "-"], cwd=folder, capture_output=True).stdout
            f = np.frombuffer(raw, np.uint8).reshape(960, 540, 3).astype(int)
            red = (f[..., 0] > 180) & (f[..., 1] < 80)
            return red[:, :260].sum(), red[:, 280:].sum()

        self.assertEqual(red_at(0.3), (0, 0))                                  # not yet
        left, right = red_at(1.6)
        self.assertGreater(left, 2000)                                         # the letters show in the background
        self.assertEqual(right, 0)                                             # and never over the speaker
        self.assertEqual(red_at(2.8), (0, 0))                                  # gone again

    def test_33_docs_point_to_files_that_exist(self):
        text = (ROOT / "SKILL.md").read_text("utf-8")
        for ref in set(re.findall(r"references/[\w-]+\.md", text)):
            self.assertTrue((ROOT / ref).exists(), ref)
        docs = text + "".join(p.read_text("utf-8") for p in (ROOT / "references").glob("*.md"))
        for path in set(re.findall(r"<skill>/(scripts/[\w/.-]+\.\w+|[\w-]+\.md)", docs)):
            if path != "my-setup.md":
                self.assertTrue((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
