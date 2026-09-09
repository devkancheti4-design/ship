"""ship: one prompt, one safely travelled commit."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

from . import __version__, law, say
from . import measure as M
from .pipeline import (default_eyes, looks_like_remote, prepare, render_outcome, render_ruling, run,
                       to_json, _would)

USAGE = """\
  ship                    stage, summarise, commit and push the working tree, as far as the law allows
  ship "what I did"       the same, with a hint for the eyes
  ship <remote url>       in a plain folder: create the repository, set origin, and ship it
  ship -i                 show the ruling, then ask y/N before anything is written
  ship -n                 dry run: measure and rule, write nothing
  ship selfcheck          re-derive the law over all 256 inputs (Python, and C if a compiler exists)
"""


def selfcheck_main() -> int:
    violations = 0
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    for title, module, src_name in (("SHIP law (how far the change travels)", law, "ship.c"),
                                    ("SAY law (what the subject may claim)", say, "say.c")):
        r = module.selfcheck()
        print(f"{title}, pure-Python reference over all 256 inputs:")
        print(module.format_selfcheck(r))
        violations += r["violations"]
        src = os.path.join(os.path.dirname(__file__), src_name)
        if cc and os.path.exists(src):
            with tempfile.TemporaryDirectory() as d:
                exe = os.path.join(d, "check")
                build = subprocess.run([cc, "-O2", src, "-o", exe], capture_output=True, text=True)
                if build.returncode != 0:
                    print(f"\n{src_name} did not compile with {cc}:\n{build.stderr}")
                    violations += 1
                else:
                    p = subprocess.run([exe], capture_output=True, text=True)
                    print(f"\n{src_name}, vendored kernel, compiled with {os.path.basename(cc)} -O2:")
                    print(p.stdout.rstrip())
                    violations += p.returncode != 0
        else:
            print(f"\n(no C compiler found: the vendored {src_name} was not re-run)")
        print()
    return 1 if violations else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["selfcheck"]:
        return selfcheck_main()
    if shutil.which("git") is None:
        print("ship: git is not installed, and everything ship does is git.\n"
              "  macOS:    xcode-select --install   (or: brew install git)\n"
              "  Windows:  winget install Git.Git   (or https://git-scm.com/download/win)\n"
              "  Linux:    sudo apt install git     (or your distribution's package manager)\n"
              "Then open a new terminal and run ship again.", file=sys.stderr)
        return 1
    ap = argparse.ArgumentParser(prog="ship", description=__doc__, usage=USAGE,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hint", nargs="*", help="optional words describing the change, shown to the eyes")
    ap.add_argument("-C", dest="repo", default=".", metavar="PATH", help="run in this repository or folder")
    ap.add_argument("--to", metavar="URL", default=None,
                    help="the remote to push to; in a plain folder this also creates the repository")
    ap.add_argument("-n", "--dry-run", action="store_true", help="measure and rule; write nothing")
    ap.add_argument("-i", "--confirm", action="store_true", default=os.environ.get("SHIP_CONFIRM", "") not in ("", "0"),
                    help="show the ruling and ask y/N before the first git write (also SHIP_CONFIRM=1)")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    ap.add_argument("--eyes", choices=("law", "ollama"), default=None,
                    help="who writes the summary: the SAY law (default, 0 tokens) or a local Ollama model")
    ap.add_argument("--fetch-timeout", type=int, default=int(os.environ.get("SHIP_FETCH_TIMEOUT", 60)))
    ap.add_argument("--check-timeout", type=int, default=int(os.environ.get("SHIP_CHECK_TIMEOUT", 600)))
    ap.add_argument("--version", action="version", version=f"ship {__version__}")
    args = ap.parse_args(argv)

    if args.hint and args.to is None and looks_like_remote(args.hint[0]):
        args.to = args.hint.pop(0)
    try:
        root, notes = prepare(args.repo, args.to)
    except (M.GitError, OSError) as e:
        print(f"ship: {e}", file=sys.stderr)
        return 1
    for note in notes:
        if not args.json:
            print(f"ship  {note}")
    shown = []

    def show_ruling(ruling):
        """Print the ruling as soon as it exists, before the first git write."""
        if not args.json and not shown:
            print(render_ruling(ruling), flush=True)
            shown.append(True)

    def ask(ruling) -> bool:
        show_ruling(ruling)
        try:
            answer = input(f"  -> will {_would(ruling)}. Continue? [y/N] ")
        except EOFError:
            answer = ""
        return answer.strip().lower() in ("y", "yes")

    try:
        ruling, outcome, code = run(root, eyes=default_eyes(args.eyes), hint=" ".join(args.hint), dry_run=args.dry_run,
                                    fetch_timeout=args.fetch_timeout, check_timeout=args.check_timeout,
                                    confirm=ask if args.confirm else show_ruling_then_go(show_ruling))
    except M.GitError as e:
        print(f"ship: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(to_json(ruling, outcome), indent=2))
    else:
        show_ruling(ruling)
        print(render_outcome(ruling, outcome))
    return code


def show_ruling_then_go(show):
    """Without -i: print the ruling first, then proceed without asking."""
    def go(ruling) -> bool:
        show(ruling)
        return True
    return go
