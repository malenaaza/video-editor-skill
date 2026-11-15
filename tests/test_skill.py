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

    def test_11_docs_point_to_files_that_exist(self):
        text = (ROOT / "SKILL.md").read_text("utf-8")
        for ref in set(re.findall(r"references/[\w-]+\.md", text)):
            self.assertTrue((ROOT / ref).exists(), ref)
        docs = text + "".join(p.read_text("utf-8") for p in (ROOT / "references").glob("*.md"))
        for path in set(re.findall(r"<skill>/(scripts/[\w/.-]+\.\w+|[\w-]+\.md)", docs)):
            if path != "my-setup.md":
                self.assertTrue((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
