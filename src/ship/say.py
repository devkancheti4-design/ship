"""The SAY law: what KIND of claim may ONE change's commit subject make?

    0 revert  1 style  2 test  3 docs  4 build  5 feat  6 fix  7 plain

The three lane expressions are vendored verbatim from say.c in this directory,
which was authored by search.  tests/test_say.py checks they are byte-identical
to the C, and selfcheck() re-derives the law against a branchy oracle over all
256 inputs, as say.c's main() does.  Nothing here reads a diff: it reads a byte.
"""
from __future__ import annotations

INVERSE, BLANK, TESTSONLY, DOCSONLY, DEPSONLY, NEWDEF, GUARD, FOCUSED = (1 << i for i in range(8))
NAMES = {
    INVERSE: "INVERSE", BLANK: "BLANK", TESTSONLY: "TESTSONLY", DOCSONLY: "DOCSONLY",
    DEPSONLY: "DEPSONLY", NEWDEF: "NEWDEF", GUARD: "GUARD", FOCUSED: "FOCUSED",
}
ORDER = (INVERSE, BLANK, TESTSONLY, DOCSONLY, DEPSONLY, NEWDEF, GUARD, FOCUSED)
SHAPE_BITS = INVERSE | BLANK | TESTSONLY | DOCSONLY | DEPSONLY

REVERT, STYLE, TEST, DOCS, BUILD, FEAT, FIX, PLAIN = range(8)
KINDS = ("revert", "style", "test", "docs", "build", "feat", "fix", "plain")


# ---- the three authored lanes (verbatim from say.c) ----
def SHAPE(x: int) -> int:
    return (x & 31)                              # -> mask bits 0..4


def CONTENT(x: int) -> int:
    return ((x & 32) + (x & 64))                 # -> mask bits 5..6


def FOCUS(x: int) -> int:
    return (x >> 7)                              # the gate


def EMIT(m: int) -> int:
    return m & (-m)


FLOOR = 128                                      # no claim survives -> plain


def say(obs: int) -> int:
    """The law.  One byte in, one kind out.  Rung order IS kind order."""
    gf = 0 - FOCUS(obs)                          # all-ones only when FOCUSED
    mask = SHAPE(obs) + (gf & CONTENT(obs)) + FLOOR
    return EMIT(mask).bit_length() - 1           # ctz


def describe(byte: int) -> str:
    names = [NAMES[b] for b in ORDER if byte & b]
    return " ".join(names) if names else "(no bit set)"


# ========== independent oracle: branchy, shares no expression ==========
def oracle(x: int) -> int:
    inverse, blank, tests = (x >> 0) & 1, (x >> 1) & 1, (x >> 2) & 1
    docs, deps, newdef = (x >> 3) & 1, (x >> 4) & 1, (x >> 5) & 1
    guard, focused = (x >> 6) & 1, (x >> 7) & 1
    if inverse:
        return 0
    if blank:
        return 1
    if tests:
        return 2
    if docs:
        return 3
    if deps:
        return 4
    if focused and newdef:
        return 5
    if focused and guard:
        return 6
    return 7


SITUATIONS = (
    (0xE0, 5), (0xA4, 2), (0x02, 1), (0x82, 1), (0x81, 0), (0x10, 4),
    (0xC0, 6), (0x60, 7), (0x80, 7), (0x00, 7), (0x0C, 2),
)
COUNTS = (128, 64, 32, 16, 8, 2, 1, 5)


def selfcheck() -> dict:
    vaguer = bolder = r1 = r2 = r3 = r4 = r5 = 0
    n = [0] * 8
    for x in range(256):
        k, o = say(x), oracle(x)
        vaguer += k > o
        bolder += k < o
        n[k] += 1
        if (x & SHAPE_BITS) and k > 4:
            r1 += 1
        if not (x >> 7) & 1 and k in (5, 6):
            r2 += 1
        if not (x & SHAPE_BITS) and (x >> 7) & 1 and (x >> 5) & 1 and k != 5:
            r3 += 1
        if not (x & SHAPE_BITS) and not ((x >> 7) & 1 and ((x >> 5) & 1 or (x >> 6) & 1)) and k != 7:
            r4 += 1
    for x in range(256):
        for b in range(8):
            if not (x >> b) & 1 and say(x | (1 << b)) > say(x):
                r5 += 1
    counts_ok = tuple(n) == COUNTS
    incidents = sum(say(b) != w for b, w in SITUATIONS)
    r = {
        "said something vaguer than allowed": vaguer,
        "claimed more than the evidence": bolder,
        "R1 shape outranks content": r1,
        "R2 no diagnosis without focus": r2,
        "R3 feat outranks fix": r3,
        "R4 silence is the floor": r4,
        "R5 monotone": r5,
        "partition": dict(zip(KINDS, n)),
        "counts 128/64/32/16/8/2/1/5": "exact" if counts_ok else "MISMATCH",
        "the nine situations": incidents,
    }
    r["violations"] = vaguer + bolder + r1 + r2 + r3 + r4 + r5 + (not counts_ok) + incidents
    return r


def format_selfcheck(r: dict) -> str:
    lines = []
    for key in ("said something vaguer than allowed", "claimed more than the evidence",
                "R1 shape outranks content", "R2 no diagnosis without focus", "R3 feat outranks fix",
                "R4 silence is the floor", "R5 monotone"):
        lines.append(f"  {key:<37}{r[key]}")
    lines.append("  partition " + "/".join(str(r["partition"][k]) for k in KINDS))
    lines.append(f"  {'counts 128/64/32/16/8/2/1/5':<37}{r['counts 128/64/32/16/8/2/1/5']}")
    lines.append(f"  {'the nine situations':<37}{r['the nine situations']} violations")
    lines.append("")
    lines.append(f"  TOTAL  256 inputs  {r['violations']} violations")
    return "\n".join(lines)
