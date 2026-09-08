# Prompt: author the SHIP law (how far one change may travel)

Author a branchless kernel that decides, for ONE working-tree change that a
user has asked to be committed, how far it may travel: into the index, into
local history, or out to the remote.

    input   one byte of observations about the change, all mechanically
            measurable before any git write
    output  act 0..3, higher travels further

        3  PUSH     stage, commit, push
        2  COMMIT   stage, commit; stop before the network
        1  STAGE    stage, write the summary to a message file; stop before
                    history
        0  NONE     write nothing, not even the index

The tool around it is a zero-config, fully local commit CLI: the working-tree
delta is the change, a local model writes the summary, git records it. The
model is the eyes. It never chooses what is staged, whether a commit exists,
or whether a push happens. Those three are this law's ruling, taken once, on
one byte, before the first git write. The body then runs the pipeline exactly
as far as the act says, and reports the byte. The only network the tool ever
touches is the user's own remote: one fetch to measure FORWARD, one push if
the act is 3. The diff never leaves the machine.

## Why this is dangerous

A commit is the one git operation that is cheap to make and expensive to
unmake. A secret that reaches the index is a `commit -a` away from history;
one that reaches history is a push away from every clone; one that reaches
the remote is out for good, whatever is force-pushed afterwards. This tool
automates all three steps from one prompt, so its failure shape is not "a bad
commit" but "a bad commit that was also pushed, under a plausible message,
before anyone looked". The law exists so that every step past the working
tree is EARNED by measurement, and so that anything unmeasured fails closed.

## The observation byte

    bit  name        meaning (measurable before any git write, none an opinion)
      0  DIRTY       the working tree differs from HEAD: a tracked file
                     modified or deleted, or an untracked non-ignored file
                     present.  0 means there is nothing to record.
      1  SECRET      a line ADDED by the change matches a credential shape
                     (private-key header, cloud access key, bearer token,
                     `password=`), or a path to be staged matches a secrets
                     glob (`.env*`, `*.pem`, `id_rsa*`, `*.key`)
      2  CONFLICT    conflict markers in any changed file, or the repository
                     is mid-operation: MERGE_HEAD, REBASE_HEAD or
                     CHERRY_PICK_HEAD exists
      3  BULK        the change is out of scale: more than 50 files, any
                     single file over 5 MB, or a binary blob not already
                     tracked.  The shape of `git add .` over build output.
      4  BLIND       the eyes failed: the summary is empty, its subject line
                     exceeds 72 characters, it contains diff syntax (a line
                     beginning `diff --git`, `+++`, `---` or `@@`), or the
                     model did not answer within budget
      5  RED         the repository's own check is red: a check exists (a
                     pre-commit hook, or an auto-detected test command) and
                     exited non-zero on this tree.  No check: 0.
      6  PROTECTED   the current branch is one the tool must not push to
                     directly (`main`, `master`, `release/*`), or HEAD is
                     detached
      7  FORWARD     a push would be a fast-forward: a remote exists and,
                     after `git fetch`, the upstream is an ancestor of HEAD
                     or does not exist yet

Fail-closed measurement: DIRTY and FORWARD are GATES, set only by a
measurement that succeeded. The other six are HAZARDS, set by a positive
finding AND by any measurement that could not complete (a scan that did not
run, a fetch that timed out, a check that would not launch). The kernel never
receives "unknown".

## The structural requirement: three tiers

SECRET, CONFLICT and BULK are VETOES: the content of the change itself is
unsafe to record. BLIND is an EYES failure: the change may be fine, but no
message exists to commit it under. RED, PROTECTED and not-FORWARD are NETWORK
hazards: the change is fine to record locally, not fine to expose.

    R1  A veto is absolute.  Any of SECRET, CONFLICT, BULK set: NONE,
        whatever the other bits say.  Nothing enters the index.  No amount
        of green, fast-forward or eloquent summary lifts a veto.
    R2  DIRTY gates everything.  DIRTY clear: NONE.  The law never invents
        work: no empty commit, no push of stale local commits on a clean
        tree.
    R3  No history without eyes.  BLIND set, no veto: STAGE at most.  A
        commit is never authored under a placeholder message; the law does
        not know what "update" or "wip" would mean and must not let the body
        find out.
    R4  No network without a green, unprotected, fast-forward path.  Any of
        RED or PROTECTED set, or FORWARD clear (no veto, not BLIND): COMMIT
        at most.  The commit is a local checkpoint; the push is the human's.
    R5  Monotone.  For every input x and every hazard bit h,
        act(x|h) <= act(x); for every gate bit g, act(x|g) >= act(x).
        Setting a hazard never moves a change further; setting a gate never
        moves it back.
    R6  Deterministic, branchless, no data-dependent loops, no tables.
        Verifiable exhaustively over all 256 inputs.

## The counts, derived before synthesis

Because the tiers nest, the partition of the 256 inputs is closed-form and
must be matched exactly:

    act 3  PUSH      1   only 0x81: DIRTY, FORWARD, nothing else
    act 2  COMMIT    7   DIRTY, no veto, not BLIND, and not
                         (green AND unprotected AND FORWARD)
    act 1  STAGE     8   DIRTY, no veto, BLIND; RED/PROTECTED/FORWARD free
    act 0  NONE    240   128 clean trees + 112 vetoed changes

A kernel that always refuses passes R1-R5 and is rejected by these counts.
So is one that pushes on any input other than 0x81.

## The situations this law must settle

None of these is measured yet; the tool does not exist. Each is the canonical
failure shape of commit automation, and the first eight runs of the tool
should replace each with a recorded byte.

1. The leaked key.  `.env` with a cloud access key sits untracked; check
   green, branch unprotected, push would fast-forward, summary fine.
   byte 0x83  (DIRTY, SECRET, FORWARD)
   REQUIRED: NONE.  Not the index, not history, not the remote.  The report
   names SECRET and the path; the tree is byte-identical afterward.

2. The half-finished merge.  MERGE_HEAD exists; two files carry `<<<<<<<`.
   byte 0x85  (DIRTY, CONFLICT, FORWARD)
   REQUIRED: NONE.  Finishing a merge is a decision, not a commit.

3. The build directory.  `dist/`, 400 files, 30 MB, untracked because nobody
   wrote the `.gitignore` line.
   byte 0x89  (DIRTY, BULK, FORWARD)
   REQUIRED: NONE.  The repair is one ignore line, not one commit.

4. The silent model.  The local model timed out, or returned an empty string.
   byte 0x91  (DIRTY, BLIND, FORWARD)
   REQUIRED: STAGE.  The index holds the change; the message file records
   the diff stat and that the eyes failed; no commit exists.  Same ruling
   with PROTECTED or RED also set (0xD1, 0xB1): BLIND caps below history
   regardless of the network tier.

5. Straight to main.  Everything green and fast-forward, but the branch is
   `main`.
   byte 0xC1  (DIRTY, PROTECTED, FORWARD)
   REQUIRED: COMMIT, not PUSH.

6. The diverged branch, or the airplane.  The upstream has three commits
   HEAD lacks, or the fetch could not complete, which measures the same.
   byte 0x01  (DIRTY only)
   REQUIRED: COMMIT, not PUSH.  The law never rebases, merges or forces; it
   reports that the push was not a fast-forward and stops.

7. The red check.  `pytest` exits 1 on this tree.
   byte 0xA1  (DIRTY, RED, FORWARD)
   REQUIRED: COMMIT, not PUSH.  A local checkpoint is cheap to fix; a red
   push is everyone's problem.

8. The clean tree, and the happy path.
   bytes 0x00 and 0x80   REQUIRED: NONE, and the report says "nothing to
                         record", not "refused".
   byte 0x81             REQUIRED: PUSH, and this is the ONLY byte that is.

## Deliverables

- `ship.c`: the kernel, same shape as `rank.c`, `sight.c` and `pair.c`:
  lanes folded, one EMIT, act from the low bits.  No branch, no compare, no
  select, no load; report the `objdump` counts as `aml` does.
- A one-paragraph derivation of why R1-R4 hold structurally, from the
  nesting of the three tiers, not by case analysis.
- An independent oracle written branchy (`if`/`else`, sharing no expression
  with the kernel) and an exhaustive self-check over all 256 inputs
  asserting R1-R5, the 1/7/8/240 counts, and the eight situations above,
  scoring "travelled further than allowed" and "refused when it must not"
  separately.

Encode no path, no branch name, no remote name, no model name.  What counts
as a secret shape, a protected branch or a bulk change lives in the
MEASUREMENT.  The law reads the SITUATION of the change, never its content.

## A note on what this law does NOT decide

- Which files.  The change is the whole working-tree delta or nothing.  A
  hazard anywhere refuses all of it; selecting a safe subset would be a
  deciding if-statement in the body.
- The words of the summary.  Those are the eyes', the local model's, and the
  law sees only whether they exist and are well-formed (BLIND).
- Recovery.  On not-FORWARD the law stops; fetching, rebasing and forcing
  are the human's.  On RED the law stops; repairing the tree is another
  law's job.
- Unpushed commits on a clean tree.  DIRTY clear is NONE.  Pushing history
  the tool did not author is not this tool's promise.
