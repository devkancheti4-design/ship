# Test case: `devkancheti4-design/test-case-`, 2026-09-08

The repository was **empty** when it was given as a test case: no commits, default
branch `main`. That made it the right test: every commit below, starting from an
unborn HEAD, was staged, summarised, committed and pushed by `ship`, with the
default eyes (the SAY law, 0 tokens). The clone's `origin` was pointed at a bare
scratch repository next to it, so every fetch and push is real git and nothing
reached GitHub: `git ls-remote` of the real remote was recorded before and after
and is identical (still empty). Reproduce with [`testcase/seed.sh`](testcase/seed.sh)
then [`testcase/matrix.sh`](testcase/matrix.sh); the seed files are in
[`testcase/seed/`](testcase/seed/).

| # | situation | SHIP byte | act | SAY byte, kind | subject written | eyes | wall | outcome |
|---|---|---|---|---|---|---|---|---|
| S1 | first commit ever: unborn HEAD, on main | `0x41` | COMMIT | `0xA0` feat | `feat(billing): add price_after_discount` | 0 ms | 0.214 s | staged 4 paths, committed a7bbce5; not pushed (PROTECTED) |
| S2 | nothing to record on a clean tree | `0x00` | NONE |  |  |  | 0.127 s | nothing to record |
| S3 | feature: guard + new total + tests, branch feature not on remote yet | `0x81` | PUSH | `0xE0` feat | `feat(billing): add total` | 26 ms | 0.653 s | staged 2 paths, committed 26b2e9d, pushed to origin/feature |
| S4 | a guard inside an existing function | `0x81` | PUSH | `0xC0` fix | `fix(billing): guard total` | 24 ms | 0.641 s | staged 1 path, committed 8e3e060, pushed to origin/feature |
| S5 | tests only | `0x81` | PUSH | `0x04` test | `test: add test_zero_rate` | 25 ms | 0.655 s | staged 1 path, committed 5d72340, pushed to origin/feature |
| S6 | docs only | `0x81` | PUSH | `0x08` docs | `docs: update README.md` | 24 ms | 0.659 s | staged 1 path, committed 4fd6048, pushed to origin/feature |
| S7 | manifest only | `0x81` | PUSH | `0x10` build | `build: update pyproject.toml` | 25 ms | 0.660 s | staged 1 path, committed 77a4f04, pushed to origin/feature |
| S8 | reformat only | `0x81` | PUSH | `0x82` style | `style: reformat src/billing.py` | 48 ms | 0.672 s | staged 1 path, committed ad7c429, pushed to origin/feature |
| S9 | that reformat undone by hand | `0x81` | PUSH | `0x83` revert | `revert: style: reformat src/billing.py` | 47 ms | 0.667 s | staged 1 path, committed 525a804, pushed to origin/feature |
| S10 | diffuse: five new modules in five directories | `0x81` | PUSH | `0x20` plain | `add 5 files in src/` | 0 ms | 0.647 s | staged 5 paths, committed acf3de4, pushed to origin/feature |
| S11 | a leaked key beside a real change | `0x03` | NONE |  |  |  | 0.133 s | refused (SECRET): nothing written, the tree is byte-identical |
| S12 | the same change with the key removed | `0x81` | PUSH | `0x80` plain | `update src/billing.py` | 74 ms | 0.705 s | staged 1 path, committed 5dae42c, pushed to origin/feature |
| S13 | a change on main | `0x41` | COMMIT | `0x08` docs | `docs: update README.md` | 24 ms | 0.229 s | staged 1 path, committed 5dd1364; not pushed (PROTECTED) |
| S14 | the remote moved ahead (diverged) | `0x01` | COMMIT | `0x80` plain | `update src/billing.py` | 85 ms | 0.441 s | staged 1 path, committed ef1b776; not pushed (FORWARD clear) |
| S15 | after the human rebased: push the pending commits? no: clean tree | `0x00` | NONE |  |  |  | 0.118 s | nothing to record |
| S16 | a red test suite | `0xA1` | COMMIT | `0x04` test | `test: add test_wrong` | 52 ms | 0.570 s | staged 1 path, committed 0daadf4; not pushed (RED) |
| S17 | the suite made green again: the held checkpoints travel | `0x81` | PUSH | `0x04` test | `test: update tests/test_billing.py` | 65 ms | 0.730 s | staged 1 path, committed 6512ed4, pushed to origin/feature |
| S18 | an accidental 51-file build directory | `0x09` | NONE |  |  |  | 0.139 s | refused (BULK): nothing written, the tree is byte-identical |
| S19 | dry run | `0x81` | PUSH | `0x08` docs | `docs: update README.md` | 51 ms | 0.508 s | dry run: would stage, commit and push; nothing written |

What the table shows:

- **`main` is never pushed.** S1 and S13 commit locally and stop. The human pushes `main`.
- **A new branch is created by the push** (S3), and every later push is a fast-forward.
- **Every SAY kind occurred** on this repository's own code: feat, fix, test, docs, build, style, revert, plain.
- **Refusals write nothing** (S11, S18): the tree hash is identical afterwards and the eyes, the check and the fetch never run.
- **A red suite holds the commit locally** (S16); when the suite goes green (S17) the push carries every held checkpoint.
- **A diverged remote holds the commit locally** (S14); after the human rebased, a clean tree is "nothing to record" (S15).
- **The check is auto-detected**: `pytest -q -x` from the `tests/` directory, 0.2 s per run, never run when the ruling did not need it.

## The full log

```

### S1 first commit ever: unborn HEAD, on main
$ ship
ship  byte 0x41  DIRTY PROTECTED                    act COMMIT
  DIRTY      1  4 paths differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  4 path(s), largest 178 B, no new binaries
  BLIND      0  SAY law feat 0xA0 NEWDEF FOCUSED (0 ms, 0 tokens): subject 'feat(billing): add price_after_discount'
  PROTECTED  1  branch main is protected
  unmeasured    RED FORWARD  (the ruling did not depend on them)
  -> staged 4 paths, committed a7bbce5
  -> not pushed (PROTECTED)
   [wall 0.214s]
   [exit 0]
a7bbce5 feat(billing): add price_after_discount

### S2 nothing to record on a clean tree
$ ship
ship  byte 0x00  (no bit set)                       act NONE
  DIRTY      0  working tree matches HEAD
  unmeasured    SECRET CONFLICT BULK BLIND RED PROTECTED FORWARD  (the ruling did not depend on them)
  -> nothing to record
   [wall 0.127s]
   [exit 0]

### S3 feature: guard + new total + tests, branch feature not on remote yet
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  2 paths differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  2 path(s), largest 327 B, no new binaries
  BLIND      0  SAY law feat 0xE0 NEWDEF GUARD FOCUSED (26 ms, 0 tokens): subject 'feat(billing): add total'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature does not exist yet: the push creates it
  -> staged 2 paths, committed 26b2e9d, pushed to origin/feature
   [wall 0.653s]
   [exit 0]

### S4 a guard inside an existing function
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 302 B, no new binaries
  BLIND      0  SAY law fix 0xC0 GUARD FOCUSED (24 ms, 0 tokens): subject 'fix(billing): guard total'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed 8e3e060, pushed to origin/feature
   [wall 0.641s]
   [exit 0]

### S5 tests only
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 396 B, no new binaries
  BLIND      0  SAY law test 0x04 TESTSONLY (25 ms, 0 tokens): subject 'test: add test_zero_rate'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed 5d72340, pushed to origin/feature
   [wall 0.655s]
   [exit 0]

### S6 docs only
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 249 B, no new binaries
  BLIND      0  SAY law docs 0x08 DOCSONLY (24 ms, 0 tokens): subject 'docs: update README.md'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed 4fd6048, pushed to origin/feature
   [wall 0.659s]
   [exit 0]

### S7 manifest only
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 233 B, no new binaries
  BLIND      0  SAY law build 0x10 DEPSONLY (25 ms, 0 tokens): subject 'build: update pyproject.toml'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed 77a4f04, pushed to origin/feature
   [wall 0.660s]
   [exit 0]

### S8 reformat only
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 334 B, no new binaries
  BLIND      0  SAY law style 0x82 BLANK FOCUSED (48 ms, 0 tokens): subject 'style: reformat src/billing.py'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed ad7c429, pushed to origin/feature
   [wall 0.672s]
   [exit 0]

### S9 that reformat undone by hand
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 302 B, no new binaries
  BLIND      0  SAY law revert 0x83 INVERSE BLANK FOCUSED (47 ms, 0 tokens): subject 'revert: style: reformat src/billing.py'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed 525a804, pushed to origin/feature
   [wall 0.667s]
   [exit 0]

### S10 diffuse: five new modules in five directories
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  5 paths differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  5 path(s), largest 75 B, no new binaries
  BLIND      0  SAY law plain 0x20 NEWDEF (0 ms, 0 tokens): subject 'add 5 files in src/'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 5 paths, committed acf3de4, pushed to origin/feature
   [wall 0.647s]
   [exit 0]

### S11 a leaked key beside a real change
$ ship
ship  byte 0x03  DIRTY SECRET                       act NONE
  DIRTY      1  2 paths differ from HEAD
  SECRET     1  .env: secrets path shape; .env:1: AWS access key
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  2 path(s), largest 321 B, no new binaries
  unmeasured    BLIND RED PROTECTED FORWARD  (the ruling did not depend on them)
  -> refused (SECRET): nothing written, the tree is byte-identical
   [wall 0.133s]
   [exit 2]
   tree identical after refusal: yes

### S12 the same change with the key removed
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 321 B, no new binaries
  BLIND      0  SAY law plain 0x80 FOCUSED (74 ms, 0 tokens): subject 'update src/billing.py'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed 5dae42c, pushed to origin/feature
   [wall 0.705s]
   [exit 0]

### S13 a change on main
$ ship
ship  byte 0x41  DIRTY PROTECTED                    act COMMIT
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 198 B, no new binaries
  BLIND      0  SAY law docs 0x08 DOCSONLY (24 ms, 0 tokens): subject 'docs: update README.md'
  PROTECTED  1  branch main is protected
  unmeasured    RED FORWARD  (the ruling did not depend on them)
  -> staged 1 path, committed 5dd1364
  -> not pushed (PROTECTED)
   [wall 0.229s]
   [exit 0]

### S14 the remote moved ahead (diverged)
$ ship
ship  byte 0x01  DIRTY                              act COMMIT
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 341 B, no new binaries
  BLIND      0  SAY law plain 0x80 FOCUSED (85 ms, 0 tokens): subject 'update src/billing.py'
  PROTECTED  0  branch feature
  FORWARD    0  origin/feature has 1 commit(s) HEAD lacks: not a fast-forward
  unmeasured    RED  (the ruling did not depend on them)
  -> staged 1 path, committed ef1b776
  -> not pushed (FORWARD clear)
   [wall 0.441s]
   [exit 0]

### S15 after the human rebased: push the pending commits? no: clean tree
$ ship
ship  byte 0x00  (no bit set)                       act NONE
  DIRTY      0  working tree matches HEAD
  unmeasured    SECRET CONFLICT BULK BLIND RED PROTECTED FORWARD  (the ruling did not depend on them)
  -> nothing to record
   [wall 0.118s]
   [exit 0]

### S16 a red test suite
$ ship
ship  byte 0xA1  DIRTY RED FORWARD                  act COMMIT
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 476 B, no new binaries
  BLIND      0  SAY law test 0x04 TESTSONLY (52 ms, 0 tokens): subject 'test: add test_wrong'
  RED        1  pytest -q -x: exit 1 (0.2s): 1 failed, 4 passed in 0.01s
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed 0daadf4
  -> not pushed (RED)
   [wall 0.570s]
   [exit 0]

### S17 the suite made green again: the held checkpoints travel
$ ship
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 476 B, no new binaries
  BLIND      0  SAY law test 0x04 TESTSONLY (65 ms, 0 tokens): subject 'test: update tests/test_billing.py'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> staged 1 path, committed 6512ed4, pushed to origin/feature
   [wall 0.730s]
   [exit 0]

### S18 an accidental 51-file build directory
$ ship
ship  byte 0x09  DIRTY BULK                         act NONE
  DIRTY      1  51 paths differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       1  51 paths (limit 50)
  unmeasured    BLIND RED PROTECTED FORWARD  (the ruling did not depend on them)
  -> refused (BULK): nothing written, the tree is byte-identical
   [wall 0.139s]
   [exit 2]

### S19 dry run
$ ship -n
ship  byte 0x81  DIRTY FORWARD                      act PUSH
  DIRTY      1  1 path differ from HEAD
  SECRET     0  no credential shape in added lines or staged paths
  CONFLICT   0  no conflict markers, no merge in progress
  BULK       0  1 path(s), largest 266 B, no new binaries
  BLIND      0  SAY law docs 0x08 DOCSONLY (51 ms, 0 tokens): subject 'docs: update README.md'
  RED        0  pytest -q -x: green (0.2s)
  PROTECTED  0  branch feature
  FORWARD    1  origin/feature is an ancestor of HEAD: fast-forward
  -> dry run: would stage, commit and push; nothing written
   [wall 0.508s]
   [exit 0]

=== scratch remote log (origin/feature) ===
6512ed4 test: update tests/test_billing.py
0daadf4 test: add test_wrong
ee0acf6 update src/billing.py
8415443 elsewhere
5dae42c update src/billing.py
acf3de4 add 5 files in src/
525a804 revert: style: reformat src/billing.py
ad7c429 style: reformat src/billing.py
77a4f04 build: update pyproject.toml
4fd6048 docs: update README.md
5d72340 test: add test_zero_rate
8e3e060 fix(billing): guard total
26b2e9d feat(billing): add total
a7bbce5 feat(billing): add price_after_discount
=== local main vs remote ===
5dd1364 docs: update README.md
a7bbce5 feat(billing): add price_after_discount
remote main: 
=== real GitHub remote, untouched? ===
identical (still empty)
```
