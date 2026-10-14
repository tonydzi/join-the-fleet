"""Tests for fleet_daily.py. stdlib unittest, no network: git is monkeypatched."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fleet_daily as fd  # noqa: E402


def fake_git_factory(heads):
    """Simulate git: rev-parse returns heads[cwd], pull/fetch/clone succeed."""
    def fake(args, cwd=None):
        if args[0] == "--version":
            return 0, "git version 0.fake"
        if args[0] == "rev-parse":
            return 0, heads.get(str(cwd), "aaaaaaa")
        if args[0] in ("pull", "fetch"):
            return 0, ""
        if args[0] == "log":
            return 0, ""
        if args[0] == "clone":
            Path(args[-1]).mkdir(parents=True, exist_ok=True)
            (Path(args[-1]) / ".git").mkdir()
            return 0, ""
        return 0, ""
    return fake


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home = root / "fleet"
        self.skills = root / "skills"
        os.environ["FLEET_HOME"] = str(self.home)
        os.environ["SKILLS_HOME"] = str(self.skills)
        # fake kit repo with two skills and a law dir
        for name in ("kit", "consensus"):
            (self.home / name / ".git").mkdir(parents=True)
        for s in ("tt", "retro"):
            d = self.home / "kit" / "skills" / s
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("# %s\n" % s, encoding="utf-8")
        (self.home / "kit" / "law").mkdir()
        (self.home / "kit" / "law" / "CORE.md").write_text("law\n", encoding="utf-8")
        self._orig_git = fd.run_git
        fd.run_git = fake_git_factory({})

    def tearDown(self):
        fd.run_git = self._orig_git
        os.environ.pop("FLEET_HOME", None)
        os.environ.pop("SKILLS_HOME", None)
        self.tmp.cleanup()

    def run_cmd(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = fd.main(argv)
        return rc, buf.getvalue()


class TestApply(Base):
    def test_marker_written_on_first_copy(self):
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.skills / "tt" / fd.MARKER).exists())
        self.assertIn("added 2", out)
        self.assertIn("FLEET PULSE OK", out)

    def test_kept_yours_not_overwritten(self):
        mine = self.skills / "tt"
        mine.mkdir(parents=True)
        (mine / "SKILL.md").write_text("MY OWN VERSION\n", encoding="utf-8")
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 0, out)
        self.assertEqual((mine / "SKILL.md").read_text(encoding="utf-8"), "MY OWN VERSION\n")
        self.assertFalse((mine / fd.MARKER).exists())
        self.assertIn("kept-yours 1", out)

    def test_second_run_is_unchanged(self):
        self.run_cmd(["pull"])
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 0)
        self.assertIn("added 0, updated 0", out)
        self.assertIn("unchanged 2", out)

    def test_dry_run_copies_nothing(self):
        rc, out = self.run_cmd(["pull", "--dry-run"])
        self.assertEqual(rc, 0, out)
        self.assertFalse(self.skills.exists())
        self.assertFalse(fd.journal_path(self.home).exists())

    def test_journal_one_line_per_run(self):
        self.run_cmd(["pull"])
        self.run_cmd(["pull"])
        lines = fd.journal_path(self.home).read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        e = json.loads(lines[0])
        self.assertEqual(e["result"], "OK")
        self.assertEqual(len(e["repos"]), 2)

    def test_git_failure_is_fail_not_ok(self):
        def broken(args, cwd=None):
            if args[0] == "pull":
                return 1, "fatal: cannot ff"
            return fake_git_factory({})(args, cwd)
        fd.run_git = broken
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 1)
        self.assertIn("FLEET PULSE FAIL", out)
        self.assertNotIn("FLEET PULSE OK", out)

    def test_git_missing_exit_2(self):
        fd.run_git = lambda args, cwd=None: (127, "git not found")
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 2)


class TestUninstall(Base):
    def test_uninstall_removes_only_marked(self):
        mine = self.skills / "mine"
        mine.mkdir(parents=True)
        (mine / "SKILL.md").write_text("mine\n", encoding="utf-8")
        self.run_cmd(["pull"])
        self.assertTrue((self.skills / "tt" / fd.MARKER).exists())
        rc, out = self.run_cmd(["uninstall"])
        self.assertEqual(rc, 0, out)
        self.assertFalse((self.skills / "tt").exists())
        self.assertTrue((mine / "SKILL.md").exists())
        self.assertFalse(self.home.exists())
        self.assertIn("skills removed (had marker): 2", out)


    def test_uninstall_survives_readonly_git_objects(self):
        # git marks pack files read-only; on Windows plain rmtree raises WinError 5
        self.run_cmd(["pull"])
        ro = self.home / "kit" / ".git" / "objects" / "pack" / "pack-x.idx"
        ro.parent.mkdir(parents=True, exist_ok=True)
        ro.write_text("x", encoding="utf-8")
        os.chmod(ro, 0o444)
        rc, out = self.run_cmd(["uninstall"])
        self.assertEqual(rc, 0, out)
        self.assertFalse(self.home.exists())


class TestStatus(Base):
    def test_status_stale(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=40)).replace(microsecond=0).isoformat()
        fd.append_journal(self.home, {"ts": old, "repos": [], "skills": {}, "result": "OK"})
        rc, out = self.run_cmd(["status"])
        self.assertEqual(rc, 1)
        self.assertIn("STALE", out)

    def test_status_fresh(self):
        self.run_cmd(["pull"])
        rc, out = self.run_cmd(["status"])
        self.assertEqual(rc, 0, out)
        self.assertNotIn("STALE", out)

    def test_status_never_ran(self):
        rc, out = self.run_cmd(["status"])
        self.assertEqual(rc, 1)
        self.assertIn("never ran", out)


class TestSchedule(Base):
    def test_windows_prints_schtasks(self):
        txt = fd.schedule_text("win32", Path("C:/x/fleet_daily.py"), "python")
        self.assertIn("schtasks /create", txt)
        self.assertIn("07:00", txt)
        self.assertNotIn("launchctl", txt)

    def test_linux_prints_cron(self):
        txt = fd.schedule_text("linux", Path("/x/fleet_daily.py"), "python3")
        self.assertIn("0 7 * * *", txt)


if __name__ == "__main__":
    unittest.main(verbosity=1)
