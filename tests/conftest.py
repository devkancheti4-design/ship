import subprocess

import pytest


@pytest.fixture(autouse=True)
def hermetic_git(monkeypatch, tmp_path_factory):
    """No user config, no system config, no host hooks, no host check, no host model."""
    cfg = tmp_path_factory.mktemp("gitcfg") / "gitconfig"
    cfg.write_text(
        "[user]\n\tname = Ship Tests\n\temail = ship@example.invalid\n"
        "[commit]\n\tgpgsign = false\n[init]\n\tdefaultBranch = feature\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(cfg))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("SHIP_CHECK", "none")          # tests opt in to a check explicitly
    monkeypatch.delenv("SHIP_MODEL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")   # discard port: the real eyes never answer in tests


def sh(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    sh(r, "init", "-q", "-b", "feature")
    (r / "README.md").write_text("# demo\n")
    sh(r, "add", "README.md")
    sh(r, "commit", "-q", "-m", "init")
    return r


@pytest.fixture
def remote(repo, tmp_path):
    bare = tmp_path / "remote.git"
    sh(tmp_path, "init", "-q", "--bare", str(bare))
    sh(repo, "remote", "add", "origin", str(bare))
    sh(repo, "push", "-q", "-u", "origin", "feature")
    return bare


class Eyes:
    """A test double for the local model: answers what it is told to, and remembers being asked."""

    def __init__(self, text="Add greeting file\n\n- add hello.txt with a greeting"):
        self.text = text
        self.calls = 0

    def __call__(self, change, hint):
        self.calls += 1
        return self.text, "test eyes"


@pytest.fixture
def eyes():
    return Eyes()
