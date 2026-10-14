#!/usr/bin/env python3
"""fleet_daily.py - the daily pulse of a machine that joined the Palo Alto AI Lab fleet.

What it does, every morning:
  1. git pull two public repositories (second-brain-starter-kit, claw-consensus)
     into FLEET_HOME (default ~/lab/fleet/).
  2. apply the update: copy fleet-managed skills into ~/.claude/skills/ and
     mirror kit/law/ into FLEET_HOME/law/.
  3. print a receipt (what changed) and append it as one JSON line to
     FLEET_HOME/journal.jsonl. The journal is the proof, not the exit code.

Three guarantees you can repeat to the human who runs it:
  * writes only inside the home directory (FLEET_HOME and ~/.claude/skills/)
  * never overwrites a skill the human wrote: only directories that carry the
    marker file `.fleet-managed` (written by this script on first copy) are
    ever replaced; everything else is reported as `kept-yours`
  * talks to nothing but github.com, and only through `git`

Usage:
  python fleet_daily.py                 # same as `pull`
  python fleet_daily.py init            # create FLEET_HOME, clone, then pull
  python fleet_daily.py pull [--dry-run]
  python fleet_daily.py status          # last 7 runs; STALE + exit 1 if > 36 h
  python fleet_daily.py install-schedule   # prints the scheduler command, never runs it
  python fleet_daily.py uninstall       # removes only what this script installed

Environment:
  FLEET_HOME    where the clones and the journal live (default ~/lab/fleet)
  SKILLS_HOME   where skills are installed (default ~/.claude/skills)

Exit codes: 0 ok, 1 git failure or STALE, 2 git not installed.
Standard library only. Python 3.9+. Windows, macOS, Linux.
Home: https://github.com/tonydzi/join-the-fleet  (MIT)
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPOS = {
    "kit": "https://github.com/tonydzi/second-brain-starter-kit.git",
    "consensus": "https://github.com/tonydzi/claw-consensus.git",
}
MARKER = ".fleet-managed"
STALE_HOURS = 36
GIT_TIMEOUT = 120


def fleet_home() -> Path:
    return Path(os.environ.get("FLEET_HOME") or Path.home() / "lab" / "fleet")


def skills_home() -> Path:
    return Path(os.environ.get("SKILLS_HOME") or Path.home() / ".claude" / "skills")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --- git -------------------------------------------------------------------

def run_git(args, cwd=None):
    """Run one git command. Returns (rc, stdout). rc 127 when git is missing."""
    try:
        p = subprocess.run(["git"] + list(args), cwd=str(cwd) if cwd else None,
                           capture_output=True, text=True, timeout=GIT_TIMEOUT)
    except FileNotFoundError:
        return 127, "git not found"
    except subprocess.TimeoutExpired:
        return 124, "git timeout after %ss" % GIT_TIMEOUT
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def head_of(repo_dir: Path) -> str:
    rc, out = run_git(["rev-parse", "HEAD"], cwd=repo_dir)
    return out.split()[0] if rc == 0 and out else ""


def pull_repo(name: str, url: str, home: Path, dry_run: bool) -> dict:
    """Clone if missing, otherwise fetch+ff. Returns a delta record."""
    repo_dir = home / name
    rec = {"repo": name, "before": "", "after": "", "delta": 0, "log": [], "error": ""}
    if not (repo_dir / ".git").exists():
        if dry_run:
            rec["error"] = "missing (dry-run, not cloned)"
            return rec
        rc, out = run_git(["clone", "--depth", "1", url, str(repo_dir)])
        if rc != 0:
            rec["error"] = "clone failed rc=%s: %s" % (rc, out[-300:])
            return rec
        rec["after"] = head_of(repo_dir)
        rec["log"] = ["(fresh clone)"]
        rec["delta"] = 1
        return rec
    rec["before"] = head_of(repo_dir)
    if dry_run:
        rc, out = run_git(["fetch", "--quiet"], cwd=repo_dir)
        if rc != 0:
            rec["error"] = "fetch failed rc=%s: %s" % (rc, out[-300:])
            return rec
        rc, out = run_git(["log", "--oneline", "HEAD..@{u}"], cwd=repo_dir)
        rec["after"] = rec["before"]
    else:
        rc, out = run_git(["pull", "--ff-only", "--quiet"], cwd=repo_dir)
        if rc != 0:
            rec["error"] = "pull failed rc=%s: %s" % (rc, out[-300:])
            return rec
        rec["after"] = head_of(repo_dir)
        if rec["after"] and rec["after"] != rec["before"]:
            rc, out = run_git(["log", "--oneline", rec["before"] + ".." + rec["after"]], cwd=repo_dir)
        else:
            out = ""
    lines = [ln for ln in out.splitlines() if ln.strip()] if rc == 0 else []
    rec["log"] = lines
    rec["delta"] = len(lines)
    return rec


# --- apply -----------------------------------------------------------------

def apply_skills(kit_dir: Path, dest: Path, dry_run: bool) -> dict:
    """Copy kit/skills/<name>/ (with SKILL.md) into dest. Never touch unmarked dirs."""
    res = {"added": [], "updated": [], "kept_yours": [], "unchanged": 0}
    src_root = kit_dir / "skills"
    if not src_root.is_dir():
        return res
    for src in sorted(p for p in src_root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()):
        tgt = dest / src.name
        if tgt.exists() and not (tgt / MARKER).exists():
            res["kept_yours"].append(src.name)
            continue
        if tgt.exists():
            if _same_tree(src, tgt):
                res["unchanged"] += 1
                continue
            if not dry_run:
                shutil.rmtree(tgt)
                shutil.copytree(src, tgt)
                (tgt / MARKER).write_text("installed by fleet_daily.py\n", encoding="utf-8")
            res["updated"].append(src.name)
        else:
            if not dry_run:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, tgt)
                (tgt / MARKER).write_text("installed by fleet_daily.py\n", encoding="utf-8")
            res["added"].append(src.name)
    return res


def _same_tree(a: Path, b: Path) -> bool:
    fa = {p.relative_to(a).as_posix(): p.read_bytes() for p in a.rglob("*") if p.is_file()}
    fb = {p.relative_to(b).as_posix(): p.read_bytes() for p in b.rglob("*")
          if p.is_file() and p.name != MARKER}
    return fa == fb


def mirror_law(kit_dir: Path, home: Path, dry_run: bool) -> int:
    src = kit_dir / "law"
    if not src.is_dir():
        return 0
    dst = home / "law"
    if dry_run:
        return len([p for p in src.rglob("*") if p.is_file()])
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return len([p for p in dst.rglob("*") if p.is_file()])


# --- journal ---------------------------------------------------------------

def journal_path(home: Path) -> Path:
    return home / "journal.jsonl"


def append_journal(home: Path, entry: dict) -> None:
    home.mkdir(parents=True, exist_ok=True)
    with journal_path(home).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")


def read_journal(home: Path) -> list:
    p = journal_path(home)
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


# --- commands --------------------------------------------------------------

def cmd_pull(dry_run: bool = False) -> int:
    home = fleet_home()
    rc_git, _ = run_git(["--version"])
    if rc_git == 127:
        print("FLEET PULSE FAIL git is not installed")
        return 2
    home.mkdir(parents=True, exist_ok=True)
    entry = {"ts": now_iso(), "dry_run": dry_run, "repos": [], "skills": {}, "law_files": 0,
             "result": "OK", "reason": ""}
    print("fleet pulse %s%s" % (entry["ts"], " (dry-run)" if dry_run else ""))
    print("home: %s" % home)
    for name, url in REPOS.items():
        rec = pull_repo(name, url, home, dry_run)
        entry["repos"].append(rec)
        if rec["error"]:
            print("  %-10s ERROR %s" % (name, rec["error"]))
            entry["result"] = "FAIL"
            entry["reason"] = "%s: %s" % (name, rec["error"])
            continue
        print("  %-10s %s -> %s  (%d new commit%s)" % (
            name, rec["before"][:7] or "-", rec["after"][:7] or "-", rec["delta"],
            "" if rec["delta"] == 1 else "s"))
        for ln in rec["log"][:10]:
            print("             " + ln)
        if len(rec["log"]) > 10:
            print("             ... and %d more" % (len(rec["log"]) - 10))
    kit_dir = home / "kit"
    if kit_dir.is_dir():
        sk = apply_skills(kit_dir, skills_home(), dry_run)
        entry["skills"] = sk
        entry["law_files"] = mirror_law(kit_dir, home, dry_run)
        print("skills -> %s: added %d, updated %d, kept-yours %d, unchanged %d" % (
            skills_home(), len(sk["added"]), len(sk["updated"]), len(sk["kept_yours"]),
            sk["unchanged"]))
        for k in ("added", "updated"):
            for n in sk[k][:10]:
                print("  %s %s" % ("+" if k == "added" else "~", n))
        if sk["kept_yours"]:
            print("  kept-yours (your own, untouched): %s" % ", ".join(sk["kept_yours"][:10]))
        print("law mirrored: %d files -> %s" % (entry["law_files"], home / "law"))
    if not dry_run:
        append_journal(home, entry)
    if entry["result"] == "OK":
        print("FLEET PULSE OK %s" % entry["ts"][:10])
        return 0
    print("FLEET PULSE FAIL %s" % entry["reason"])
    return 1


def cmd_init() -> int:
    home = fleet_home()
    home.mkdir(parents=True, exist_ok=True)
    print("init: %s" % home)
    return cmd_pull(dry_run=False)


def cmd_status() -> int:
    home = fleet_home()
    entries = read_journal(home)
    if not entries:
        print("no runs recorded in %s" % journal_path(home))
        print("STALE never ran")
        return 1
    print("%-20s %6s %6s %7s  %s" % ("date (UTC)", "kit", "cons.", "skills", "result"))
    for e in entries[-7:]:
        deltas = {r.get("repo"): r.get("delta", 0) for r in e.get("repos", [])}
        sk = e.get("skills") or {}
        changed = len(sk.get("added", [])) + len(sk.get("updated", []))
        print("%-20s %6s %6s %7s  %s%s" % (
            e.get("ts", "")[:19], deltas.get("kit", "-"), deltas.get("consensus", "-"),
            changed, e.get("result", "?"), " (dry)" if e.get("dry_run") else ""))
    last = entries[-1]
    try:
        ts = datetime.fromisoformat(last["ts"])
    except (KeyError, ValueError):
        print("STALE last entry has no readable timestamp")
        return 1
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
    print("newest entry: %.1f h ago" % age_h)
    if age_h > STALE_HOURS:
        print("STALE (older than %d h)" % STALE_HOURS)
        return 1
    return 0


def schedule_text(sysname: str, script: Path, python: str) -> str:
    cmd = '%s "%s" pull' % (python, script)
    lines = ["Schedule the daily pull at 07:00 local time. This script only prints; you run it.", ""]
    if sysname == "win32":
        lines += ["Windows (PowerShell or cmd):",
                  '  schtasks /create /tn "FleetDaily" /sc daily /st 07:00 /tr \'%s\' /f' % cmd]
    elif sysname == "darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / "ai.palo-alto.fleet-daily.plist"
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>\n'
            '  <key>Label</key><string>ai.palo-alto.fleet-daily</string>\n'
            '  <key>ProgramArguments</key><array>\n'
            '    <string>%s</string><string>%s</string><string>pull</string>\n'
            '  </array>\n'
            '  <key>StartCalendarInterval</key><dict>'
            '<key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>\n'
            '  <key>StandardOutPath</key><string>%s</string>\n'
            '  <key>StandardErrorPath</key><string>%s</string>\n'
            '</dict></plist>\n' % (python, script, fleet_home() / "launchd.log", fleet_home() / "launchd.err"))
        try:
            plist.parent.mkdir(parents=True, exist_ok=True)
            plist.write_text(body, encoding="utf-8")
            lines += ["macOS: plist written to %s" % plist]
        except OSError as exc:
            lines += ["macOS: could not write %s (%s); create it by hand with this content:" % (plist, exc), body]
        lines += ["  launchctl load %s" % plist]
    else:
        lines += ["Linux (crontab -e):", "  0 7 * * * %s >> %s 2>&1" % (cmd, fleet_home() / "cron.log")]
    lines += ["", "or ask Claude Code: schedule `python %s pull` every day at 07:00" % script]
    return "\n".join(lines)


def cmd_install_schedule() -> int:
    script = Path(__file__).resolve()
    print(schedule_text(sys.platform, script, sys.executable or "python"))
    return 0


def _force_rmtree(path: Path) -> None:
    """rmtree that also removes read-only files (git pack objects on Windows)."""
    import stat

    def _retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_retry)
    else:
        shutil.rmtree(path, onerror=_retry)


def cmd_uninstall() -> int:
    """Remove only what this script installed: marked skills, law mirror, FLEET_HOME, plist."""
    home = fleet_home()
    removed = []
    dest = skills_home()
    if dest.is_dir():
        for d in sorted(p for p in dest.iterdir() if p.is_dir()):
            if (d / MARKER).exists():
                _force_rmtree(d)
                removed.append(d.name)
    print("skills removed (had marker): %d" % len(removed))
    kept = [p.name for p in dest.iterdir() if p.is_dir()] if dest.is_dir() else []
    print("skills kept (yours, no marker): %d" % len(kept))
    plist = Path.home() / "Library" / "LaunchAgents" / "ai.palo-alto.fleet-daily.plist"
    if plist.exists():
        try:
            plist.unlink()
            print("removed %s (run: launchctl unload %s)" % (plist, plist))
        except OSError as exc:
            print("could not remove %s: %s" % (plist, exc))
    if home.exists():
        _force_rmtree(home)
        print("removed %s" % home)
    if sys.platform == "win32":
        print("now remove the task: schtasks /delete /tn \"FleetDaily\" /f")
    elif sys.platform != "darwin":
        print("now remove the crontab line that runs fleet_daily.py (crontab -e)")
    print("then delete this file: %s" % Path(__file__).resolve())
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="daily pulse of a fleet machine")
    ap.add_argument("cmd", nargs="?", default="pull",
                    choices=["init", "pull", "status", "install-schedule", "uninstall"])
    ap.add_argument("--dry-run", action="store_true", help="fetch and show, copy nothing")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        return cmd_init()
    if a.cmd == "pull":
        return cmd_pull(dry_run=a.dry_run)
    if a.cmd == "status":
        return cmd_status()
    if a.cmd == "uninstall":
        return cmd_uninstall()
    return cmd_install_schedule()


if __name__ == "__main__":
    sys.exit(main())
