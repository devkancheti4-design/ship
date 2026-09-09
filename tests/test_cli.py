import json

import pytest

from conftest import Eyes
from ship import cli


def test_selfcheck_reports_zero_violations(capsys):
    assert cli.main(["selfcheck"]) == 0
    out = capsys.readouterr().out
    assert out.count("TOTAL  256 inputs  0 violations") == 4          # two laws, Python and C each
    assert "PUSH 1  COMMIT 7  STAGE 8  NONE 240" in out and "partition 128/64/32/16/8/2/1/5" in out


def test_not_a_repository(tmp_path, capsys):
    assert cli.main(["-C", str(tmp_path)]) == 1
    assert "not a git repository" in capsys.readouterr().err


def test_one_command_from_a_plain_folder(tmp_path, capsys):
    """A folder and a remote URL: one command creates the repo, sets origin, commits and pushes."""
    from conftest import sh
    bare = tmp_path / "remote.git"
    sh(tmp_path, "init", "-q", "--bare", str(bare))
    folder = tmp_path / "myapp"
    folder.mkdir()
    (folder / "app.py").write_text("def main():\n    return 1\n")
    assert cli.main(["-C", str(folder), "--to", str(bare)]) == 0
    out = capsys.readouterr().out
    assert "created a repository in myapp/ on branch work" in out and f"origin -> {bare}" in out
    assert "act PUSH" in out and "pushed to origin/work" in out
    assert sh(bare, "log", "--oneline", "work").strip().endswith("feat(app): add main")
    assert sh(folder, "branch", "--show-current").strip() == "work"


def test_url_as_first_word_is_the_remote_not_the_hint(tmp_path, capsys):
    from conftest import sh
    bare = tmp_path / "remote.git"
    sh(tmp_path, "init", "-q", "--bare", str(bare))
    folder = tmp_path / "site"
    folder.mkdir()
    (folder / "index.html").write_text("<h1>hi</h1>\n")
    assert cli.main(["-C", str(folder), f"file://{bare}", "first", "version"]) == 0
    assert sh(bare, "log", "-1", "--format=%s", "work").strip() == "first version"


def test_existing_repo_without_remote_gets_one(repo, tmp_path, capsys):
    from conftest import sh
    bare = tmp_path / "remote.git"
    sh(tmp_path, "init", "-q", "--bare", str(bare))
    (repo / "hello.txt").write_text("hi\n")
    assert cli.main(["-C", str(repo), "--to", str(bare)]) == 0
    out = capsys.readouterr().out
    assert "created a repository" not in out and "pushed to origin/feature" in out


def test_a_different_existing_remote_is_never_replaced(repo, remote, tmp_path, capsys):
    (repo / "hello.txt").write_text("hi\n")
    assert cli.main(["-C", str(repo), "--to", "https://example.invalid/other.git"]) == 1
    err = capsys.readouterr().err
    assert "origin is already" in err and "git remote set-url" in err
    from conftest import sh
    assert sh(repo, "remote", "get-url", "origin").strip() == str(remote)


def test_a_second_ship_in_the_created_repo_needs_no_url(tmp_path, capsys):
    from conftest import sh
    bare = tmp_path / "remote.git"
    sh(tmp_path, "init", "-q", "--bare", str(bare))
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("def a():\n    return 1\n")
    assert cli.main(["-C", str(folder), "--to", str(bare)]) == 0
    (folder / "a.py").write_text("def a():\n    if a is None:\n        raise ValueError\n    return 1\n")
    capsys.readouterr()
    assert cli.main(["-C", str(folder)]) == 0
    assert "fix(a): guard a" in capsys.readouterr().out
    assert sh(bare, "rev-list", "--count", "work").strip() == "2"


def test_dry_run_json_from_the_cli(repo, remote, capsys, monkeypatch):
    monkeypatch.setenv("SHIP_CHECK", "true")
    monkeypatch.setattr("ship.eyes.summarize", Eyes())
    (repo / "hello.txt").write_text("hi\n")
    assert cli.main(["-C", str(repo), "-n", "--json", "say", "hi"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["act_name"] == "PUSH" and j["outcome"]["dry_run"] is True


def test_real_eyes_unreachable_means_blind_not_a_crash(repo, remote, capsys, monkeypatch):
    """OLLAMA_HOST points at a discard port in tests: the eyes fail, the law says STAGE."""
    (repo / "hello.txt").write_text("hi\n")
    assert cli.main(["-C", str(repo), "--eyes", "ollama"]) == 0
    out = capsys.readouterr().out
    assert "act STAGE" in out and "BLIND      1" in out and "git commit -eF" in out


def test_default_eyes_are_the_law_and_cost_nothing(repo, remote, capsys):
    (repo / "hello.txt").write_text("hi\n")
    assert cli.main(["-C", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "act PUSH" in out and "SAY law docs 0x08 DOCSONLY" in out and "0 tokens" in out
    from conftest import sh
    assert sh(repo, "log", "-1", "--format=%s").strip() == "docs: add hello.txt"


def test_refusal_exit_code_and_wording(repo, remote, capsys):
    (repo / "id_rsa").write_text("nope\n")
    assert cli.main(["-C", str(repo)]) == 2
    out = capsys.readouterr().out
    assert "act NONE" in out and "refused (SECRET)" in out and "byte-identical" in out


def test_confirm_no_writes_nothing(repo, remote, capsys, monkeypatch):
    import io
    from conftest import sh
    (repo / "hello.txt").write_text("hi\n")
    before = sh(repo, "rev-parse", "HEAD")
    monkeypatch.setattr("sys.stdin", io.StringIO("n\n"))
    assert cli.main(["-C", str(repo), "-i"]) == 0
    out = capsys.readouterr().out
    assert "act PUSH" in out and "Continue? [y/N]" in out and "declined: would stage, commit and push; nothing written" in out
    assert sh(repo, "rev-parse", "HEAD") == before and sh(repo, "diff", "--cached", "--name-only") == ""


def test_confirm_yes_proceeds(repo, remote, capsys, monkeypatch):
    import io
    from conftest import sh
    (repo / "hello.txt").write_text("hi\n")
    monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))
    assert cli.main(["-C", str(repo), "--confirm"]) == 0
    assert "pushed to origin/feature" in capsys.readouterr().out
    assert sh(remote, "rev-parse", "feature").strip() == sh(repo, "rev-parse", "HEAD").strip()


def test_confirm_with_no_input_fails_closed(repo, remote, capsys, monkeypatch):
    import io
    (repo / "hello.txt").write_text("hi\n")
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert cli.main(["-C", str(repo), "-i"]) == 0
    assert "declined" in capsys.readouterr().out


def test_ruling_prints_before_the_outcome(repo, remote, capsys):
    (repo / "hello.txt").write_text("hi\n")
    assert cli.main(["-C", str(repo)]) == 0
    out = capsys.readouterr().out
    assert out.index("act PUSH") < out.index("FORWARD    1") < out.index("-> staged 1 path")


def test_a_path_ending_in_dot_git_is_a_remote(tmp_path, capsys):
    from conftest import sh
    bare = tmp_path / "remote.git"
    sh(tmp_path, "init", "-q", "--bare", str(bare))
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("def a():\n    return 1\n")
    assert cli.main(["-C", str(folder), "../remote.git"]) == 0
    assert "pushed to origin/work" in capsys.readouterr().out
    assert sh(bare, "rev-list", "--count", "work").strip() == "1"


def test_never_creates_a_repo_in_a_folder_of_repos(tmp_path, capsys):
    from conftest import sh
    ws = tmp_path / "workspace"
    (ws / "proj-a").mkdir(parents=True)
    sh(ws / "proj-a", "init", "-q")
    (ws / "notes.txt").write_text("hi\n")
    assert cli.main(["-C", str(ws), "--to", "https://example.invalid/x.git"]) == 1
    err = capsys.readouterr().err
    assert "already holds git repositories (proj-a)" in err and not (ws / ".git").exists()


def test_missing_git_is_explained_not_a_traceback(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert cli.main(["-C", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "git is not installed" in err and "winget install Git.Git" in err and "xcode-select" in err
