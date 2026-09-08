# ship-push.mp4: a real terminal, the real tool, a real push

Recorded 2026-09-08 with VHS 0.11.0 (`brew install vhs`; ffmpeg and ttyd from
Homebrew) from [`ship-push.tape`](ship-push.tape), which
[`make_tape.py`](make_tape.py) generates. Every command in the video ran live
while recording. Nothing is generated, drawn, or edited afterwards.

What it shows, in order:

1. `git clone` of `github.com/devkancheti4-design/test-case-`, empty at the time.
   `ship` never pushes `main`, so the work goes on a branch.
2. `ship selfcheck`: both machine-authored laws re-proved over all 256 inputs,
   in Python and in C, on the recording machine.
3. Two files typed in, then one word: `ship`. The SAY law names it
   `feat(billing): add price_after_discount`; the SHIP law rules PUSH; the
   push creates `origin/feature` on GitHub.
4. A guard added inside the existing function. `fix(billing): guard
   price_after_discount`, pushed.
5. A leaked AWS key in `.env`: refused before the index, exit 2, tree
   untouched. The eyes, the test run and the fetch never happen.
6. A new helper with a hint on the command line: your words become the
   phrase, the law still names the kind: `feat(billing): add the total helper`.
7. `git ls-remote` shows the branch on GitHub at the local HEAD. `main` is
   pushed by hand with one plain git command, because that is not `ship`'s
   decision to make.

Reproduce: rehearse against a scratch bare remote first
(`python3 make_tape.py /path/to/scratch.git /path/to/demo rehearsal.mp4`), then
record with the real URL. The tape's `Output` must be a relative path.

Recorder caveat, as with the neo-teach video: VHS records MP4 at 25 fps and
drops frames when a screenshot exceeds its tick, so at 1080p the video runs a
few percent fast. The timings `ship` prints on screen are its own and are
unaffected.
