# Prompt: author the SAY law (what the subject line may claim)

Author a branchless kernel that decides, for ONE working-tree change, what
KIND of claim its commit subject may make. This law replaces the language
model as the eyes of `ship`: the model wrote prose; the law rules the claim,
and the body fills in the nouns from measurement. The SHIP law is unchanged
and still rules how far the change travels.

    input   one byte of observations about the change, all mechanically
            measurable from git and the diff, no model anywhere
    output  kind 0..7, lower is the more specific claim

        0  revert   the change undoes a recorded commit
        1  style    the change alters no token, only whitespace
        2  test     every changed path is a test
        3  docs     every changed path is documentation
        4  build    every changed path is a manifest, lockfile, build or CI file
        5  feat     a focused change introduces a new definition
        6  fix      a focused change adds a guard to an existing definition
        7  plain    no claim: the subject describes the change, never diagnoses it

The body renders `<kind>(<scope>): <phrase>` for kinds 0-6 and `<phrase>`
alone for plain, where the phrase is the author's own words when a hint was
given and the measured nouns otherwise. Every word of the message is then
traceable: the type to this law, the nouns to a measurement, the why to the
author. Nothing is inferred by anything that cannot be audited.

## Why a law and not a model

A model writes a fluent message, and that is the problem. The same diff gets
a different message on a different day; the message can claim a fix the
diff does not contain; it costs seconds and a GPU; and when the model is
down the change stops at STAGE. Measured on 2026-09-08: 7.1s cold, 0.3-1.5s
warm, and one BLIND ruling when the configured model did not exist.

A law costs nothing, answers in nanoseconds, gives the same change the same
message every time, and can only be BLIND when git itself fails. What it
gives up is eloquence: a mechanical subject describes what changed and never
explains why. The author's hint carries the why. That trade is the point.

## The observation byte

    bit  name       meaning (measurable, none an opinion)
      0  INVERSE    the change's patch, reversed, is byte-identical to the
                    patch of one of the last 20 commits (index lines ignored)
      1  BLANK      the diff has hunks, but none survive `-w --ignore-blank-
                    lines`, and no untracked file has a non-blank line
      2  TESTSONLY  every changed path is a test path: under tests/, test/,
                    __tests__/, spec/; or named test_*.py, *_test.py,
                    *_test.go, *.test.*, *.spec.*, *Test.java, *Tests.cs,
                    conftest.py
      3  DOCSONLY   every changed path is documentation: *.md, *.rst, *.txt,
                    *.adoc, under docs/, or README*, CHANGELOG*, LICENSE*
      4  DEPSONLY   every changed path is a manifest, lockfile, build or CI
                    file: pyproject.toml, setup.*, requirements*.txt,
                    package.json, *lock*, Cargo.*, go.mod, go.sum, Makefile,
                    CMakeLists.txt, Dockerfile, *.gradle, pom.xml, Gemfile*,
                    tox.ini, .github/workflows/*
      5  NEWDEF     in a CODE path (one in none of the three classes above)
                    an added line has definition shape (def, class, function,
                    fn, func, struct, enum, interface, type X =, column-0
                    const) and its name occurs in no removed definition line
      6  GUARD      in a CODE path an added line has guard shape (raise,
                    throw, assert, panic(, return err, if ... is None,
                    if (!..., == null, errors.New) and lies inside a
                    definition that existed before this change, not inside
                    one this change adds
      7  FOCUSED    the CODE paths number 1 to 3 and share one top-level
                    directory (or all sit at the root); the scope is that
                    directory, or the single file's stem

The body keeps TESTSONLY, DOCSONLY and DEPSONLY disjoint by classifying each
path in that fixed order, directory before basename. A path is CODE when it
is in none of the three. NEWDEF, GUARD and FOCUSED are measured over CODE
paths only, so a new test function never reads as a feature and a README
never has a scope.

Fail closed: a measurement that cannot complete leaves its bit clear. The
law then says less, never more. If git itself fails the body reports the
eyes as BLIND and the SHIP law rules STAGE, exactly as with the model.

## The structural requirement: shape before content, focus before diagnosis

INVERSE, BLANK, TESTSONLY, DOCSONLY and DEPSONLY are SHAPE claims: each is
a statement about the whole diff or every changed path, and they are
mutually exclusive on any byte the body can produce. NEWDEF and GUARD are
CONTENT claims: statements about particular lines. FOCUSED is a GATE.

    R1  Shape outranks content.  A change that is entirely tests, docs,
        dependencies, whitespace, or an undo is described as that, whatever
        definitions or guards it also contains.  Among shapes the order is
        INVERSE, BLANK, TESTSONLY, DOCSONLY, DEPSONLY: an undo of a
        reformat is a revert; a reformat of tests is style.
    R2  No diagnosis without focus.  feat and fix are claims about what a
        change DOES, and a diffuse change (FOCUSED clear) does many things.
        Such a change gets plain, whatever NEWDEF and GUARD say.  "feat:
        add helper" over 40 files is a lie by omission.
    R3  feat outranks fix.  A new definition that contains a guard is a
        feature with validation, not a repair.
    R4  Silence is the floor.  With no shape bit and no gated content claim
        the kind is plain.  The law never invents a claim: a small edit with
        no new definition and no guard is "update billing.py", never "fix".
    R5  Monotone.  For every input x and every bit b, kind(x|b) <= kind(x).
        More evidence never yields a vaguer message.
    R6  Total, deterministic, branchless, no data-dependent loops, no
        tables.  Bytes the body cannot produce (two shape bits at once) are
        ruled by the same ladder, never special-cased.  Verifiable
        exhaustively over all 256 inputs.

## The counts, derived before synthesis

The shape ladder halves the space at each rung and the gated content claims
share what is left:

    kind 0  revert  128   INVERSE
    kind 1  style    64   BLANK, not INVERSE
    kind 2  test     32
    kind 3  docs     16
    kind 4  build     8
    kind 5  feat      2   no shape; NEWDEF and FOCUSED; GUARD free
    kind 6  fix       1   no shape; GUARD and FOCUSED, not NEWDEF
    kind 7  plain     5   no shape; not (NEWDEF and FOCUSED), not (GUARD and FOCUSED)

A kernel that always says plain passes R2, R4 and R5 and is rejected by the
counts.  So is one that says feat on any diffuse change.

## The situations this law must settle

The first is measured; the rest are the canonical shapes and should be
replaced by recorded bytes from the first runs.

1. The billing change, 2026-09-08 (the SHIP law's first real push).
   billing.py gained a `raise` inside the existing price_after_discount and
   a new `total`; tests/test_billing.py gained two tests.  CODE paths:
   billing.py only.
   byte 0xE0  (NEWDEF, GUARD, FOCUSED)
   REQUIRED: feat.  Rendered: `feat(billing): add total`, with the guard
   in the body.  The model wrote "Validate discount rate and add total
   helper"; the law's subject is shorter and claims nothing it did not
   measure.

2. Tests only.  Two new test functions, nothing else.
   byte 0xA4  (TESTSONLY, NEWDEF, FOCUSED)
   REQUIRED: test, not feat.  New test functions are not features.

3. The reformat.  `black .` over 30 files, no token changed.
   byte 0x02  (BLANK)
   REQUIRED: style.  Also with FOCUSED (0x82): style.

4. The undo.  The billing change reverted by hand; the reversed patch
   equals the recorded commit.
   byte 0x81  (INVERSE, FOCUSED)
   REQUIRED: revert.  Rendered: `revert: <subject of that commit>` and a
   body line naming its sha.

5. The lockfile bump.  package-lock.json alone.
   byte 0x10  (DEPSONLY)
   REQUIRED: build.

6. The guard.  One `raise` added inside one existing function, one file.
   byte 0xC0  (GUARD, FOCUSED)
   REQUIRED: fix.  Rendered: `fix(billing): guard price_after_discount`.

7. The migration.  40 files across 6 packages: new definitions, new
   guards, deletions.
   byte 0x60  (NEWDEF, GUARD, not FOCUSED)
   REQUIRED: plain.  Rendered from measurement: `update 40 files across 6
   packages`.  No feat, no fix.

8. The tweak, and nothing at all.  A constant changed in one file.
   bytes 0x80 and 0x00
   REQUIRED: plain.  "update billing.py", never "fix".

9. The impossible byte.  TESTSONLY and DOCSONLY both set (0x0C).
   REQUIRED: test, by the ladder.  The law is total and does not know
   which bytes the body can produce.

## Deliverables

- `say.c`: the kernel, same shape as `ship.c`: lanes folded, one EMIT,
  kind from the low bit.  No branch, no compare, no select, no load;
  report the `objdump` counts.
- A one-paragraph derivation of why R1-R4 hold structurally, from the
  ladder and the gate, not by case analysis.
- An independent oracle written branchy (`if`/`else`, sharing no
  expression with the kernel) and an exhaustive self-check over all 256
  inputs asserting R1-R5, the 128/64/32/16/8/2/1/5 counts, and the nine
  situations above.

Encode no word, no path, no extension, no language.  What counts as a test
path, a definition shape or a guard shape lives in the MEASUREMENT.  The
law reads the SITUATION of the change, never its content.

## A note on what this law does NOT decide

- The words.  The nouns in the subject are measured: definition names,
  paths, the scope directory, the inverted commit's subject.  The verb is
  measured too: add when only lines were added, remove when only removed,
  update otherwise.  The body clips the subject to 72 characters at a word
  boundary, so the SHIP law's BLIND can only fire on a failed measurement.
- The why.  A mechanical message never explains motive.  The author's hint,
  when given, is the phrase, verbatim, after the law's type.
- The body of the message.  One bullet per changed path with its line
  counts and the definitions it added or removed, from measurement.
- How far the change travels.  That is the SHIP law's, unchanged.  This law
  only makes the eyes deterministic, free, and never absent.
