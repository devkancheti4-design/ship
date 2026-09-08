"""The mechanical eyes: the SAY law rules what the subject may claim, and
measurement supplies the nouns.  Zero tokens, deterministic, never absent.

The same change always gets the same message, and every word is traceable:
the type to say.c, the nouns to a measurement here, the why to the author's
hint.  Nothing in this file decides the kind; it measures eight bits and
renders what the law returns.
"""
from __future__ import annotations

import os
import posixpath
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from . import measure as M
from . import say as S
from .say import (BLANK, BUILD, DEPSONLY, DOCS, DOCSONLY, FEAT, FIX, FOCUSED, GUARD, INVERSE, KINDS,
                  NEWDEF, PLAIN, REVERT, STYLE, TEST, TESTSONLY)

SUBJECT_LIMIT = 72
INVERSE_DEPTH = 20
MAX_NAMES = 3

# ---------------------------------------------------------------- path classes
TEST_DIRS = {"tests", "test", "__tests__", "spec", "specs"}
DOC_DIRS = {"docs", "doc"}
DOC_EXTS = {".md", ".rst", ".txt", ".adoc", ".markdown"}
DOC_NAMES = ("README", "CHANGELOG", "LICENSE", "CONTRIBUTING", "AUTHORS", "NOTICE", "CODE_OF_CONDUCT")
DEPS_NAMES = {
    "pyproject.toml", "setup.py", "setup.cfg", "tox.ini", "pipfile", "pipfile.lock", "poetry.lock", "uv.lock",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.json", "composer.lock",
    "cargo.toml", "cargo.lock", "go.mod", "go.sum", "gemfile", "gemfile.lock", "pom.xml",
    "build.gradle", "settings.gradle", "build.gradle.kts", "settings.gradle.kts",
    "makefile", "cmakelists.txt", "dockerfile", ".pre-commit-config.yaml", ".dockerignore",
}


def classify(path: str) -> str:
    """'test' | 'deps' | 'docs' | 'code'.  First match wins, so the classes are disjoint."""
    parts = path.split("/")
    base, dirs = parts[-1], parts[:-1]
    low = base.lower()
    stem, ext = posixpath.splitext(low)
    if any(d in TEST_DIRS for d in dirs):
        return "test"
    if (low == "conftest.py" or (low.startswith("test_") and ext == ".py") or low.endswith("_test.py")
            or low.endswith("_test.go") or ".test." in low or ".spec." in low
            or low.endswith("test.java") or low.endswith("tests.cs")):
        return "test"
    if (low in DEPS_NAMES or low.startswith("dockerfile") or low.startswith("requirements")
            or ".github/workflows" in path or ext == ".gradle"):
        return "deps"
    if any(d in DOC_DIRS for d in dirs) or ext in DOC_EXTS or base.upper().startswith(DOC_NAMES):
        return "docs"
    return "code"


# ------------------------------------------------------------- line shapes
_MODS = (r"(?:(?:export|default|public|private|protected|internal|static|async|abstract|final|sealed|"
         r"override|virtual|unsafe|extern|inline|constexpr|pub(?:\([^)]*\))?)\s+)*")
DEF_KEYWORD = re.compile(
    r"^\s*" + _MODS
    + r"(?:def|class|function\*?|fn|func|struct|enum|interface|trait|impl|type|object|module|record|protocol|extension)\s+"
    + r"(?:\([^)]*\)\s+)?"                                   # a Go receiver
    + r"([A-Za-z_][A-Za-z0-9_]*)")
DEF_CONST = re.compile(r"^(?:export\s+)?(?:const|let|var|val)\s+([A-Za-z_]\w*)\s*[=:(]")   # column 0 only
DEF_SIG_MOD = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|final|abstract|override|virtual|async|sealed)\s+)+"
    r"[\w<>\[\],\s\?\.]*?\s([A-Za-z_]\w*)\s*\(")
DEF_SIG_C = re.compile(r"^[A-Za-z_][\w\s\*:<>,]*?[\s\*]([A-Za-z_]\w*)\s*\([^;]*$")
KEYWORDS = {"if", "for", "while", "switch", "return", "else", "catch", "sizeof", "case", "do", "new",
            "delete", "throw", "try", "elif", "with", "yield", "await", "print", "assert", "raise"}
GUARD_RX = re.compile(
    r"^\s*(?:raise\b|throw\b|assert\b|panic\(|return\s+(?:err\b|nil,\s*err\b|Err\()"
    r"|if\s+.*\bis\s+None\b|if\s*\(\s*!)|.*==\s*null\b|.*\berrors\.New\(")


def def_name(line: str) -> Optional[str]:
    m = DEF_KEYWORD.match(line)
    if m:
        return m.group(1)
    for rx in (DEF_CONST, DEF_SIG_MOD, DEF_SIG_C):
        m = rx.match(line)
        if m and m.group(1) not in KEYWORDS:
            return m.group(1)
    return None


def is_guard(line: str) -> bool:
    return bool(GUARD_RX.match(line))


def _indent(s: str) -> int:
    return len(s) - len(s.lstrip(" \t"))


def enclosing_def(lines: list, lineno: int) -> Optional[tuple]:
    """(line number, name) of the definition enclosing 1-based `lineno`, judged by indentation."""
    indent = _indent(lines[lineno - 1])
    if indent == 0:
        return None
    for i in range(lineno - 1, 0, -1):
        s = lines[i - 1]
        if not s.strip():
            continue
        if _indent(s) < indent:
            name = def_name(s)
            if name:
                return i, name
            if _indent(s) == 0:
                return None
    return None


GENERIC_DIRS = {"src", "lib", "libs", "app", "apps", "pkg", "internal", "cmd", "packages", "modules", "source"}
GENERIC_STEMS = {"__init__", "index", "main", "mod", "lib", "utils", "util", "helpers", "core"}


def scope_of(code_paths: list) -> str:
    """The name a maintainer would put in parentheses: the package directory when there is a
    meaningful one, the module stem for a lone file in a generic directory or at the root."""
    if len(code_paths) == 1:
        p = code_paths[0]
        stem = posixpath.splitext(posixpath.basename(p))[0]
        parents = [d for d in posixpath.dirname(p).split("/") if d][::-1]
        if parents and parents[0] not in GENERIC_DIRS:
            return parents[0]
        if stem not in GENERIC_STEMS:
            return stem
        return next((d for d in parents if d not in GENERIC_DIRS), "")
    common = posixpath.commonpath(code_paths)
    parts = [d for d in common.split("/") if d][::-1]
    return next((d for d in parts if d not in GENERIC_DIRS), "")


# ------------------------------------------------------------- the facts
@dataclass
class Facts:
    byte: int = 0
    kind: int = PLAIN
    details: dict = field(default_factory=dict)
    code_paths: list = field(default_factory=list)
    scope: str = ""
    verb: str = "update"
    new_defs: list = field(default_factory=list)          # NEWDEF names, code paths only
    guard_defs: list = field(default_factory=list)        # existing definitions that gained a guard
    defs_added: dict = field(default_factory=dict)        # path -> names (every class)
    defs_removed: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)            # path -> (added, removed)
    inverse: Optional[tuple] = None                       # (sha, subject)


def _normalize(patch: str) -> str:
    return "\n".join(s for s in patch.splitlines() if not s.startswith("index "))


def measure_inverse(ch: M.Change) -> tuple:
    if ch.untracked or "@@" not in ch.diff:
        return None, "no recorded commit could be its inverse" if ch.untracked else "no hunks"
    # one log call finds the recent commits that touch exactly these paths; only those are compared
    log = M.git(ch.repo, "log", f"-{INVERSE_DEPTH}", "--format=%x00%H%x01%s", "--name-only", "--no-renames",
                check=False).stdout
    want = set(ch.paths)
    candidates = []
    for block in log.split("\0"):
        head, _, rest = block.partition("\n")
        sha, _, subject = head.partition("\x01")
        if sha and {ln.strip() for ln in rest.splitlines() if ln.strip()} == want:
            candidates.append((sha, subject.strip()))
    if not candidates:
        return None, f"no commit in the last {INVERSE_DEPTH} touches exactly these paths"
    rev = _normalize(M.git(ch.repo, "diff", "-R", "--no-prefix", ch.base, "--no-color", "--no-ext-diff",
                           "--no-renames").stdout)
    for sha, subject in candidates:
        patch = M.git(ch.repo, "show", "--format=", "--no-prefix", "--no-color", "--no-ext-diff", "--no-renames",
                      sha, check=False).stdout
        if _normalize(patch.lstrip("\n")) == rev:
            return (sha, subject), f"inverse of {sha[:7]} {subject!r}"
    return None, f"not the inverse of any of the last {INVERSE_DEPTH} commits"


def measure_blank(ch: M.Change) -> tuple:
    if "@@" not in ch.diff:
        return False, "no hunks in the tracked diff"
    if any(t.strip() for p, _, t in ch.added if p in ch.untracked):
        return False, "an untracked file has content"
    w = M.git(ch.repo, "diff", ch.base, "-w", "--ignore-blank-lines", "--no-color", "--no-ext-diff",
              "--no-renames").stdout
    if any(s.startswith("@@") for s in w.splitlines()):
        return False, "tokens changed"
    return True, "no hunk survives -w --ignore-blank-lines"


def _is_new(ch: M.Change, p: str) -> bool:
    return ch.status.get(p, "") == "??" or ch.status.get(p, "").startswith("A")


def _is_deleted(ch: M.Change, p: str) -> bool:
    return "D" in ch.status.get(p, "")


def verb_for_paths(ch: M.Change, paths: list) -> str:
    """add when every named path is a new file, remove when every one is deleted, update otherwise."""
    if paths and all(_is_new(ch, p) for p in paths):
        return "add"
    if paths and all(_is_deleted(ch, p) for p in paths):
        return "remove"
    return "update"


def observe(ch: M.Change) -> Facts:
    f = Facts()
    classes = {p: classify(p) for p in ch.paths}
    f.code_paths = [p for p in ch.paths if classes[p] == "code"]

    # names and counts, every path
    for p in ch.paths:
        f.defs_added[p], f.defs_removed[p] = [], []
        f.counts[p] = [0, 0]
    def_paths = {p for p in ch.paths if classes[p] in ("code", "test")}   # docs and manifests define nothing
    for p, _, t in ch.added:
        if p in f.counts:
            f.counts[p][0] += 1
            n = def_name(t) if p in def_paths else None
            if n and n not in f.defs_added[p]:
                f.defs_added[p].append(n)
    for p, t in ch.removed:
        if p in f.counts:
            f.counts[p][1] += 1
            n = def_name(t) if p in def_paths else None
            if n and n not in f.defs_removed[p]:
                f.defs_removed[p].append(n)

    f.verb = verb_for_paths(ch, ch.paths)

    # ---- the byte
    byte = 0
    inv, d = measure_inverse(ch)
    f.inverse = inv
    if inv:
        byte |= INVERSE
    f.details[INVERSE] = d

    blank, d = measure_blank(ch)
    byte |= BLANK if blank else 0
    f.details[BLANK] = d

    for bit, cls in ((TESTSONLY, "test"), (DOCSONLY, "docs"), (DEPSONLY, "deps")):
        only = bool(ch.paths) and all(classes[p] == cls for p in ch.paths)
        byte |= bit if only else 0
        f.details[bit] = f"every path is {cls}" if only else f"{sum(classes[p] == cls for p in ch.paths)} of {len(ch.paths)} paths are {cls}"

    removed_names = {n for p in f.code_paths for n in f.defs_removed[p]}
    f.new_defs = [n for p in f.code_paths for n in f.defs_added[p] if n not in removed_names]
    byte |= NEWDEF if f.new_defs else 0
    f.details[NEWDEF] = ("new definitions: " + ", ".join(f.new_defs)) if f.new_defs else "no new definition in code paths"

    added_at = {(p, n) for p, n, _ in ch.added}
    moved = {(p, " ".join(t.split())) for p, t in ch.removed}      # a reindented or moved line is not a new guard
    content: dict = {}
    for p, n, t in ch.added:
        if p not in f.code_paths or p in ch.untracked or not is_guard(t) or (p, " ".join(t.split())) in moved:
            continue
        if p not in content:
            try:
                with open(os.path.join(ch.repo, p), encoding="utf-8", errors="replace") as fh:
                    content[p] = fh.read().splitlines()
            except OSError:
                content[p] = []
        lines = content[p]
        if n < 1 or n > len(lines):
            continue
        enc = enclosing_def(lines, n)
        if enc and (p, enc[0]) not in added_at and enc[1] not in f.guard_defs:
            f.guard_defs.append(enc[1])
    byte |= GUARD if f.guard_defs else 0
    f.details[GUARD] = ("guards added in existing: " + ", ".join(f.guard_defs)) if f.guard_defs else "no guard added inside an existing definition"

    tops = {p.split("/")[0] if "/" in p else "" for p in f.code_paths}
    focused = 1 <= len(f.code_paths) <= 3 and len(tops) == 1
    byte |= FOCUSED if focused else 0
    if focused:
        f.scope = scope_of(f.code_paths)
    f.details[FOCUSED] = (f"{len(f.code_paths)} code path(s) in one place" + (f", scope {f.scope}" if f.scope else "")
                          if focused else f"{len(f.code_paths)} code paths across {len(tops)} top-level directories")

    f.byte = byte
    f.kind = S.say(byte)
    return f


# ------------------------------------------------------------- rendering
def _names(names: list) -> str:
    shown = ", ".join(names[:MAX_NAMES])
    return shown + (f" +{len(names) - MAX_NAMES} more" if len(names) > MAX_NAMES else "")


def _paths_phrase(paths: list) -> str:
    if len(paths) <= 3:
        return ", ".join(paths)
    tops = {p.split("/")[0] if "/" in p else "." for p in paths}
    if len(tops) == 1:
        top = next(iter(tops))
        return f"{len(paths)} files" + (f" in {top}/" if top != "." else "")
    return f"{len(paths)} files across {len(tops)} directories"


def clip(s: str, limit: int = SUBJECT_LIMIT) -> str:
    if len(s) <= limit:
        return s
    cut = s[: limit - 1]
    if " " in cut[limit // 2:]:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:") + "…"


def measured_phrase(f: Facts, ch: M.Change) -> str:
    if f.kind == REVERT and f.inverse:
        return f.inverse[1]
    if f.kind == STYLE:
        return "reformat " + _paths_phrase(ch.paths)
    if f.kind == TEST:
        names = [n for p in ch.paths for n in f.defs_added[p] if n not in {m for q in ch.paths for m in f.defs_removed[q]}]
        return f"add {_names(names)}" if names else f"{f.verb} {_paths_phrase(ch.paths)}"
    if f.kind == FEAT:
        return "add " + _names(f.new_defs)
    if f.kind == FIX:
        return "guard " + _names(f.guard_defs)
    return f"{f.verb} {_paths_phrase(ch.paths)}"


def subject(f: Facts, ch: M.Change, hint: str = "") -> str:
    phrase = hint.strip().splitlines()[0].strip() if hint.strip() else measured_phrase(f, ch)
    if f.kind == PLAIN:
        return clip(phrase)
    scope = f"({f.scope})" if f.scope and f.kind in (FEAT, FIX) else ""
    return clip(f"{KINDS[f.kind]}{scope}: {phrase}")


def body(f: Facts, ch: M.Change) -> list:
    lines = []
    if f.kind == REVERT and f.inverse:
        lines.append(f"This reverts commit {f.inverse[0]}.")
    for p in ch.paths:
        a, r = f.counts[p]
        bits = []
        if ch.status.get(p) == "??" or ch.status.get(p, "").startswith("A"):
            bits.append("new file")
        elif "D" in ch.status.get(p, ""):
            bits.append("deleted")
        if a:
            bits.append(f"+{a}")
        if r:
            bits.append(f"-{r}")
        extras = []
        if f.defs_added[p]:
            extras.append("defines " + _names(f.defs_added[p]))
        if f.defs_removed[p]:
            extras.append("removes " + _names(f.defs_removed[p]))
        guarded = [g for g in f.guard_defs if g in f.defs_added.get(p, []) or p in f.code_paths]
        if p in f.code_paths and f.guard_defs and guarded:
            extras.append("guards " + _names(f.guard_defs))
        line = f"- {p}: {' '.join(bits) or 'changed'}"
        if extras:
            line += "; " + "; ".join(extras)
        lines.append(line)
    return lines


def render(f: Facts, ch: M.Change, hint: str = "") -> str:
    return subject(f, ch, hint) + "\n\n" + "\n".join(body(f, ch)) + "\n"


def summarize(change: M.Change, hint: str = "") -> tuple:
    """The eyes interface: (message or None, detail).  None only when git itself failed."""
    t0 = time.monotonic()
    try:
        f = observe(change)
        text = render(f, change, hint)
    except M.GitError as e:
        return None, f"SAY law: git failed: {str(e).splitlines()[-1][:100]}"
    ms = (time.monotonic() - t0) * 1000
    return text, f"SAY law {KINDS[f.kind]} 0x{f.byte:02X} {S.describe(f.byte)} ({ms:.0f} ms, 0 tokens)"
