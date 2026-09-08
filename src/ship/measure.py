"""The body: the eight measurements, all taken before any git write.

Every function here MEASURES.  None decides.  A hazard whose measurement cannot
complete is reported set (fail closed); a gate whose measurement cannot
complete is reported clear.  The law reads the byte these produce.

What counts as a secret shape, a protected branch or a bulk change lives here,
in the measurement, and nowhere in the law.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
MAX_FILES = 50
MAX_BYTES = 5 * 1024 * 1024
SCAN_BYTES = 1024 * 1024            # the secret scan reads at most this much of one file
BINARY_PROBE = 8000                 # git's own heuristic: a NUL in the first 8000 bytes
PROTECTED_NAMES = ("main", "master")
PROTECTED_PREFIXES = ("release/",)

SECRET_SHAPES = (
    ("private key header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("sk- style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("bearer token", re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("assigned secret literal", re.compile(          # DB_PASSWORD = "...", api_key_prod: '...'
        r"(?i)(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\w*"
        r"\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
)
SECRET_GLOBS = (".env", ".env.*", "*.pem", "id_rsa*", "id_ed25519*", "id_ecdsa*", "*.key", "*.p12", "*.pfx")
SECRET_GLOB_EXEMPT = (".example", ".sample", ".template", ".dist", ".pub")
CONFLICT_MARKER = re.compile(r"^(<{7}|>{7}|\|{7})( |$)")
MID_OPERATION = ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")
DIFF_SYNTAX = re.compile(r"^(diff --git|\+\+\+|---|@@)")
DIFF_GIT = re.compile(r'^diff --git "?a/(.+?)"? "?b/(.+?)"?$')
SUBJECT_LIMIT = 72


class GitError(RuntimeError):
    pass


def git(repo: str, *args: str, timeout: int = 60, check: bool = True,
        env: Optional[dict] = None) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    e["GIT_TERMINAL_PROMPT"] = "0"          # never hang on a credential prompt: fail closed instead
    e.update(env or {})
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                       errors="replace", timeout=timeout, env=e)
    if check and p.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {(p.stderr or p.stdout).strip()}")
    return p


def toplevel(path: str) -> str:
    return git(path, "rev-parse", "--show-toplevel").stdout.strip()


def git_dir(repo: str) -> str:
    d = git(repo, "rev-parse", "--git-dir").stdout.strip()
    return d if os.path.isabs(d) else os.path.join(repo, d)


def has_head(repo: str) -> bool:
    return git(repo, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0


def current_branch(repo: str) -> Optional[str]:
    p = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    return p.stdout.strip() if p.returncode == 0 else None


# ---------------------------------------------------------------- the change
@dataclass
class Change:
    paths: list = field(default_factory=list)            # every path in the delta
    status: dict = field(default_factory=dict)           # path -> XY from git status
    untracked: list = field(default_factory=list)
    unmerged: list = field(default_factory=list)
    diff: str = ""                                       # tracked changes vs HEAD, unified
    stat: str = ""
    added: list = field(default_factory=list)            # (path, line number, text)
    removed: list = field(default_factory=list)          # (path, text)
    repo: str = ""
    base: str = "HEAD"                                   # what the diff is against
    sizes: dict = field(default_factory=dict)            # path -> bytes on disk
    binary_untracked: list = field(default_factory=list)
    unreadable: list = field(default_factory=list)       # the scan could not open these
    partial: list = field(default_factory=list)          # only the first SCAN_BYTES were scanned
    nested: list = field(default_factory=list)           # git repositories inside the tree: never committed

    def render(self, budget: int = 6000) -> str:
        """What the eyes are shown: the stat, then as much diff as fits."""
        parts = [self.stat.rstrip()]
        for p in self.untracked:
            n = sum(1 for a in self.added if a[0] == p)
            parts.append(f" {p} | new file, {n} lines" + (" (binary)" if p in self.binary_untracked else ""))
        body = self.diff
        for p in self.untracked:
            if p in self.binary_untracked:
                continue
            lines = [t for (q, _, t) in self.added if q == p]
            body += f"\n--- /dev/null\n+++ b/{p}\n" + "".join(f"+{t}\n" for t in lines)
        if len(body) > budget:
            body = body[:budget] + f"\n[... diff truncated at {budget} characters ...]\n"
        return "\n".join(parts) + "\n\nDiff:\n" + body


def collect(repo: str) -> Change:
    ch = Change()
    out = git(repo, "status", "--porcelain=v1", "--untracked-files=all", "-z").stdout
    fields = out.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if xy[0] in "RC":                  # rename/copy: the original path follows
            i += 1
        if xy == "??" and path.endswith("/"):            # git lists a nested repository as one directory
            ch.nested.append(path)
            continue
        ch.paths.append(path)
        ch.status[path] = xy
        if xy == "??":
            ch.untracked.append(path)
        elif "U" in xy or xy in ("AA", "DD"):
            ch.unmerged.append(path)

    base = "HEAD" if has_head(repo) else EMPTY_TREE
    ch.diff = git(repo, "diff", base, "--no-color", "--no-ext-diff", "--no-renames", timeout=120).stdout
    ch.stat = git(repo, "diff", base, "--stat", "--no-color", "--no-renames", timeout=120).stdout

    ch.repo, ch.base = repo, base
    path, newline, in_hunk = None, 0, False
    for line in ch.diff.splitlines():
        if line.startswith("diff --git "):
            m = DIFF_GIT.match(line)
            path = m.group(2) if m else line[11:]
            in_hunk = False
            continue
        if line.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            newline = int(m.group(1)) if m else 0
            in_hunk = True
            continue
        if not in_hunk:                       # headers: ---/+++/index/mode lines
            continue
        if line.startswith("+"):
            ch.added.append((path, newline, line[1:]))
            newline += 1
        elif line.startswith("-"):
            ch.removed.append((path, line[1:]))
        elif line.startswith("\\"):
            continue
        else:
            newline += 1

    for p in ch.paths:
        if "D" in ch.status[p]:
            continue
        full = os.path.join(repo, p)
        try:
            ch.sizes[p] = os.path.getsize(full)
        except OSError:
            ch.unreadable.append(p)

    for p in ch.untracked:
        if p in ch.unreadable:
            continue
        full = os.path.join(repo, p)
        try:
            with open(full, "rb") as f:
                head = f.read(SCAN_BYTES)
        except OSError:
            ch.unreadable.append(p)
            continue
        if b"\0" in head[:BINARY_PROBE]:
            ch.binary_untracked.append(p)
            continue
        for n, text in enumerate(head.decode("utf-8", "replace").splitlines(), 1):
            ch.added.append((p, n, text))
        if ch.sizes.get(p, 0) > SCAN_BYTES:
            ch.partial.append(p)
    return ch


# ------------------------------------------------------------ measurements
def measure_dirty(ch: Change) -> tuple[bool, str]:
    n = len(ch.paths) + len(ch.nested)
    return n > 0, (f"{n} path{'s' if n != 1 else ''} differ from HEAD" if n else "working tree matches HEAD")


def _secret_path(path: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    if any(base.endswith(x) for x in SECRET_GLOB_EXEMPT):
        return False
    return any(fnmatch.fnmatch(base, g) for g in SECRET_GLOBS)


def measure_secret(ch: Change) -> tuple[bool, str]:
    hits = []
    for p in ch.paths:
        if "D" not in ch.status.get(p, "") and _secret_path(p):
            hits.append(f"{p}: secrets path shape")
    seen = set()
    for p, n, text in ch.added:
        if p in seen:
            continue
        for name, rx in SECRET_SHAPES:
            if rx.search(text):
                hits.append(f"{p}:{n}: {name}")
                seen.add(p)
                break
    for p in ch.unreadable:
        hits.append(f"{p}: could not be scanned")
    if hits:
        return True, "; ".join(hits[:4]) + (f"; +{len(hits) - 4} more" if len(hits) > 4 else "")
    note = f" ({len(ch.partial)} large file(s) scanned in part)" if ch.partial else ""
    return False, "no credential shape in added lines or staged paths" + note


def measure_conflict(repo: str, ch: Change) -> tuple[bool, str]:
    reasons = []
    gd = git_dir(repo)
    for name in MID_OPERATION:
        if os.path.exists(os.path.join(gd, name)):
            reasons.append(f"{name} present: mid-operation")
    if ch.unmerged:
        reasons.append("unmerged: " + ", ".join(ch.unmerged[:3]))
    seen = set()
    for p, n, text in ch.added:
        if p not in seen and CONFLICT_MARKER.match(text):
            reasons.append(f"{p}:{n}: conflict marker")
            seen.add(p)
    if reasons:
        return True, "; ".join(reasons[:4])
    return False, "no conflict markers, no merge in progress"


def measure_bulk(ch: Change) -> tuple[bool, str]:
    reasons = []
    if len(ch.paths) > MAX_FILES:
        reasons.append(f"{len(ch.paths)} paths (limit {MAX_FILES})")
    for p, s in ch.sizes.items():
        if s > MAX_BYTES:
            reasons.append(f"{p} is {s / 1e6:.1f} MB (limit {MAX_BYTES // (1024 * 1024)} MB)")
    if ch.binary_untracked:
        reasons.append("untracked binary: " + ", ".join(ch.binary_untracked[:3]))
    if ch.nested:
        reasons.append("git repositories inside this folder: " + ", ".join(ch.nested[:4])
                       + (f" +{len(ch.nested) - 4} more" if len(ch.nested) > 4 else "")
                       + " (run ship inside one of them)")
    if reasons:
        return True, "; ".join(reasons[:4])
    largest = max(ch.sizes.values(), default=0)
    size = f"{largest / 1e6:.1f} MB" if largest >= 1e6 else f"{largest / 1e3:.0f} kB" if largest >= 1e3 else f"{largest} B"
    return False, f"{len(ch.paths)} path(s), largest {size}, no new binaries"


def well_formed(summary: Optional[str]) -> tuple[bool, str]:
    """BLIND: does a usable summary exist?  Returns (blind, reason)."""
    if summary is None:
        return True, "the model did not answer"
    text = summary.strip()
    if not text:
        return True, "empty summary"
    subject = next(line for line in text.splitlines() if line.strip())
    if len(subject) > SUBJECT_LIMIT:
        return True, f"subject line is {len(subject)} characters (limit {SUBJECT_LIMIT})"
    for line in text.splitlines():
        if DIFF_SYNTAX.match(line):
            return True, f"contains diff syntax: {line[:40]!r}"
    return False, f"subject {subject!r}"


def measure_protected(repo: str) -> tuple[bool, str]:
    b = current_branch(repo)
    if b is None:
        return True, "HEAD is detached"
    if b in PROTECTED_NAMES or any(b.startswith(p) for p in PROTECTED_PREFIXES):
        return True, f"branch {b} is protected"
    return False, f"branch {b}"


@dataclass
class PushTarget:
    remote: str
    branch: str                      # local branch
    upstream: Optional[str] = None   # "remote/branch" if the upstream is configured


def push_target(repo: str) -> Optional[PushTarget]:
    b = current_branch(repo)
    if b is None:
        return None
    remotes = git(repo, "remote").stdout.split()
    if not remotes:
        return None
    r = git(repo, "config", "--get", f"branch.{b}.remote", check=False).stdout.strip()
    m = git(repo, "config", "--get", f"branch.{b}.merge", check=False).stdout.strip()
    if r and m and r in remotes:
        return PushTarget(r, b, f"{r}/{m.removeprefix('refs/heads/')}")
    return PushTarget("origin" if "origin" in remotes else remotes[0], b, None)


def measure_forward(repo: str, timeout: int = 60) -> tuple[bool, str]:
    t = push_target(repo)
    if t is None:
        return False, "HEAD is detached: nothing to push" if current_branch(repo) is None else "no remote configured"
    try:
        git(repo, "fetch", "--quiet", t.remote, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"fetch from {t.remote} did not finish in {timeout}s"
    except GitError as e:
        return False, f"fetch from {t.remote} failed: {str(e).splitlines()[-1][:120]}"
    ref = t.upstream or f"{t.remote}/{t.branch}"
    if git(repo, "rev-parse", "--verify", "-q", ref, check=False).returncode != 0:
        return True, f"{ref} does not exist yet: the push creates it"
    if not has_head(repo):
        return False, f"{ref} exists but HEAD has no commits"
    if git(repo, "merge-base", "--is-ancestor", ref, "HEAD", check=False).returncode == 0:
        return True, f"{ref} is an ancestor of HEAD: fast-forward"
    n = git(repo, "rev-list", "--count", f"HEAD..{ref}").stdout.strip()
    return False, f"{ref} has {n} commit(s) HEAD lacks: not a fast-forward"


def detect_check(repo: str) -> Optional[tuple]:
    """The repository's own check, if one exists.  Returns (argv-or-shell-string, label)."""
    override = os.environ.get("SHIP_CHECK")
    if override is not None:
        if override.strip().lower() in ("", "none", "off", "0"):
            return None
        return override, override
    exists = lambda *p: os.path.exists(os.path.join(repo, *p))  # noqa: E731

    pytest_signals = (
        exists("pytest.ini"), exists("conftest.py"),
        exists("pyproject.toml") and "[tool.pytest" in open(os.path.join(repo, "pyproject.toml"), errors="replace").read(),
    )
    for d in ("tests", "test"):
        if os.path.isdir(os.path.join(repo, d)):
            names = os.listdir(os.path.join(repo, d))
            if any(n.startswith("test_") or n.endswith("_test.py") for n in names if n.endswith(".py")):
                pytest_signals += (True,)
    if any(pytest_signals):
        py = sys.executable
        for venv in (".venv", "venv"):
            for cand in (os.path.join(repo, venv, "bin", "python"), os.path.join(repo, venv, "Scripts", "python.exe")):
                if os.path.exists(cand):
                    py = cand
                    break
        return [py, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], "pytest -q -x"

    if exists("package.json"):
        try:
            scripts = json.load(open(os.path.join(repo, "package.json"), errors="replace")).get("scripts", {})
        except (ValueError, OSError):
            scripts = {}
        test = scripts.get("test", "")
        if test and "no test specified" not in test:
            tool = "pnpm" if exists("pnpm-lock.yaml") else "yarn" if exists("yarn.lock") else "npm"
            return [tool, "test"], f"{tool} test"
    if exists("Cargo.toml"):
        return ["cargo", "test", "-q"], "cargo test"
    if exists("go.mod"):
        return ["go", "test", "./..."], "go test ./..."
    if exists("Makefile"):
        try:
            if re.search(r"^test\s*:", open(os.path.join(repo, "Makefile"), errors="replace").read(), re.M):
                return ["make", "test"], "make test"
        except OSError:
            pass
    return None


def measure_red(repo: str, timeout: int = 600) -> tuple[bool, str]:
    check = detect_check(repo)
    if check is None:
        return False, "no check found (no pytest, npm test, cargo, go, or make test target)"
    cmd, label = check
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, cwd=repo, shell=isinstance(cmd, str), capture_output=True,
                           text=True, errors="replace", timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return True, f"{label}: no verdict within {timeout}s"
    except OSError as e:
        return True, f"{label}: would not launch ({e.strerror or e})"
    dt = time.monotonic() - t0
    if p.returncode == 0:
        return False, f"{label}: green ({dt:.1f}s)"
    tail = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.strip()]
    return True, f"{label}: exit {p.returncode} ({dt:.1f}s)" + (f": {tail[-1][:100]}" if tail else "")
