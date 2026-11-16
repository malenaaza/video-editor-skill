"""Tests the skill's scripts on a small generated clip. No real footage or Whisper needed.

Run: python tests/test_skill.py
Needs Python 3.10+, FFmpeg, ffprobe and numpy. The colour key test also needs OpenCV and is
skipped without it. The face-tracking scripts (masks, mouth check) and the Whisper scripts
are only compiled here, not run.
"""
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "video-editor"
SCRIPTS = ROOT / "scripts"
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
        for path in SCRIPTS.rglob("*.py"):
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
        for name in ("skin", "teeth", "strong", "bg"):
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=gray:s=540x960:r={FPS}:d=0.5",
                 "-pix_fmt", "gray", "-c:v", "ffv1", f"{name}.mkv"], cwd=self.dir)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=540x960:r={FPS}:d=0.5",
             "-c:v", "libx264", "-preset", "ultrafast", "clean.mp4"], cwd=self.dir)
        masks = ["-i", "skin.mkv", "-i", "teeth.mkv", "-i", "strong.mkv"]
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
