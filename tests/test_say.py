"""The SAY law is re-derived, never trusted: exhaustive in Python and in the vendored C."""
import os
import re
import shutil
import subprocess

import pytest

from ship import say
from ship.say import COUNTS, SITUATIONS, oracle
from ship.say import say as kind

SRC = os.path.join(os.path.dirname(say.__file__), "say.c")


def test_selfcheck_has_zero_violations():
    r = say.selfcheck()
    assert r["violations"] == 0, r


def test_partition_is_exactly_128_64_32_16_8_2_1_5():
    assert tuple(sum(kind(x) == k for x in range(256)) for k in range(8)) == COUNTS
    assert [x for x in range(256) if kind(x) == 6] == [0xC0]


def test_matches_branchy_oracle_on_every_input():
    assert [kind(x) for x in range(256)] == [oracle(x) for x in range(256)]


def test_r5_monotone_every_bit():
    for x in range(256):
        for b in range(8):
            assert kind(x | 1 << b) <= kind(x)


@pytest.mark.parametrize("byte,want", SITUATIONS)
def test_the_nine_situations(byte, want):
    assert kind(byte) == want


def test_diffuse_change_never_claims_feat_or_fix():
    for x in range(128):                   # FOCUSED clear
        assert kind(x) not in (5, 6)


def test_python_lanes_are_verbatim_from_say_c():
    c = open(SRC).read()
    py = open(say.__file__).read()
    lanes = re.findall(r"static inline int32_t (SHAPE|CONTENT|FOCUS)\s*\(int32_t x\) \{ return (\(.*?\)); \}", c)
    assert {n for n, _ in lanes} == {"SHAPE", "CONTENT", "FOCUS"}
    for name, expr in lanes:
        assert expr in py, f"{name} lane in say.py differs from say.c: {expr}"
    assert "#define FLOOR 128" in c and "FLOOR = 128" in py and "0 - FOCUS(obs)" in py


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler")
def test_vendored_c_kernel_passes_its_own_selfcheck(tmp_path):
    exe = tmp_path / "say_check"
    subprocess.run(["cc", "-O2", SRC, "-o", str(exe)], check=True)
    p = subprocess.run([str(exe)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout
    assert "TOTAL  256 inputs  0 violations" in p.stdout
    assert "partition 128/64/32/16/8/2/1/5" in p.stdout
