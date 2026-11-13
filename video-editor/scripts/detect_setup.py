"""Detect this computer's video hardware and tools, and test which encoders really work.

Usage:
  python detect_setup.py                 full report (takes under a minute: it test-encodes)
  python detect_setup.py --json          the same, as JSON
  python detect_setup.py --speech-python <path to the speech venv's python>
                                         also check whether Whisper can use an NVIDIA GPU
  python detect_setup.py power           only say whether a laptop is plugged in

Uses only the Python standard library, so it runs before anything else is installed.
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SYSTEM = platform.system()  # Windows, Darwin, Linux

# Settings for in-between renders: near-lossless and fast. The final export always uses libx264.
# Every candidate is test-encoded below; one that fails is never recommended.
CANDIDATES = {
    "nvidia": {
        "h264": ["-c:v", "h264_nvenc", "-preset", "p7", "-rc", "vbr", "-cq", "12", "-b:v", "0", "-pix_fmt", "yuv420p"],
        "hevc10": ["-c:v", "hevc_nvenc", "-preset", "p7", "-rc", "vbr", "-cq", "12", "-b:v", "0",
                   "-profile:v", "main10", "-pix_fmt", "p010le"],
    },
    "intel": {
        "h264": ["-c:v", "h264_qsv", "-preset", "slow", "-global_quality", "10", "-pix_fmt", "nv12"],
        "hevc10": ["-c:v", "hevc_qsv", "-preset", "slow", "-global_quality", "10", "-pix_fmt", "p010le"],
    },
    "amd": {
        "h264": ["-c:v", "h264_amf", "-quality", "quality", "-rc", "cqp", "-qp_i", "12", "-qp_p", "12",
                 "-pix_fmt", "nv12"],
        "hevc10": ["-c:v", "hevc_amf", "-quality", "quality", "-rc", "cqp", "-qp_i", "12", "-qp_p", "12",
                   "-profile:v", "main10", "-pix_fmt", "p010le"],
    },
    "apple": {
        "h264": ["-c:v", "h264_videotoolbox", "-q:v", "80", "-pix_fmt", "nv12"],
        "hevc10": ["-c:v", "hevc_videotoolbox", "-q:v", "80", "-profile:v", "main10", "-pix_fmt", "p010le"],
    },
    "cpu": {
        "h264": ["-c:v", "libx264", "-preset", "medium", "-crf", "10", "-pix_fmt", "yuv420p"],
        "hevc10": ["-c:v", "libx265", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p10le"],
    },
}
FINAL_EXPORT = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                "-ac", "2", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart"]


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def power():
    """'plugged in', 'on battery', or 'no battery' (desktop) / 'unknown'."""
    if SYSTEM == "Windows":
        code, out = run(["powershell", "-NoProfile", "-Command",
                         "(Get-CimInstance Win32_Battery).BatteryStatus"])
        out = out.strip()
        if code != 0:
            return "unknown"
        if not out:
            return "no battery"
        return "on battery" if out.splitlines()[0].strip() == "1" else "plugged in"
    if SYSTEM == "Darwin":
        code, out = run(["pmset", "-g", "batt"])
        if "InternalBattery" not in out:
            return "no battery"
        return "on battery" if "Battery Power" in out else "plugged in"
    base = "/sys/class/power_supply"
    if not os.path.isdir(base):
        return "unknown"
    supplies = os.listdir(base)
    if not any(s.startswith("BAT") for s in supplies):
        return "no battery"
    for s in supplies:
        try:
            if open(os.path.join(base, s, "type")).read().strip() == "Mains":
                return "plugged in" if open(os.path.join(base, s, "online")).read().strip() == "1" else "on battery"
        except OSError:
            pass
    return "unknown"


def gpus():
    if SYSTEM == "Windows":
        _, out = run(["powershell", "-NoProfile", "-Command",
                      "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }"])
        return [l.strip() for l in out.splitlines() if l.strip()]
    if SYSTEM == "Darwin":
        _, out = run(["system_profiler", "SPDisplaysDataType"])
        return [l.split(":", 1)[1].strip() for l in out.splitlines() if "Chipset Model" in l]
    if shutil.which("lspci"):
        _, out = run(["lspci"])
        return [l.split(": ", 1)[-1] for l in out.splitlines() if re.search(r"VGA|3D|Display", l)]
    return []


def cpu_name():
    if SYSTEM == "Windows":
        _, out = run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"])
        return out.strip().splitlines()[0] if out.strip() else platform.processor()
    if SYSTEM == "Darwin":
        _, out = run(["sysctl", "-n", "machdep.cpu.brand_string"])
        return out.strip() or platform.machine()
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def tool_version(name, args=("-version",)):
    path = shutil.which(name)
    if not path:
        return None
    _, out = run([path, *args], timeout=30)
    first = out.strip().splitlines()[0] if out.strip() else ""
    return {"path": path, "version": first}


def ffmpeg_major(version_line):
    m = re.search(r"version n?(\d+)\.", version_line or "")
    return int(m.group(1)) if m else None


def test_encoder(args, ten_bit, tmp):
    """Encode 4K test video. Returns (ok, fps, error). Speed leaves out the encoder's startup time."""
    vf = ["-vf", "format=yuv420p10le"] if ten_bit else []
    out = os.path.join(tmp, "test.mp4")

    def encode(frames):
        if os.path.exists(out):
            os.remove(out)
        start = time.time()
        code, text = run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=3840x2160:r=24:d=3",
                          *vf, *args, "-frames:v", str(frames), out], timeout=300)
        ok = code == 0 and os.path.exists(out) and os.path.getsize(out) > 0
        return ok, time.time() - start, code, text

    ok, short, code, text = encode(1)
    if ok:
        ok, long, code, text = encode(49)
    if not ok:
        lines = [l for l in text.strip().splitlines() if "Nothing was written" not in l]
        reason = next((l for l in lines if re.search(r"(?i)cannot|error|fail|not|unsupported|no device", l)),
                      lines[0] if lines else f"exit code {code}")
        return False, None, re.sub(r"\[[^\]]+ @ [0-9a-fx]+\] ", "", reason)[:160]
    return True, round(48 / max(long - short, 0.01), 1), None


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "power":
        print(power())
        return
    as_json = "--json" in sys.argv
    speech_python = None
    if "--speech-python" in sys.argv:
        speech_python = sys.argv[sys.argv.index("--speech-python") + 1]

    report = {
        "os": f"{SYSTEM} {platform.release()} ({platform.machine()})",
        "cpu": cpu_name(),
        "cpu_threads": os.cpu_count(),
        "gpus": gpus(),
        "power": power(),
        "tools": {n: tool_version(n) for n in ("ffmpeg", "ffprobe")},
        "encoders": {},
    }
    report["tools"]["yt-dlp"] = tool_version("yt-dlp", ("--version",))
    report["tools"]["node"] = tool_version("node", ("--version",))
    report["tools"]["nvidia-smi"] = tool_version("nvidia-smi", ("-L",))

    ff = report["tools"]["ffmpeg"]
    if ff:
        major = ffmpeg_major(ff["version"])
        report["ffmpeg_major"] = major
        report["ffmpeg_reads_filter_files_with_dash_slash"] = (major is None or major >= 7)
        _, listing = run(["ffmpeg", "-hide_banner", "-encoders"])
        with tempfile.TemporaryDirectory() as tmp:
            for vendor, kinds in CANDIDATES.items():
                for kind, args in kinds.items():
                    name = args[args.index("-c:v") + 1]
                    entry = {"encoder": name, "args": " ".join(args)}
                    if not re.search(rf"\s{re.escape(name)}\s", listing):
                        entry.update(ok=False, error="not in this FFmpeg build")
                    else:
                        ok, fps, err = test_encoder(args, kind == "hevc10", tmp)
                        entry.update(ok=ok, fps_4k=fps, error=err)
                    report["encoders"][f"{vendor}/{kind}"] = entry

        def best(kind):
            working = [(v, e) for k, e in report["encoders"].items()
                       for v in [k.split("/")[0]] if k.endswith("/" + kind) and e["ok"]]
            hw = [(v, e) for v, e in working if v != "cpu"]
            pool = hw or working
            return max(pool, key=lambda ve: ve[1]["fps_4k"] or 0) if pool else (None, None)

        for kind in ("h264", "hevc10"):
            vendor, e = best(kind)
            report[f"recommended_{kind}"] = {"vendor": vendor, "args": e["args"] if e else None,
                                             "fps_4k": e["fps_4k"] if e else None}
    report["final_export_args"] = " ".join(FINAL_EXPORT)

    if speech_python:
        code, out = run([speech_python, "-I", "-c",
                         "import ctranslate2; print(ctranslate2.get_cuda_device_count())"])
        report["whisper_cuda_devices"] = int(out.strip()) if code == 0 and out.strip().isdigit() else 0

    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    print(f"System:     {report['os']}")
    print(f"CPU:        {report['cpu']} ({report['cpu_threads']} threads)")
    print(f"GPU:        {', '.join(report['gpus']) or 'none found'}")
    print(f"Power:      {report['power']}")
    for n, t in report["tools"].items():
        print(f"{n + ':':12}{t['version'] if t else 'NOT FOUND'}")
    if ff and report.get("ffmpeg_major") and report["ffmpeg_major"] < 7:
        print("NOTE: FFmpeg is older than 7. Use -filter_complex_script <file> instead of -/filter_complex <file>.")
    if report["encoders"]:
        print("\nEncoder tests (4K, speed without startup time):")
        for k, e in report["encoders"].items():
            status = f"works, {e['fps_4k']} fps" if e["ok"] else f"no ({e['error']})"
            print(f"  {k:14} {e['encoder']:18} {status}")
        for kind, label in (("h264", "8-bit in-between renders"), ("hevc10", "10-bit in-between renders")):
            r = report[f"recommended_{kind}"]
            print(f"\nRecommended for {label}: {r['vendor']}\n  {r['args']}")
    print(f"\nFinal export (always): {report['final_export_args']}")
    if "whisper_cuda_devices" in report:
        n = report["whisper_cuda_devices"]
        print(f"\nWhisper on GPU: {'yes, ' + str(n) + ' NVIDIA device(s)' if n else 'no, runs on the CPU'}")
    if report["power"] == "on battery":
        print("\nNOTE: running on battery. Speeds above may be lower than when plugged in.")


if __name__ == "__main__":
    main()
