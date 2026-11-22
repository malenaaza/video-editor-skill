"""Detect this computer's video hardware and tools, and test which encoders really work.

Usage:
  python detect_setup.py                 full report (takes under a minute: it test-encodes)
  python detect_setup.py --json          the same, as JSON
  python detect_setup.py --speech-python <path to the speech venv's python>
                                         also check whether Whisper can use an NVIDIA GPU
  python detect_setup.py power           only say whether a laptop is plugged in, and which
                                         power mode it uses on battery
  python detect_setup.py folder [path] [--json]
                                         check a work folder: suggests ~/video-work when no path is given, says whether
                                         it exists, the free space, and whether it is inside OneDrive, iCloud,
                                         Dropbox or Google Drive (big videos time out there). Creates nothing.

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
# Rec.709 tags, or players guess and faces look darker and redder. FFmpeg 7+ ignores these options and takes the
# tags from the frames: end the filter chain with setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709.
FINAL_EXPORT = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                "-ac", "2", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart"]


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


SYNCED_NAMES = (("onedrive", "OneDrive"), ("dropbox", "Dropbox"), ("icloud", "iCloud"),
                ("mobile documents", "iCloud"), ("google drive", "Google Drive"), ("googledrive", "Google Drive"),
                ("my drive", "Google Drive"), ("cloudstorage", "a cloud-synced folder"))


def synced_service(path):
    """Which sync service the path is inside (OneDrive, Dropbox, iCloud, Google Drive), or None.
    Follows links and junctions, and also checks the folders Windows names in OneDrive* variables."""
    real = os.path.normcase(os.path.realpath(os.path.expanduser(path)))
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root = os.environ.get(var)
        if root:
            root = os.path.normcase(os.path.realpath(root))
            if real == root or real.startswith(root + os.sep):
                return "OneDrive"
    for part in real.lower().replace("\\", "/").split("/"):
        for key, name in SYNCED_NAMES:
            if key in part:
                return name
    return None


def folder_report(path=None):
    suggested = path is None
    path = path or os.path.join(os.path.expanduser("~"), "video-work")
    full = os.path.abspath(os.path.expanduser(path))
    probe = full
    while not os.path.exists(probe) and os.path.dirname(probe) != probe:
        probe = os.path.dirname(probe)
    free = round(shutil.disk_usage(probe).free / 1e9, 1)
    service = synced_service(full)
    return {"path": full, "suggested": suggested, "exists": os.path.isdir(full), "free_gb": free,
            "synced_service": service, "ok": service is None}


def print_folder_report(report):
    print(("Suggested work folder: " if report["suggested"] else "Folder: ") + report["path"])
    print("Exists: " + ("yes" if report["exists"] else "no (create it when the user agrees)"))
    print(f"Free space: {report['free_gb']} GB")
    if report["ok"]:
        print("OK: not inside a synced folder.")
    else:
        print(f"NOT OK: inside {report['synced_service']}. Big videos time out there; pick another folder, "
              f"for example {os.path.join(os.path.expanduser('~'), 'video-work')}.")


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


# Windows power-mode overlays (Settings > System > Power > Power mode), set separately
# for plugged in (AC) and on battery (DC).
WINDOWS_OVERLAYS = {
    "961cc777-2547-4f9d-8174-7d86181b8a7a": ("Best power efficiency", True),
    "00000000-0000-0000-0000-000000000000": ("Balanced", False),
    "3af9b8d9-7c97-431d-ad78-34a8bfea439f": ("Better performance", False),
    "ded574b5-45a0-4f42-8737-46345c09c238": ("Best performance", False),
}
# Classic power plans, used when no overlay is saved.
WINDOWS_PLANS = {
    "a1841308-3541-4fab-bc81-f71556f20b4a": ("Power saver plan", True),
    "381b4222-f694-41f0-9685-ff5bb260df2e": ("Balanced plan", False),
    "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": ("High performance plan", False),
    "e9a42b02-d5df-448d-aa00-03f14749eb61": ("Ultimate performance plan", False),
}


def battery_power_mode():
    """The power mode used on battery: (name, saves_power), with saves_power True, False or None (unknown).

    Being on battery is not slow by itself: the power mode chosen for battery is what throttles.
    """
    if SYSTEM == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes")
            values = {}
            for name in ("ActiveOverlayDcPowerScheme", "ActivePowerScheme"):
                try:
                    values[name] = str(winreg.QueryValueEx(key, name)[0]).lower()
                except OSError:
                    pass
        except (ImportError, OSError):
            return ("unknown", None)
        dc = values.get("ActiveOverlayDcPowerScheme")
        if dc in WINDOWS_OVERLAYS:
            return WINDOWS_OVERLAYS[dc]
        plan = values.get("ActivePowerScheme")
        if plan in WINDOWS_PLANS:
            return WINDOWS_PLANS[plan]
        return ("unknown", None)
    if SYSTEM == "Darwin":
        _, out = run(["pmset", "-g", "custom"])
        section = out.split("Battery Power:", 1)[1].split("AC Power:", 1)[0] if "Battery Power:" in out else ""
        m = re.search(r"(?:lowpowermode|powermode)\s+(\d)", section)
        if not m:
            return ("unknown", None)
        return ("Low Power Mode", True) if m.group(1) == "1" else ("normal", False)
    return ("unknown", None)


def power_report():
    """One line for the `power` command: whether it's plugged in, and whether battery will slow jobs down."""
    state = power()
    if state in ("no battery", "unknown"):
        return state
    mode, saves = battery_power_mode()
    if state == "plugged in":
        return f"plugged in (on battery this laptop uses: {mode})"
    if saves:
        return f"on battery, power mode {mode}: long jobs will be slower"
    if saves is False:
        return f"on battery, power mode {mode}: close to full speed, but the battery drains fast"
    return "on battery, power mode unknown: long jobs may be slower"


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
        print(power_report())
        return
    if len(sys.argv) > 1 and sys.argv[1] == "folder":
        rest = [x for x in sys.argv[2:] if x != "--json"]
        report = folder_report(rest[0] if rest else None)
        if "--json" in sys.argv:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print_folder_report(report)
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
        "battery_power_mode": battery_power_mode()[0],
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
    if report["power"] not in ("no battery", "unknown"):
        print(f"On battery: power mode {report['battery_power_mode']}")
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
