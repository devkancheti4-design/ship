"""Every bit is measured, never opined.  Each test builds the situation in a real repository."""
import os

import pytest

from conftest import sh
from ship import measure as M


# Built at runtime so this file is not itself secret-shaped: ship scans added lines, and a
# literal key here would make the suite uncommittable by the very tool it tests.
LIVE_AWS_KEY = "AKIA" + "5TQ7WJ2H4RNZ6BXC"


def scan(repo):
    ch = M.collect(str(repo))
    return ch, M.measure_dirty(ch), M.measure_secret(ch), M.measure_conflict(str(repo), ch), M.measure_bulk(ch)


# ---- DIRTY
def test_clean_tree_is_not_dirty(repo):
    ch, dirty, *_ = scan(repo)
    assert dirty[0] is False and ch.paths == []


def test_modified_tracked_file_is_dirty(repo):
    (repo / "README.md").write_text("# demo\nmore\n")
    ch, dirty, secret, conflict, bulk = scan(repo)
    assert dirty[0] and ch.paths == ["README.md"]
    assert (secret[0], conflict[0], bulk[0]) == (False, False, False)
    assert ("README.md", 2, "more") in ch.added


def test_untracked_file_is_dirty_and_scanned(repo):
    (repo / "hello.txt").write_text("hi\nthere\n")
    ch, dirty, *_ = scan(repo)
    assert dirty[0] and ch.untracked == ["hello.txt"]
    assert ("hello.txt", 2, "there") in ch.added


def test_already_staged_change_counts(repo):
    (repo / "new.txt").write_text("x\n")
    sh(repo, "add", "new.txt")
    ch, dirty, *_ = scan(repo)
    assert dirty[0] and ch.status["new.txt"] == "A "


def test_unborn_repository(tmp_path):
    r = tmp_path / "unborn"
    r.mkdir()
    sh(r, "init", "-q")
    (r / "a.txt").write_text("first\n")
    ch, dirty, secret, conflict, bulk = scan(r)
    assert dirty[0] and not secret[0] and not conflict[0] and not bulk[0]


# ---- SECRET
def test_aws_key_in_added_line(repo):
    (repo / "config.py").write_text(f"KEY = '{LIVE_AWS_KEY}'\n")
    _, _, secret, *_ = scan(repo)
    assert secret[0] and "config.py:1: AWS access key" in secret[1]


def test_private_key_header(repo):
    (repo / "notes.txt").write_text("-----BEGIN RSA PRIVATE KEY-----\nabc\n")
    assert scan(repo)[2][0]


def test_assigned_password_literal(repo):
    (repo / "settings.py").write_text('DB_PASSWORD = "hunter2hunter2"\n')
    assert scan(repo)[2][0]


def test_password_without_literal_is_not_a_secret(repo):
    (repo / "auth.py").write_text("password = input('password: ')\npassword: str\n")
    assert not scan(repo)[2][0]


def test_dotenv_path_is_a_secret_shape(repo):
    (repo / ".env").write_text("A=1\n")
    secret = scan(repo)[2]
    assert secret[0] and ".env: secrets path shape" in secret[1]


def test_dotenv_example_is_exempt(repo):
    (repo / ".env.example").write_text("A=\n")
    assert not scan(repo)[2][0]


def test_deleting_a_secret_file_is_not_a_secret(repo):
    (repo / "server.pem").write_text("not really\n")
    sh(repo, "add", "server.pem")
    sh(repo, "commit", "-q", "-m", "oops")
    (repo / "server.pem").unlink()
    ch, dirty, secret, *_ = scan(repo)
    assert dirty[0] and not secret[0]


def test_secret_only_in_removed_lines_is_not_flagged(repo):
    (repo / "README.md").write_text(f"# demo\ntoken = '{LIVE_AWS_KEY}'\n")
    sh(repo, "add", "README.md")
    sh(repo, "commit", "-q", "-m", "leak")
    (repo / "README.md").write_text("# demo\n")
    assert not scan(repo)[2][0]


# ---- CONFLICT
def test_conflict_markers(repo):
    (repo / "README.md").write_text("<<<<<<< HEAD\n# demo\n=======\n# other\n>>>>>>> theirs\n")
    conflict = scan(repo)[3]
    assert conflict[0] and "README.md:1: conflict marker" in conflict[1]


def test_setext_underline_is_not_a_marker(repo):
    (repo / "README.md").write_text("Title\n=======\n")
    assert not scan(repo)[3][0]


def test_merge_head_means_mid_operation(repo):
    (repo / "README.md").write_text("# demo\nx\n")
    (repo / ".git" / "MERGE_HEAD").write_text("0" * 40 + "\n")
    conflict = scan(repo)[3]
    assert conflict[0] and "MERGE_HEAD present" in conflict[1]


# ---- BULK
def test_fifty_one_files_is_bulk(repo):
    (repo / "dist").mkdir()
    for i in range(51):
        (repo / "dist" / f"f{i}.js").write_text("x\n")
    bulk = scan(repo)[4]
    assert bulk[0] and "51 paths" in bulk[1]


def test_fifty_files_is_not_bulk(repo):
    (repo / "dist").mkdir()
    for i in range(50):
        (repo / "dist" / f"f{i}.js").write_text("x\n")
    assert not scan(repo)[4][0]


def test_oversized_file_is_bulk(repo):
    with open(repo / "big.log", "wb") as f:
        f.seek(M.MAX_BYTES)
        f.write(b"\n")
    bulk = scan(repo)[4]
    assert bulk[0] and "big.log" in bulk[1]


def test_untracked_binary_is_bulk(repo):
    (repo / "blob.bin").write_bytes(b"\x00\x01\x02" * 100)
    bulk = scan(repo)[4]
    assert bulk[0] and "blob.bin" in bulk[1]


def test_modified_tracked_binary_is_not_bulk(repo):
    (repo / "img.bin").write_bytes(b"\x00\x01")
    sh(repo, "add", "img.bin")
    sh(repo, "commit", "-q", "-m", "img")
    (repo / "img.bin").write_bytes(b"\x00\x02")
    ch, dirty, secret, conflict, bulk = scan(repo)
    assert dirty[0] and not bulk[0]


# ---- BLIND
@pytest.mark.parametrize("text,blind", [
    (None, True), ("", True), ("   \n", True),
    ("x" * 73, True), ("x" * 72 + "\n\nbody", False),
    ("Fix thing\n\n--- a/file\n+++ b/file", True),
    ("Fix thing\n\n@@ -1 +1 @@", True),
    ("Fix thing\n\ndiff --git a b", True),
    ("Fix thing\n\n- one\n- two", False),
])
def test_well_formed(text, blind):
    assert M.well_formed(text)[0] is blind


# ---- PROTECTED
def test_feature_branch_is_not_protected(repo):
    assert M.measure_protected(str(repo)) == (False, "branch feature")


@pytest.mark.parametrize("name", ["main", "master", "release/1.2"])
def test_protected_names(repo, name):
    sh(repo, "checkout", "-q", "-b", name)
    assert M.measure_protected(str(repo))[0]


def test_detached_head_is_protected(repo):
    sh(repo, "checkout", "-q", "--detach")
    assert M.measure_protected(str(repo)) == (True, "HEAD is detached")


# ---- FORWARD
def test_no_remote_is_not_forward(repo):
    assert M.measure_forward(str(repo)) == (False, "no remote configured")


def test_in_sync_is_forward(repo, remote):
    fwd = M.measure_forward(str(repo))
    assert fwd[0] and "fast-forward" in fwd[1]


def test_local_commits_ahead_is_forward(repo, remote):
    (repo / "a.txt").write_text("a\n")
    sh(repo, "add", "a.txt")
    sh(repo, "commit", "-q", "-m", "ahead")
    assert M.measure_forward(str(repo))[0]


def test_remote_ahead_is_not_forward(repo, remote, tmp_path):
    other = tmp_path / "other"
    sh(tmp_path, "clone", "-q", str(remote), str(other))
    (other / "b.txt").write_text("b\n")
    sh(other, "add", "b.txt")
    sh(other, "commit", "-q", "-m", "elsewhere")
    sh(other, "push", "-q", "origin", "HEAD:feature")
    fwd = M.measure_forward(str(repo))
    assert not fwd[0] and "1 commit(s) HEAD lacks" in fwd[1]


def test_new_branch_is_forward(repo, remote):
    sh(repo, "checkout", "-q", "-b", "topic")
    fwd = M.measure_forward(str(repo))
    assert fwd[0] and "does not exist yet" in fwd[1]


def test_detached_head_is_not_forward(repo, remote):
    sh(repo, "checkout", "-q", "--detach")
    assert not M.measure_forward(str(repo))[0]


def test_unreachable_remote_is_not_forward(repo):
    sh(repo, "remote", "add", "origin", str(repo / "nowhere.git"))
    fwd = M.measure_forward(str(repo), timeout=30)
    assert not fwd[0] and "fetch from origin failed" in fwd[1]


# ---- RED
def test_no_check_is_not_red(repo, monkeypatch):
    monkeypatch.delenv("SHIP_CHECK")
    assert M.measure_red(str(repo)) == (False, "no check found (no pytest, npm test, cargo, go, or make test target)")


def test_green_check(repo, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    red = M.measure_red(str(repo))
    assert not red[0] and red[1].startswith("true: green")


def test_red_check(repo, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "false")
    red = M.measure_red(str(repo))
    assert red[0] and "exit 1" in red[1]


def test_check_that_cannot_launch_is_red(repo, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "ship-no-such-command-xyz")
    assert M.measure_red(str(repo))[0]


def test_check_that_times_out_is_red(repo, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "sleep 5")
    red = M.measure_red(str(repo), timeout=1)
    assert red[0] and "no verdict within 1s" in red[1]


def test_detects_pytest(repo, monkeypatch):
    monkeypatch.delenv("SHIP_CHECK")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    cmd, label = M.detect_check(str(repo))
    assert cmd[1:3] == ["-m", "pytest"] and label.startswith("pytest")


def test_detects_npm_test_but_not_the_placeholder(repo, monkeypatch):
    monkeypatch.delenv("SHIP_CHECK")
    (repo / "package.json").write_text('{"scripts": {"test": "echo \\"Error: no test specified\\" && exit 1"}}')
    assert M.detect_check(str(repo)) is None
    (repo / "package.json").write_text('{"scripts": {"test": "jest"}}')
    assert M.detect_check(str(repo)) == (["npm", "test"], "npm test")


def test_detects_make_test_target(repo, monkeypatch):
    monkeypatch.delenv("SHIP_CHECK")
    (repo / "Makefile").write_text("build:\n\techo b\n\ntest:\n\techo t\n")
    assert M.detect_check(str(repo)) == (["make", "test"], "make test")


def test_nested_repository_is_bulk_not_unscannable(repo):
    inner = repo / "lib"
    inner.mkdir()
    sh(inner, "init", "-q")
    (inner / "x.py").write_text("x = 1\n")
    ch, dirty, secret, conflict, bulk = scan(repo)
    assert dirty[0] and ch.nested == ["lib/"] and ch.paths == []
    assert not secret[0], secret
    assert bulk[0] and "git repositories inside this folder: lib/" in bulk[1]


def test_empty_new_repository_says_so(tmp_path):
    r = tmp_path / "empty"
    r.mkdir()
    sh(r, "init", "-q")
    ch, dirty, *_ = scan(r)
    assert dirty == (False, "the folder has no files yet: add one, then run ship again")


# ---- launchability (the Windows .cmd shim defect)
def test_launchable_resolves_to_an_absolute_path(monkeypatch):
    monkeypatch.setattr(M.shutil, "which", lambda name: "/usr/local/bin/npm")
    monkeypatch.setattr(M.os, "name", "posix")
    assert M.launchable(["npm", "test"]) == ["/usr/local/bin/npm", "test"]


def test_launchable_routes_a_windows_cmd_shim_through_the_interpreter(monkeypatch):
    monkeypatch.setattr(M.shutil, "which", lambda name: r"C:\Program Files\nodejs\npm.cmd")
    monkeypatch.setattr(M.os, "name", "nt")
    monkeypatch.setenv("COMSPEC", r"C:\Windows\system32\cmd.exe")
    assert M.launchable(["npm", "test"]) == [
        r"C:\Windows\system32\cmd.exe", "/c", r"C:\Program Files\nodejs\npm.cmd", "test"]


def test_launchable_leaves_an_unresolvable_command_alone(monkeypatch):
    monkeypatch.setattr(M.shutil, "which", lambda name: None)
    assert M.launchable(["nope-xyz", "test"]) == ["nope-xyz", "test"]


def test_an_unresolvable_check_is_red_with_its_reason(repo, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "")
    monkeypatch.setattr(M, "detect_check", lambda r: (["ship-no-such-tool-xyz", "test"], "npm test"))
    red = M.measure_red(str(repo))
    assert red[0] and "would not launch" in red[1]


def test_git_output_is_decoded_as_utf8_whatever_the_locale(repo, monkeypatch):
    """A non-ASCII path must not read as unscannable, which the law would veto as SECRET."""
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    (repo / "caf\u00e9.py").write_text("x = 1\n", encoding="utf-8")
    ch = M.collect(str(repo))
    assert ch.paths == ["caf\u00e9.py"] and ch.unreadable == []
    assert not M.measure_secret(ch)[0]


def test_the_venv_search_stops_at_the_first_hit(repo, monkeypatch):
    """A .venv must win over a venv, not be silently overridden by it."""
    monkeypatch.delenv("SHIP_CHECK")
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    for name in ("venv", ".venv"):
        (repo / name / "bin").mkdir(parents=True)
        (repo / name / "bin" / "python").write_text("")
    cmd, _ = M.detect_check(str(repo))
    assert cmd[0] == str(repo / ".venv" / "bin" / "python")


def test_aws_documented_example_key_is_not_a_secret(repo):
    """AWS reserves the EXAMPLE suffix for documentation, so fixtures may carry it."""
    (repo / "docs.py").write_text("EXAMPLE_KEY = 'AKIAIOSFODNN7EXAMPLE'\n")
    assert not scan(repo)[2][0]


def test_a_real_shaped_aws_key_is_still_a_secret(repo):
    (repo / "config.py").write_text(f"KEY = '{LIVE_AWS_KEY}'\n")
    secret = scan(repo)[2]
    assert secret[0] and "AWS access key" in secret[1]


# ---- PROTECTED is about where the push lands, not where you stand
def test_a_branch_whose_upstream_is_main_is_protected(repo, remote):
    """git checkout -b mywork origin/main tracks main; a push there is a push to main."""
    sh(repo, "branch", "-M", "main")
    sh(repo, "push", "-q", "-u", "origin", "main")
    sh(repo, "checkout", "-q", "-b", "mywork", "origin/main")
    prot = M.measure_protected(str(repo))
    assert prot[0] and "pushes to origin/main, which is protected" in prot[1]


def test_a_branch_with_its_own_upstream_is_not_protected(repo, remote):
    sh(repo, "checkout", "-q", "-b", "topic")
    sh(repo, "push", "-q", "-u", "origin", "topic")
    assert M.measure_protected(str(repo)) == (False, "branch topic")
