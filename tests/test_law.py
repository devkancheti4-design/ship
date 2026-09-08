"""The law is re-derived, never trusted: exhaustive over all 256 inputs, in Python and in the vendored C."""
import itertools
import os
import re
import shutil
import subprocess

import pytest

from ship import law
from ship.law import (BLIND, BULK, CONFLICT, DIRTY, FORWARD, GATES, HAZARDS, PROTECTED, RED, SECRET,
                      SITUATIONS, bounds, depends, oracle, ship)

SRC = os.path.join(os.path.dirname(law.__file__), "ship.c")


def test_selfcheck_has_zero_violations():
    r = law.selfcheck()
    assert r["violations"] == 0, r


def test_partition_is_exactly_1_7_8_240():
    counts = [sum(ship(x) == a for x in range(256)) for a in range(4)]
    assert counts == [240, 8, 7, 1]
    assert [x for x in range(256) if ship(x) == 3] == [0x81]


def test_matches_branchy_oracle_on_every_input():
    assert [ship(x) for x in range(256)] == [oracle(x) for x in range(256)]


def test_r5_monotone():
    for x in range(256):
        for h in (SECRET, CONFLICT, BULK, BLIND, RED, PROTECTED):
            assert ship(x | h) <= ship(x)
        for g in (DIRTY, FORWARD):
            assert ship(x | g) >= ship(x)


@pytest.mark.parametrize("byte,want", SITUATIONS)
def test_the_eight_situations(byte, want):
    assert ship(byte) == want


def test_bounds_bracket_every_completion():
    """low/high from R5 must contain the act of every completion of the open bits."""
    masks = [sum(c) for k in range(4) for c in itertools.combinations([1 << i for i in range(8)], k)]
    for byte in range(256):
        for open_ in masks:
            base = byte & ~open_
            low, high = bounds(base, open_)
            acts = set()
            open_bits = [b for b in (1 << i for i in range(8)) if open_ & b]
            for fill in range(1 << len(open_bits)):
                x = base
                for i, b in enumerate(open_bits):
                    if fill >> i & 1:
                        x |= b
                acts.add(ship(x))
            assert min(acts) == low and max(acts) == high, (hex(byte), hex(open_))


def test_depends_is_exact_when_one_bit_is_open():
    for byte in range(256):
        for b in (1 << i for i in range(8)):
            base = byte & ~b
            assert depends(base, b, b) == (ship(base) != ship(base | b))


def test_gates_and_hazards_partition_the_byte():
    assert GATES | HAZARDS == 0xFF and GATES & HAZARDS == 0


def test_python_lanes_are_verbatim_from_ship_c():
    c = open(SRC).read()
    py = open(law.__file__).read()
    lanes = re.findall(r"static inline int32_t (STOP|EYES|NET) ?\(int32_t x\) \{ return (\(.*?\)); \}", c)
    assert {n for n, _ in lanes} == {"STOP", "EYES", "NET"}
    for name, expr in lanes:
        assert expr in py, f"{name} lane in law.py differs from ship.c: {expr}"
    assert "m & (-m)" in py and "#define FLOOR 8" in c and "FLOOR = 8" in py


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler")
def test_vendored_c_kernel_passes_its_own_selfcheck(tmp_path):
    exe = tmp_path / "ship_check"
    subprocess.run(["cc", "-O2", SRC, "-o", str(exe)], check=True)
    p = subprocess.run([str(exe)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout
    assert "TOTAL  256 inputs  0 violations" in p.stdout
    assert "PUSH 1  COMMIT 7  STAGE 8  NONE 240" in p.stdout
