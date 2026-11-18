"""Turns a problem or a wish into a report the user can send to the skill's author, in one click.

  python -I report.py --kind bug  --title "Skin not softened on a close-up" --details details.md
  python -I report.py --kind idea --title "Music under the voice" --details details.md

`details.md` is written by Claude, in the user's language: what they saw or want, in their own words,
the step of the build order, and the settings in force. This script then:
 - adds the skill version, the system, Python and FFmpeg versions;
 - removes personal details: the home folder path becomes ~, and the user name is replaced;
 - saves the report to ~/.video-editor/reports/<date>-<kind>.md;
 - prints a link that opens a new issue on the skill's GitHub page with everything filled in (the user
   only clicks Submit; they need a free GitHub account), and, if support.json has an email address, a
   link that opens an email with the same text.
Nothing is sent by this script: the user decides. Frames, audio and videos are never included; if the
user wants to share one, they attach it themselves, after looking at it.
"""
import argparse
import getpass
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
MAX_URL_BODY = 6000  # GitHub refuses very long links; longer reports are cut, and the full one is saved

sys.stdout.reconfigure(encoding="utf-8")


def anonymise(text, home=None, user=None):
    home = home or os.path.expanduser("~")
    user = user if user is not None else getpass.getuser()
    for variant in {home, home.replace("\\", "/"), home.replace("/", "\\")}:
        if variant and len(variant) > 3:
            text = re.sub(re.escape(variant), "~", text, flags=re.IGNORECASE)
    if user and len(user) >= 3:
        text = re.sub(r"(?<![\w])" + re.escape(user) + r"(?![\w])", "<user>", text, flags=re.IGNORECASE)
    return text


def environment():
    version = (SKILL / "VERSION").read_text(encoding="utf-8").strip() if (SKILL / "VERSION").exists() else "unknown"
    try:
        ffmpeg = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=20).stdout.splitlines()[0]
    except (OSError, IndexError, subprocess.SubprocessError):
        ffmpeg = "not found"
    return (f"- Skill version: {version}\n- System: {platform.system()} {platform.release()} ({platform.machine()})\n"
            f"- Python: {platform.python_version()}\n- FFmpeg: {ffmpeg}")


def build(kind, title, details, support, home=None, user=None):
    label = "Bug" if kind == "bug" else "Idea"
    body = f"{details.strip()}\n\n**Environment**\n{environment()}\n\n_Sent from the video-editor skill._"
    body = anonymise(body, home, user)
    title = anonymise(f"[{label}] {title.strip()}", home, user)
    links = {}
    repo = support.get("github_repo")
    if repo:
        short = body if len(body) <= MAX_URL_BODY else body[:MAX_URL_BODY] + "\n\n…(cut: the full report is in the user's file)"
        template = "bug.md" if kind == "bug" else "improvement.md"
        query = urllib.parse.urlencode({"template": template, "title": title, "body": short})
        links["github"] = f"https://github.com/{repo}/issues/new?{query}"
    if support.get("email"):
        subject = urllib.parse.quote(f"video-editor skill: {title}")
        links["email"] = f"mailto:{support['email']}?subject={subject}&body={urllib.parse.quote(body)}"
    return title, body, links


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", choices=["bug", "idea"], required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--details", required=True, help="a text file with the report, written in the user's language")
    ap.add_argument("--support", default=str(SKILL / "support.json"))
    ap.add_argument("--reports-dir", default=os.path.join(os.path.expanduser("~"), ".video-editor", "reports"))
    a = ap.parse_args()
    support = json.load(open(a.support, encoding="utf-8")) if os.path.exists(a.support) else {}
    details = Path(a.details).read_text(encoding="utf-8")
    title, body, links = build(a.kind, a.title, details, support)
    folder = Path(a.reports_dir)
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / f"{time.strftime('%Y%m%d-%H%M%S')}-{a.kind}.md"
    saved.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    print(f"Report saved to {saved} (names and personal paths removed). Show it to the user before they send it.")
    if "github" in links:
        print("\nTo send it on GitHub (opens the report filled in; the user clicks Submit; needs a free GitHub account):")
        print(links["github"])
    if "email" in links:
        print(f"\nOr by email to {support['email']} (opens an email with the report):")
        print(links["email"])
    if not links:
        print("\nNo GitHub page or email address is set in support.json: the user can send the saved file to the author.")


if __name__ == "__main__":
    main()
