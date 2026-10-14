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
        if args[:2] == ["ls-remote", "--symref"]:
            return 0, "ref: refs/heads/main\tHEAD"
        if args[0] in ("pull", "fetch", "merge"):
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
            if args[0] in ("pull", "merge"):
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


class TestReleaseChannel(Base):
    """Default channel follows the newest release tag, not main."""

    def make_git(self, tags):
        calls = []

        def fake(args, cwd=None):
            calls.append(list(args))
            if args[0] == "--version":
                return 0, "git version 0.fake"
            if args[:2] == ["ls-remote", "--symref"]:
                return 0, "ref: refs/heads/main\tHEAD"
            if args[0] == "ls-remote":
                return 0, "\n".join("%040d\trefs/tags/%s" % (i, t) for i, t in enumerate(tags))
            if args[0] == "rev-parse":
                return 0, "a" * 40
            if args[:2] == ["ls-remote", "--symref"]:
                return 0, "ref: refs/heads/main\tHEAD"
            return 0, ""
        return fake, calls

    def tearDown(self):
        os.environ.pop("FLEET_CHANNEL", None)
        os.environ.pop("FLEET_PIN_KIT", None)
        super().tearDown()

    def test_picks_highest_semver_not_lexical(self):
        fd.run_git, calls = self.make_git(["v0.9.1", "v0.10.0", "v0.2.0", "latest"])
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 0, out)
        self.assertIn(["checkout", "--quiet", "--detach", "refs/tags/v0.10.0"], calls)
        self.assertFalse(any(c[0] == "merge" for c in calls))
        self.assertIn("release v0.10.0", out)

    def test_pin_overrides_for_rollback(self):
        # pin is per repo: kit rolls back, consensus keeps following its newest tag
        os.environ["FLEET_PIN_KIT"] = "v0.9.1"
        fd.run_git, calls = self.make_git(["v0.9.1", "v0.10.0"])
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 0, out)
        checkouts = [c[-1] for c in calls if c[:2] == ["checkout", "--quiet"]]
        self.assertEqual(checkouts, ["refs/tags/v0.9.1", "refs/tags/v0.10.0"])

    def test_pin_to_missing_tag_fails_loud(self):
        os.environ["FLEET_PIN_KIT"] = "v9.9.9"
        fd.run_git, calls = self.make_git(["v0.9.1"])
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 1, out)
        self.assertIn("v9.9.9", out)

    def test_no_tags_falls_back_to_main_and_says_so(self):
        fd.run_git, calls = self.make_git([])
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 0, out)
        self.assertIn(["merge", "--ff-only", "--quiet", "origin/main"], calls)
        self.assertIn("no release tag", out)

    def test_main_channel_keeps_old_behaviour(self):
        os.environ["FLEET_CHANNEL"] = "main"
        fd.run_git, calls = self.make_git(["v0.10.0"])
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 0, out)
        self.assertIn(["merge", "--ff-only", "--quiet", "origin/main"], calls)
        self.assertFalse(any(c[:2] == ["ls-remote", "--tags"] for c in calls))

    def test_network_error_is_not_no_tags(self):
        # review PR #2: a failed ls-remote used to fall through to main (unreleased code)
        fake, calls = self.make_git(["v0.10.0"])

        def broken(args, cwd=None):
            if args[0] == "ls-remote":
                calls.append(list(args))
                return 128, "fatal: unable to access"
            return fake(args, cwd)
        fd.run_git = broken
        rc, out = self.run_cmd(["pull"])
        self.assertEqual(rc, 1, out)
        self.assertIn("could not list release tags", out)
        self.assertFalse(any(c[0] == "merge" for c in calls))
        self.assertFalse(any(c[0] == "checkout" for c in calls))

    def test_fresh_dry_run_still_checks_pin(self):
        # review PR #2: dry-run on a fresh machine skipped release and pin entirely
        import shutil as _sh
        _sh.rmtree(self.home / "kit")
        os.environ["FLEET_PIN_KIT"] = "v9.9.9"
        fd.run_git, calls = self.make_git(["v0.9.1"])
        rc, out = self.run_cmd(["pull", "--dry-run"])
        self.assertEqual(rc, 1, out)
        self.assertIn("v9.9.9", out)
        self.assertFalse(any(c[0] == "clone" for c in calls))


class TestReleaseRealGit(unittest.TestCase):
    """Real git, no mocks: a local branch named like the tag must not be picked."""

    def setUp(self):
        import shutil as _sh
        import subprocess as _sp
        if _sh.which("git") is None:
            self.skipTest("git not installed")
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.origin = root / "origin"
        self.origin.mkdir()

        def g(*a, cwd=None):
            _sp.run(["git"] + list(a), cwd=str(cwd or self.origin), check=True,
                    capture_output=True, text=True)
        self.g = g
        g("init", "-q", "-b", "master")
        g("config", "user.email", "t@example.invalid")
        g("config", "user.name", "t")
        for i, tag in enumerate(["v0.9.1", "v0.10.0", None]):
            (self.origin / "f.txt").write_text(str(i), encoding="utf-8")
            g("add", "f.txt")
            g("commit", "-q", "-m", "c%d" % i)
            if tag:
                g("tag", tag)
        self.home = root / "fleet"
        os.environ["FLEET_HOME"] = str(self.home)
        os.environ["SKILLS_HOME"] = str(root / "skills")
        self.url = self.origin.as_uri()

    def tearDown(self):
        for k in ("FLEET_HOME", "SKILLS_HOME", "FLEET_CHANNEL"):
            os.environ.pop(k, None)
        self.tmp.cleanup()

    def sha(self, ref, cwd):
        import subprocess as _sp
        return _sp.run(["git", "rev-parse", ref], cwd=str(cwd), capture_output=True,
                       text=True).stdout.strip()

    def test_tag_wins_over_same_named_branch_and_main_returns(self):
        rec = fd.pull_repo("kit", self.url, self.home, False)
        self.assertEqual(rec["error"], "", rec)
        self.assertTrue(rec["cloned"])
        repo = self.home / "kit"
        tag_sha = self.sha("v0.10.0^{commit}", self.origin)
        self.assertEqual(self.sha("HEAD", repo), tag_sha)
        # a local branch called like the tag, on another commit
        self.g("checkout", "-q", "-b", "v0.10.0", cwd=repo)
        (repo / "trap.txt").write_text("trap", encoding="utf-8")
        self.g("add", "trap.txt", cwd=repo)
        self.g("-c", "user.email=t@example.invalid", "-c", "user.name=t",
               "commit", "-q", "-m", "trap", cwd=repo)
        self.assertNotEqual(self.sha("HEAD", repo), tag_sha)
        rec = fd.pull_repo("kit", self.url, self.home, False)
        self.assertEqual(rec["error"], "", rec)
        self.assertEqual(self.sha("HEAD", repo), tag_sha)
        # main channel goes back to origin's default branch (master here)
        os.environ["FLEET_CHANNEL"] = "main"
        rec = fd.pull_repo("kit", self.url, self.home, False)
        self.assertEqual(rec["error"], "", rec)
        self.assertEqual(self.sha("HEAD", repo), self.sha("master", self.origin))

    def test_main_return_keeps_local_commits_and_follows_rename(self):
        repo = self.home / "kit"
        self.assertEqual(fd.pull_repo("kit", self.url, self.home, False)["error"], "")
        os.environ["FLEET_CHANNEL"] = "main"
        self.assertEqual(fd.pull_repo("kit", self.url, self.home, False)["error"], "")
        # a local commit on master, then back to a release tag
        (repo / "mine.txt").write_text("mine", encoding="utf-8")
        self.g("add", "mine.txt", cwd=repo)
        self.g("-c", "user.email=t@example.invalid", "-c", "user.name=t",
               "commit", "-q", "-m", "mine", cwd=repo)
        mine = self.sha("HEAD", repo)
        os.environ.pop("FLEET_CHANNEL")
        self.assertEqual(fd.pull_repo("kit", self.url, self.home, False)["error"], "")
        # main again: must refuse to drop the local commit, not reset it away
        os.environ["FLEET_CHANNEL"] = "main"
        rec = fd.pull_repo("kit", self.url, self.home, False)
        self.assertEqual(self.sha("master", repo), mine)
        # the server renames master -> main and moves on
        self.g("branch", "-m", "master", "main")
        (self.origin / "f.txt").write_text("after rename", encoding="utf-8")
        self.g("commit", "-q", "-am", "after rename")
        os.environ.pop("FLEET_CHANNEL")
        self.assertEqual(fd.pull_repo("kit", self.url, self.home, False)["error"], "")
        os.environ["FLEET_CHANNEL"] = "main"
        rec = fd.pull_repo("kit", self.url, self.home, False)
        self.assertEqual(rec["error"], "", rec)
        self.assertEqual(self.sha("HEAD", repo), self.sha("main", self.origin))
        # and the NEXT main run after the rename works too (review round 3)
        (self.origin / "f.txt").write_text("later", encoding="utf-8")
        self.g("commit", "-q", "-am", "later")
        rec = fd.pull_repo("kit", self.url, self.home, False)
        self.assertEqual(rec["error"], "", rec)
        self.assertEqual(self.sha("HEAD", repo), self.sha("main", self.origin))


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
