"""The pipeline: measure until the ruling is settled, then travel exactly that far.

Measurement order is cost order, and a bit is measured only while the law's
ruling still depends on it (law.bounds / law.depends, both consequences of R5).
So a veto skips the model and the check; a protected branch skips the fetch
and the check; only the happy path pays for everything.  No if-statement here
decides where the change goes.  The act does.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import law
from . import measure as M
from .law import (ACTS, BLIND, BULK, COMMIT, CONFLICT, DIRTY, FORWARD, GATES, NAMES, NONE, ORDER,
                  PROTECTED, PUSH, RED, SECRET, STAGE)

COST_ORDER = (DIRTY, SECRET, CONFLICT, BULK, PROTECTED, FORWARD, BLIND, RED)
MSG_FILE = "SHIP_MSG"
Eyes = Callable[[M.Change, str], tuple[Optional[str], str]]


@dataclass
class Context:
    repo: str
    eyes: Eyes
    hint: str = ""
    fetch_timeout: int = 60
    check_timeout: int = 600
    change: Optional[M.Change] = None
    summary: Optional[str] = None
    eyes_detail: str = ""


@dataclass
class Ruling:
    byte: int
    measured: int
    act: int
    details: dict = field(default_factory=dict)      # bit -> what was measured
    change: Optional[M.Change] = None
    summary: Optional[str] = None
    eyes_detail: str = ""

    @property
    def act_name(self) -> str:
        return ACTS[self.act]

    def bits(self) -> str:
        return law.describe(self.byte, self.measured)

    def unmeasured(self) -> list:
        return [NAMES[b] for b in ORDER if not self.measured & b]

    def deciders(self) -> list:
        """The bits that stopped the change where it stopped."""
        if self.act == NONE:
            if not self.byte & DIRTY:
                return ["DIRTY clear"] if self.measured & DIRTY else []
            return [NAMES[b] for b in (SECRET, CONFLICT, BULK) if self.byte & b]
        if self.act == STAGE:
            return ["BLIND"]
        if self.act == COMMIT:
            out = [NAMES[b] for b in (RED, PROTECTED) if self.byte & b]
            if self.measured & FORWARD and not self.byte & FORWARD:
                out.append("FORWARD clear")
            return out
        return []


def _change(ctx: Context) -> M.Change:
    if ctx.change is None:
        ctx.change = M.collect(ctx.repo)
    return ctx.change


def _measure(ctx: Context, bit: int) -> dict:
    """Measure one bit (the scan measures three at once).  Returns {bit: (value, detail)}."""
    try:
        if bit == DIRTY:
            return {DIRTY: M.measure_dirty(_change(ctx))}
        if bit in (SECRET, CONFLICT, BULK):
            ch = _change(ctx)
            return {SECRET: M.measure_secret(ch), CONFLICT: M.measure_conflict(ctx.repo, ch),
                    BULK: M.measure_bulk(ch)}
        if bit == PROTECTED:
            return {PROTECTED: M.measure_protected(ctx.repo)}
        if bit == FORWARD:
            return {FORWARD: M.measure_forward(ctx.repo, ctx.fetch_timeout)}
        if bit == BLIND:
            ch = _change(ctx)
            try:
                ctx.summary, ctx.eyes_detail = ctx.eyes(ch, ctx.hint)
            except Exception as e:  # the eyes may fail any way they like; the law sees BLIND
                ctx.summary, ctx.eyes_detail = None, f"eyes raised {type(e).__name__}: {e}"
            blind, reason = M.well_formed(ctx.summary)
            return {BLIND: (blind, reason if blind else f"{ctx.eyes_detail}: {reason}")}
        if bit == RED:
            return {RED: M.measure_red(ctx.repo, ctx.check_timeout)}
        raise ValueError(bit)
    except M.GitError:
        raise
    except Exception as e:  # a measurement that could not complete: fail closed
        failed = f"measurement failed: {type(e).__name__}: {e}"
        bits = (SECRET, CONFLICT, BULK) if bit in (SECRET, CONFLICT, BULK) else (bit,)
        return {b: (not (b & GATES), failed) for b in bits}


def rule(repo: str, eyes: Eyes, hint: str = "", fetch_timeout: int = 60, check_timeout: int = 600) -> Ruling:
    ctx = Context(repo, eyes, hint, fetch_timeout, check_timeout)
    byte, open_, details = 0, 0xFF, {}
    while True:
        low, high = law.bounds(byte, open_)
        if low == high:
            break
        relevant = [b for b in COST_ORDER if open_ & b and law.depends(byte, open_, b)]
        bit = relevant[0] if relevant else next(b for b in COST_ORDER if open_ & b)
        for b, (value, detail) in _measure(ctx, bit).items():
            if not open_ & b:
                continue
            if value:
                byte |= b
            open_ &= ~b
            details[b] = detail
    return Ruling(byte, 0xFF & ~open_, low, details, ctx.change, ctx.summary, ctx.eyes_detail)


# ---------------------------------------------------------------- actuation
@dataclass
class Outcome:
    act: int
    dry_run: bool = False
    staged: list = field(default_factory=list)
    message_file: Optional[str] = None
    commit: Optional[str] = None
    pushed: Optional[str] = None
    failed: Optional[str] = None       # "stage" | "commit" | "push"
    error: str = ""


def message_text(ruling: Ruling, msg_rel: str) -> str:
    if not ruling.byte & BLIND and ruling.summary:
        return ruling.summary.strip() + "\n"
    lines = ["", f"# ship: the eyes failed: {ruling.details.get(BLIND, '')}",
             f"# Write the message above this line, then:  git commit -eF {msg_rel}", "#"]
    if ruling.change is not None:
        lines += ["# " + s for s in ruling.change.stat.splitlines()]
        lines += [f"# {p} | new file" for p in ruling.change.untracked]
    if ruling.summary:
        lines += ["#", "# what the model returned:"] + ["# " + s for s in ruling.summary.splitlines()[:30]]
    return "\n".join(lines) + "\n"


def actuate(repo: str, ruling: Ruling, dry_run: bool = False) -> Outcome:
    out = Outcome(act=ruling.act, dry_run=dry_run)
    if dry_run or ruling.act == NONE or ruling.change is None:
        return out
    paths = list(ruling.change.paths)              # exactly what was measured, nothing that appeared since
    try:
        for i in range(0, len(paths), 200):
            M.git(repo, "add", "-A", "--", *paths[i:i + 200])
    except M.GitError as e:
        out.failed, out.error = "stage", str(e)
        return out
    out.staged = paths
    gd = M.git_dir(repo)
    msg_path = os.path.join(gd, MSG_FILE)
    msg_rel = os.path.relpath(msg_path, repo)
    with open(msg_path, "w", encoding="utf-8") as f:
        f.write(message_text(ruling, msg_rel))
    out.message_file = msg_rel
    if ruling.act < COMMIT:
        return out

    p = M.git(repo, "commit", "--quiet", "-F", msg_path, check=False)
    if p.returncode != 0:
        tail = [s for s in (p.stdout + p.stderr).splitlines() if s.strip()]
        out.failed, out.error = "commit", (tail[-1] if tail else f"git commit exited {p.returncode}")
        return out
    out.commit = M.git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    if ruling.act < PUSH:
        return out

    t = M.push_target(repo)
    if t is None:
        out.failed, out.error = "push", "no push target"
        return out
    if t.upstream:
        remote_branch = t.upstream[len(t.remote) + 1:]
        args = ["push", "--quiet", t.remote, f"{t.branch}:refs/heads/{remote_branch}"]
    else:
        args = ["push", "--quiet", "-u", t.remote, t.branch]
    try:
        M.git(repo, *args, timeout=120)                # never --force: git itself refuses a non-fast-forward
    except subprocess.TimeoutExpired:
        out.failed, out.error = "push", "push did not finish in 120s"
        return out
    except M.GitError as e:
        out.failed, out.error = "push", str(e).splitlines()[-1][:160]
        return out
    out.pushed = t.upstream or f"{t.remote}/{t.branch}"
    return out


def exit_code(ruling: Ruling, outcome: Outcome) -> int:
    if outcome.failed:
        return 3
    if ruling.act == NONE and ruling.byte & DIRTY:
        return 2
    return 0


INIT_BRANCH = "work"                       # never main: ship does not push main, and a new repo should ship


def looks_like_remote(arg: str) -> bool:
    return arg.startswith(("http://", "https://", "git@", "ssh://", "git://", "file://"))


def prepare(path: str, remote: Optional[str] = None) -> tuple:
    """Make `path` a repository that can ship: create it if needed, set origin if given.

    Returns (toplevel, notes).  Setup only: no commit, no push, nothing the SHIP
    law rules on.  Raises GitError with a plain sentence when it cannot proceed.
    """
    path = os.path.abspath(path)
    notes = []
    try:
        root = M.toplevel(path)
    except M.GitError:
        root = None
    if root is None:
        if not remote:
            raise M.GitError(f"{path} is not a git repository. To create one and push it: ship <remote url>")
        M.git(path, "init", "-q", "-b", INIT_BRANCH)
        root = path
        notes.append(f"created a repository in {os.path.basename(path)}/ on branch {INIT_BRANCH}")
    elif remote and not os.path.isdir(os.path.join(path, ".git")) and root != path:
        raise M.GitError(f"{path} is inside the repository at {root}; run ship there")
    if remote:
        current = M.git(root, "remote", "get-url", "origin", check=False).stdout.strip()
        if not current:
            M.git(root, "remote", "add", "origin", remote)
            notes.append(f"origin -> {remote}")
        elif current != remote:
            raise M.GitError(f"origin is already {current}; ship pushes there. To change it: git remote set-url origin {remote}")
    return root, notes


def default_eyes(mode: Optional[str] = None) -> Eyes:
    """'law' (default): the SAY law and measurement, 0 tokens.  'ollama': a local model."""
    mode = (mode or os.environ.get("SHIP_EYES", "law")).strip().lower()
    if mode == "ollama":
        from .eyes import summarize
        return summarize
    from .mechanical import summarize
    return summarize


def run(repo: str, eyes: Optional[Eyes] = None, hint: str = "", dry_run: bool = False,
        fetch_timeout: int = 60, check_timeout: int = 600):
    if eyes is None:
        eyes = default_eyes()
    ruling = rule(repo, eyes, hint, fetch_timeout, check_timeout)
    outcome = actuate(repo, ruling, dry_run)
    return ruling, outcome, exit_code(ruling, outcome)


# ---------------------------------------------------------------- reporting
def render(ruling: Ruling, outcome: Outcome) -> str:
    head = f"ship  byte 0x{ruling.byte:02X}  {ruling.bits()}"
    lines = [f"{head:<50}  act {ruling.act_name}"]
    for b in ORDER:
        if ruling.measured & b:
            lines.append(f"  {NAMES[b]:<10} {1 if ruling.byte & b else 0}  {ruling.details.get(b, '')}")
    if ruling.unmeasured():
        lines.append(f"  {'unmeasured':<10}    {' '.join(ruling.unmeasured())}  (the ruling did not depend on them)")
    if outcome.dry_run:
        lines.append(f"  -> dry run: would {_would(ruling)}; nothing written")
    elif ruling.act == NONE:
        if ruling.byte & DIRTY:
            lines.append(f"  -> refused ({', '.join(ruling.deciders())}): nothing written, the tree is byte-identical")
        else:
            lines.append("  -> nothing to record")
    else:
        done = [f"staged {len(outcome.staged)} path{'s' if len(outcome.staged) != 1 else ''}"]
        if outcome.commit:
            done.append(f"committed {outcome.commit}")
        if outcome.pushed:
            done.append(f"pushed to {outcome.pushed}")
        lines.append("  -> " + ", ".join(done))
        if outcome.failed:
            lines.append(f"  -> {outcome.failed} failed: {outcome.error}")
        elif ruling.act == STAGE:
            lines.append(f"  -> no commit ({', '.join(ruling.deciders())}); finish with:  git commit -eF {outcome.message_file}")
        elif ruling.act == COMMIT:
            lines.append(f"  -> not pushed ({', '.join(ruling.deciders())})")
    return "\n".join(lines)


def _would(ruling: Ruling) -> str:
    return {NONE: "write nothing", STAGE: "stage only", COMMIT: "stage and commit, not push",
            PUSH: "stage, commit and push"}[ruling.act]


def to_json(ruling: Ruling, outcome: Outcome) -> dict:
    return {
        "byte": ruling.byte,
        "hex": f"0x{ruling.byte:02X}",
        "act": ruling.act,
        "act_name": ruling.act_name,
        "bits": {NAMES[b]: bool(ruling.byte & b) for b in ORDER if ruling.measured & b},
        "details": {NAMES[b]: d for b, d in ruling.details.items()},
        "unmeasured": ruling.unmeasured(),
        "deciders": ruling.deciders(),
        "summary": ruling.summary if not ruling.byte & BLIND else None,
        "eyes": ruling.eyes_detail,
        "outcome": {
            "dry_run": outcome.dry_run, "staged": outcome.staged, "message_file": outcome.message_file,
            "commit": outcome.commit, "pushed": outcome.pushed, "failed": outcome.failed, "error": outcome.error,
        },
        "exit_code": exit_code(ruling, outcome),
    }
