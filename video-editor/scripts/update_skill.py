"""Updates the video-editor skill to the latest version, safely. For people who don't use Git.

  python -I update_skill.py --check     only say whether a newer version exists
  python -I update_skill.py             back up the installed skill, then replace it with the latest version

What it does, in this order:
 1. Looks at the installed skill and the latest one (the `VERSION` file in each).
 2. If the installed skill is linked to a repository (a Git clone, which developers use), it stops:
    updating that is done with `git pull`, and replacing it here could overwrite work.
 3. Copies the whole installed skill to ~/.video-editor/backups/ first. Nothing is ever lost.
 4. Moves a `my-setup.md` that an older version kept inside the skill folder to ~/.video-editor/
    (only if there isn't one there already), so the user's settings are never inside a folder that gets replaced.
 5. Replaces the skill with the latest version. If anything fails halfway, the old one is put back.
 6. Prints a report: the versions, which files had been changed by hand (it can tell once the skill was
    installed by this script; before that it can't), where the backup is, and the top of the changelog.

Only the standard library and an internet connection are needed. `--source` takes a ZIP file, a folder or a
web address instead of GitHub (used by the tests). `--skill-dir`, `--backup-dir` and `--settings-dir`
point at other folders. `--force` updates even when the versions match (to repair a modified copy).
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

REPO_ZIP = "https://github.com/malenaaza/video-editor-skill/archive/refs/heads/main.zip"
REPO_VERSION = "https://raw.githubusercontent.com/malenaaza/video-editor-skill/main/video-editor/VERSION"
MANIFEST = ".installed-manifest.json"
SKIP_NAMES = {"__pycache__", MANIFEST, "my-setup.md"}

sys.stdout.reconfigure(encoding="utf-8")


def read_version(folder):
    try:
        return (Path(folder) / "VERSION").read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def version_key(text):
    try:
        return tuple(int(p) for p in text.split("."))
    except (AttributeError, ValueError):
        return None


def is_newer(latest, installed):
    a, b = version_key(latest), version_key(installed)
    if a is None or b is None:
        return latest != installed
    return a > b


def hash_tree(folder):
    out = {}
    folder = Path(folder)
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if path.is_dir() or any(part in SKIP_NAMES for part in rel.parts) or path.suffix == ".pyc":
            continue
        out[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def linked_to_repository(skill_dir):
    """True if the folder is a link, or lives inside a Git clone (developers' setups)."""
    absolute = os.path.abspath(skill_dir)
    real = os.path.realpath(skill_dir)
    if os.path.islink(absolute) or os.path.normcase(real) != os.path.normcase(absolute):
        return True
    return (Path(real).parent / ".git").exists() or (Path(real) / ".git").exists()


def download(source, target):
    if os.path.exists(source):
        shutil.copy(source, target)
        return
    request = urllib.request.Request(source, headers={"User-Agent": "video-editor-skill-updater"})
    with urllib.request.urlopen(request, timeout=60) as response, open(target, "wb") as handle:
        shutil.copyfileobj(response, handle)


def fetch_latest(source, work):
    """Returns (folder with the new skill, folder that holds CHANGELOG.md or None)."""
    if os.path.isdir(source):
        folder = Path(source)
        return (folder if (folder / "SKILL.md").exists() else folder / "video-editor"), folder
    archive = Path(work) / "latest.zip"
    download(source, archive)
    extracted = Path(work) / "latest"
    with zipfile.ZipFile(archive) as z:
        z.extractall(extracted)
    for skill_md in extracted.rglob("SKILL.md"):
        if skill_md.parent.name == "video-editor":
            return skill_md.parent, skill_md.parent.parent
    sys.exit("The download doesn't contain the video-editor skill.")


def latest_version_only():
    request = urllib.request.Request(REPO_VERSION, headers={"User-Agent": "video-editor-skill-updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8").strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only report whether an update exists")
    ap.add_argument("--force", action="store_true", help="update even if the version is the same")
    ap.add_argument("--source", help="ZIP file, folder or web address of the latest version (default: GitHub)")
    ap.add_argument("--skill-dir", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--backup-dir", default=os.path.join(os.path.expanduser("~"), ".video-editor", "backups"))
    ap.add_argument("--settings-dir", default=os.path.join(os.path.expanduser("~"), ".video-editor"))
    a = ap.parse_args()
    skill_dir = Path(a.skill_dir)
    installed = read_version(skill_dir)

    try:
        if a.check:
            latest = read_version(fetch_latest(a.source, tempfile.mkdtemp())[0]) if a.source else latest_version_only()
            print(f"Installed version: {installed or 'unknown (an older version)'}. Latest: {latest}.")
            print("An update is available." if installed is None or is_newer(latest, installed) else "You are up to date.")
            return
    except OSError as error:
        sys.exit(f"Couldn't reach the latest version ({error}). Check the internet connection and try again.")

    if linked_to_repository(skill_dir):
        sys.exit("This skill is linked to a repository (a Git clone), so it is updated with `git pull` in that folder, "
                 "not with this script. Nothing was changed.")

    work = tempfile.mkdtemp(prefix="video-editor-update-")
    try:
        try:
            new_dir, release_root = fetch_latest(a.source or REPO_ZIP, work)
        except OSError as error:
            sys.exit(f"Couldn't download the latest version ({error}). Check the internet connection and try again. "
                     "Nothing was changed.")
        latest = read_version(new_dir)
        if not a.force and installed is not None and latest is not None and not is_newer(latest, installed):
            print(f"You are up to date (version {installed}). Nothing was changed.")
            return

        # what the user changed by hand: only known if this script installed the current version
        changed = None
        manifest_path = skill_dir / MANIFEST
        if manifest_path.exists():
            recorded = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
            now = hash_tree(skill_dir)
            changed = sorted([f for f in now if recorded.get(f) != now[f]] + [f for f in recorded if f not in now])

        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = Path(a.backup_dir) / f"video-editor-{installed or 'unknown'}-{stamp}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, backup, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        moved_settings = False
        legacy = skill_dir / "my-setup.md"
        settings_dir = Path(a.settings_dir)
        if legacy.exists() and not (settings_dir / "my-setup.md").exists():
            settings_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(legacy, settings_dir / "my-setup.md")
            moved_settings = True

        staging = skill_dir.parent / (skill_dir.name + ".new")
        old = skill_dir.parent / (skill_dir.name + ".old")
        for leftover in (staging, old):
            if leftover.exists():
                shutil.rmtree(leftover)
        shutil.copytree(new_dir, staging, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "my-setup.md"))
        (staging / MANIFEST).write_text(json.dumps({"version": latest, "files": hash_tree(staging)}, indent=1), encoding="utf-8")
        os.rename(skill_dir, old)
        try:
            os.rename(staging, skill_dir)
        except OSError:
            os.rename(old, skill_dir)  # put the old one back
            raise
        shutil.rmtree(old, ignore_errors=True)

        print(f"Updated the video-editor skill: {installed or 'an older version'} -> {latest}.")
        print(f"Backup of the old version: {backup}")
        if moved_settings:
            print(f"Your settings (my-setup.md) were moved to {settings_dir}, outside the skill folder.")
        if changed is None:
            print("Files changed by hand: can't tell for this install (it wasn't installed by this updater). "
                  "If you changed any skill file yourself, it is in the backup.")
        elif changed:
            print("Files you had changed by hand (the new version replaced them; your versions are in the backup):")
            for f in changed:
                print("  " + f)
        else:
            print("No files had been changed by hand.")
        changelog = Path(release_root) / "CHANGELOG.md"
        if changelog.exists():
            print("\nWhat's new (top of the changelog):\n")
            print("\n".join(changelog.read_text(encoding="utf-8").splitlines()[:60]))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
