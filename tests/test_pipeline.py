"""End to end: the change travels exactly as far as the act says, and not one step further."""
import os

import pytest

from conftest import Eyes, sh
from ship import law
from ship.law import BLIND, COMMIT, DIRTY, FORWARD, NONE, PROTECTED, PUSH, RED, SECRET, STAGE
from ship.pipeline import render, rule, run, to_json


def head(repo):
    return sh(repo, "rev-parse", "HEAD").strip()


def remote_head(remote, branch="feature"):
    return sh(remote, "rev-parse", branch).strip()


def staged(repo):
    return sh(repo, "diff", "--cached", "--name-only").split()


def add_change(repo):
    (repo / "hello.txt").write_text("hello\n")


# ---- the happy byte
def test_happy_path_pushes(repo, remote, eyes, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    add_change(repo)
    before = head(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.byte, ruling.act, code) == (0x81, PUSH, 0)
    assert ruling.measured == 0xFF and ruling.unmeasured() == []
    assert head(repo) != before and remote_head(remote) == head(repo)
    assert sh(repo, "log", "-1", "--format=%B").strip() == eyes.text
    assert outcome.staged == ["hello.txt"] and outcome.commit and outcome.pushed == "origin/feature"
    assert staged(repo) == [] and sh(repo, "status", "--porcelain") == ""
    assert eyes.calls == 1


def test_new_branch_is_pushed_with_upstream(repo, remote, eyes):
    sh(repo, "checkout", "-q", "-b", "topic")
    add_change(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert ruling.act == PUSH and outcome.pushed == "origin/topic"
    assert remote_head(remote, "topic") == head(repo)
    assert sh(repo, "config", "branch.topic.remote").strip() == "origin"


# ---- vetoes: nothing written, nothing asked
def test_secret_refuses_and_never_asks_the_eyes(repo, remote, eyes):
    (repo / ".env").write_text("TOKEN=abc\n")
    before = head(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.act, code) == (NONE, 2)
    assert ruling.byte & SECRET and ruling.byte & DIRTY
    assert eyes.calls == 0
    assert set(ruling.unmeasured()) == {"BLIND", "RED", "PROTECTED", "FORWARD"}
    assert head(repo) == before and staged(repo) == []
    assert sh(repo, "status", "--porcelain") == "?? .env\n"
    assert not os.path.exists(repo / ".git" / "SHIP_MSG")


def test_conflict_refuses(repo, remote, eyes):
    (repo / "README.md").write_text("<<<<<<< HEAD\na\n=======\nb\n>>>>>>> x\n")
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.act, code) == (NONE, 2) and staged(repo) == [] and eyes.calls == 0


def test_bulk_refuses(repo, remote, eyes):
    (repo / "dist").mkdir()
    for i in range(51):
        (repo / "dist" / f"{i}.js").write_text("x\n")
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.act, code) == (NONE, 2) and staged(repo) == [] and eyes.calls == 0


# ---- the eyes failed: index only
@pytest.mark.parametrize("text", ["", "x" * 80, "Fix\n\n+++ b/hello.txt", None])
def test_blind_stages_and_stops(repo, remote, text, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    add_change(repo)
    before = head(repo)
    eyes = Eyes(text)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.act, code) == (STAGE, 0) and ruling.byte & BLIND
    assert staged(repo) == ["hello.txt"] and head(repo) == before
    assert outcome.commit is None and outcome.pushed is None
    msg = (repo / ".git" / "SHIP_MSG").read_text()
    assert msg.startswith("\n# ship: the eyes failed") and "git commit -eF" in msg
    assert "RED" in ruling.unmeasured()          # history was unreachable; the check was never run


def test_eyes_that_raise_are_blind(repo, remote):
    add_change(repo)

    def broken(change, hint):
        raise ConnectionError("model gone")

    ruling, outcome, code = run(str(repo), eyes=broken)
    assert ruling.act == STAGE and "the model did not answer" in ruling.details[BLIND]


# ---- network tier: local checkpoint only
def test_protected_branch_commits_but_never_pushes_and_skips_the_check(repo, remote, eyes, tmp_path, monkeypatch):
    marker = tmp_path / "check-ran"
    monkeypatch.setenv("SHIP_CHECK", f"touch {marker}")
    sh(repo, "checkout", "-q", "-b", "main")
    add_change(repo)
    before = head(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.act, code) == (COMMIT, 0) and ruling.byte & PROTECTED
    assert head(repo) != before and outcome.commit and outcome.pushed is None
    assert sh(remote, "branch", "--list", "main").strip() == ""
    assert not marker.exists() and {"RED", "FORWARD"} <= set(ruling.unmeasured())
    assert ruling.deciders() == ["PROTECTED"]


def test_diverged_branch_commits_but_never_pushes(repo, remote, eyes, tmp_path, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    other = tmp_path / "other"
    sh(tmp_path, "clone", "-q", str(remote), str(other))
    (other / "b.txt").write_text("b\n")
    sh(other, "add", "b.txt")
    sh(other, "commit", "-q", "-m", "elsewhere")
    sh(other, "push", "-q", "origin", "HEAD:feature")
    theirs = remote_head(remote)
    add_change(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.act, code) == (COMMIT, 0)
    assert not ruling.byte & FORWARD and "not a fast-forward" in ruling.details[FORWARD]
    assert outcome.commit and outcome.pushed is None and remote_head(remote) == theirs
    assert "RED" in ruling.unmeasured() and ruling.deciders() == ["FORWARD clear"]


def test_red_check_commits_but_never_pushes(repo, remote, eyes, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "false")
    add_change(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.byte, ruling.act, code) == (0xA1, COMMIT, 0)
    assert outcome.commit and outcome.pushed is None and remote_head(remote) != head(repo)


def test_no_remote_commits_but_never_pushes(repo, eyes, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    add_change(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.byte, ruling.act) == (0x01, COMMIT) and outcome.commit


# ---- nothing to do, dry runs, and what the body must not do
def test_clean_tree_is_nothing_to_record(repo, remote, eyes):
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert (ruling.act, code) == (NONE, 0) and eyes.calls == 0
    assert ruling.measured == DIRTY and "nothing to record" in render(ruling, outcome)


def test_dry_run_writes_nothing(repo, remote, eyes, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    add_change(repo)
    before = head(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes, dry_run=True)
    assert ruling.act == PUSH and outcome.dry_run and code == 0
    assert head(repo) == before and staged(repo) == [] and remote_head(remote) == before
    assert not os.path.exists(repo / ".git" / "SHIP_MSG")
    assert "dry run" in render(ruling, outcome)


def test_only_the_measured_change_is_staged(repo, remote, eyes, monkeypatch):
    """A file the check creates after measurement is not part of the change that was ruled on."""
    monkeypatch.setenv("SHIP_CHECK", "touch created_by_check.txt")
    add_change(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert ruling.act == PUSH and outcome.staged == ["hello.txt"]
    assert sh(repo, "show", "--name-only", "--format=", "HEAD").split() == ["hello.txt"]
    assert sh(repo, "status", "--porcelain") == "?? created_by_check.txt\n"


def test_hook_rejection_is_reported_not_hidden(repo, remote, eyes, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'hook says no'\nexit 1\n")
    hook.chmod(0o755)
    add_change(repo)
    before = head(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes)
    assert ruling.act == PUSH and outcome.failed == "commit" and code == 3
    assert "hook says no" in outcome.error and head(repo) == before and staged(repo) == ["hello.txt"]
    assert "commit failed" in render(ruling, outcome)


def test_hint_reaches_the_eyes(repo, remote):
    seen = {}

    def eyes(change, hint):
        seen["hint"] = hint
        seen["render"] = change.render()
        return "Add greeting\n\n- hello", "x"

    add_change(repo)
    rule(str(repo), eyes, hint="say hello")
    assert seen["hint"] == "say hello" and "hello.txt" in seen["render"] and "+hello" in seen["render"]


def test_json_report_is_complete(repo, remote, eyes, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    add_change(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes, dry_run=True)
    j = to_json(ruling, outcome)
    assert j["hex"] == "0x81" and j["act_name"] == "PUSH" and j["bits"]["FORWARD"] is True
    assert j["summary"] == eyes.text and j["outcome"]["dry_run"] is True and j["exit_code"] == 0


def test_render_names_every_measured_bit(repo, remote, eyes, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    add_change(repo)
    ruling, outcome, code = run(str(repo), eyes=eyes, dry_run=True)
    text = render(ruling, outcome)
    for name in law.NAMES.values():
        assert name in text
    assert text.startswith("ship  byte 0x81  DIRTY FORWARD")
