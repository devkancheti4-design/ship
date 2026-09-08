"""The SHIP law: how far may ONE working-tree change travel?

    3 PUSH    stage, commit, push
    2 COMMIT  stage, commit; stop before the network
    1 STAGE   stage and write the message file; stop before history
    0 NONE    write nothing, not even the index

The three lane expressions below are vendored verbatim from ship.c in this
directory, which was authored by search.  tests/test_law.py checks that they
are byte-identical to the C, and selfcheck() re-derives the law against a
branchy oracle over all 256 inputs, exactly as ship.c's main() does.

Nothing in this file decides anything about git.  It reads a byte.
"""
from __future__ import annotations

DIRTY, SECRET, CONFLICT, BULK, BLIND, RED, PROTECTED, FORWARD = (1 << i for i in range(8))

NAMES = {
    DIRTY: "DIRTY", SECRET: "SECRET", CONFLICT: "CONFLICT", BULK: "BULK",
    BLIND: "BLIND", RED: "RED", PROTECTED: "PROTECTED", FORWARD: "FORWARD",
}
ORDER = (DIRTY, SECRET, CONFLICT, BULK, BLIND, RED, PROTECTED, FORWARD)

GATES = DIRTY | FORWARD                       # set only by a successful measurement
HAZARDS = SECRET | CONFLICT | BULK | BLIND | RED | PROTECTED   # set on finding OR on failed measurement
VETO = SECRET | CONFLICT | BULK

NONE, STAGE, COMMIT, PUSH = 0, 1, 2, 3
ACTS = ("NONE", "STAGE", "COMMIT", "PUSH")

# ---- the three authored tier lanes (verbatim from ship.c) ----
def STOP(x: int) -> int:
    return (((x + 14) >> 4) - ((x - 1) >> 4))            # -> mask bit 0


def EYES(x: int) -> int:
    return ((1 & (x >> 4)) + (1 & (x >> 4)))              # -> mask bit 1


def NET(x: int) -> int:
    return ((1 - (4 & (x >> 5))) + (3 | ((x + 96) >> 6)))  # -> mask bit 2


def EMIT(m: int) -> int:
    return m & (-m)


FLOOR = 8                                                  # nothing objected -> PUSH


def ship(obs: int) -> int:
    """The law.  One byte in, one act out.  Tier order IS act order."""
    mask = STOP(obs) + EYES(obs) + NET(obs) + FLOOR
    return EMIT(mask).bit_length() - 1                     # ctz


# ---- consequences of R5 (monotone), used by the body to know when to stop measuring ----
def bounds(byte: int, unmeasured: int) -> tuple[int, int]:
    """Least and greatest act over every completion of the unmeasured bits.

    By R5 a hazard never moves a change further and a gate never moves it
    back, so the extremes sit at 'every open hazard set, every open gate
    clear' and the reverse.  When low == high the ruling no longer depends on
    anything still unmeasured.
    """
    low = ship((byte | (unmeasured & HAZARDS)) & ~(unmeasured & GATES))
    high = ship((byte & ~(unmeasured & HAZARDS)) | (unmeasured & GATES))
    return low, high


def depends(byte: int, unmeasured: int, bit: int) -> bool:
    """Would measuring `bit` change what the law can still rule?"""
    rest = unmeasured & ~bit
    return bounds(byte & ~bit, rest) != bounds(byte | bit, rest)


def describe(byte: int, measured: int = 0xFF) -> str:
    names = [NAMES[b] for b in ORDER if (byte & measured) & b]
    return " ".join(names) if names else "(no bit set)"


# ============ independent oracle: branchy, shares no expression ============
def oracle(x: int) -> int:
    dirty = (x >> 0) & 1
    secret = (x >> 1) & 1
    conflict = (x >> 2) & 1
    bulk = (x >> 3) & 1
    blind = (x >> 4) & 1
    red = (x >> 5) & 1
    protectd = (x >> 6) & 1
    forward = (x >> 7) & 1
    if not dirty:
        return 0
    if secret:
        return 0
    if conflict:
        return 0
    if bulk:
        return 0
    if blind:
        return 1
    if red:
        return 2
    if protectd:
        return 2
    if not forward:
        return 2
    return 3


SITUATIONS = (
    (0x83, 0), (0x85, 0), (0x89, 0),           # leaked key, half-finished merge, build dir
    (0x91, 1), (0xD1, 1), (0xB1, 1),           # the silent model, alone and with net hazards
    (0xC1, 2), (0x01, 2), (0xA1, 2),           # straight to main, diverged/airplane, red check
    (0x00, 0), (0x80, 0), (0x81, 3),           # clean tree twice, the one happy byte
)


def selfcheck() -> dict:
    """Re-derive the law over all 256 inputs.  Every value must be zero except
    the partition, which must be exactly 1/7/8/240."""
    further = refused = r1 = r2 = r3 = r4 = r5 = 0
    n = [0, 0, 0, 0]
    for x in range(256):
        k, o = ship(x), oracle(x)
        further += k > o
        refused += k < o
        n[k] += 1
        if (x & VETO) and k != 0:
            r1 += 1
        if not (x & 1) and k != 0:
            r2 += 1
        if (x & 16) and not (x & VETO) and (x & 1) and k > 1:
            r3 += 1
        if ((x & 32) or (x & 64) or not (x & 128)) and not (x & VETO) and (x & 1) and not (x & 16) and k > 2:
            r4 += 1
    for x in range(256):
        for h in (2, 4, 8, 16, 32, 64):
            if not (x & h) and ship(x | h) > ship(x):
                r5 += 1
        for g in (1, 128):
            if not (x & g) and ship(x | g) < ship(x):
                r5 += 1
    counts_ok = (n[3], n[2], n[1], n[0]) == (1, 7, 8, 240)
    incidents = sum(ship(b) != w for b, w in SITUATIONS)
    result = {
        "travelled further than allowed": further,
        "refused when it must not": refused,
        "R1 veto absolute": r1,
        "R2 DIRTY gates everything": r2,
        "R3 no history without eyes": r3,
        "R4 no network without ff/green": r4,
        "R5 monotone": r5,
        "partition": {"PUSH": n[3], "COMMIT": n[2], "STAGE": n[1], "NONE": n[0]},
        "counts 1/7/8/240": "exact" if counts_ok else "MISMATCH",
        "the eight situations": incidents,
    }
    result["violations"] = further + refused + r1 + r2 + r3 + r4 + r5 + (not counts_ok) + incidents
    return result


def format_selfcheck(r: dict) -> str:
    lines = []
    for key in ("travelled further than allowed", "refused when it must not", "R1 veto absolute",
                "R2 DIRTY gates everything", "R3 no history without eyes",
                "R4 no network without ff/green", "R5 monotone"):
        lines.append(f"  {key:<33}{r[key]}")
    p = r["partition"]
    lines.append(f"  partition  PUSH {p['PUSH']}  COMMIT {p['COMMIT']}  STAGE {p['STAGE']}  NONE {p['NONE']}")
    lines.append(f"  {'counts 1/7/8/240':<33}{r['counts 1/7/8/240']}")
    lines.append(f"  {'the eight situations':<33}{r['the eight situations']} violations")
    lines.append("")
    lines.append(f"  TOTAL  256 inputs  {r['violations']} violations")
    return "\n".join(lines)
