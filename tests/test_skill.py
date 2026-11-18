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

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "plugins" / "video-editor" / "skills" / "video-editor"
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
