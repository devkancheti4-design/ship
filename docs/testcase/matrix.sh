#!/bin/bash
# The test matrix for ship on devkancheti4-design/test-case-: every run is real, origin is a scratch bare remote.
export PATH=/Users/kanchetidevieswar/neo/ship/.venv/bin:$PATH
export GIT_TERMINAL_PROMPT=0
T=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/1e1664fd-1962-4d88-8a91-f786fbfbe0b6/scratchpad/testcase
cd $T/clone
TIMEFORMAT='   [wall %Rs]'
run() { echo; echo "### $1"; shift; echo "\$ $*"; time "$@"; echo "   [exit $?]"; }

run "S1 first commit ever: unborn HEAD, on main" ship
git log --oneline -1
run "S2 nothing to record on a clean tree" ship
git checkout -q -b feature
cat > src/billing.py <<'PY'
def price_after_discount(p, rate):
    if not 0 <= rate <= 1:
        raise ValueError(f"rate must be in [0, 1], got {rate}")
    return p * (1 - rate)


def total(prices, rate=0.0):
    return sum(price_after_discount(p, rate) for p in prices)
PY
cat >> tests/test_billing.py <<'PY'


def test_rejects_bad_rate():
    import pytest
    with pytest.raises(ValueError):
        price_after_discount(100, 1.5)


def test_total():
    from billing import total
    assert total([100, 50], 0.1) == 135
PY
run "S3 feature: guard + new total + tests, branch feature not on remote yet" ship
python3 - <<'PY'
s = open("src/billing.py").read()
s = s.replace("def total(prices, rate=0.0):\n", "def total(prices, rate=0.0):\n    if not prices:\n        raise ValueError(\"no prices\")\n")
open("src/billing.py", "w").write(s)
PY
run "S4 a guard inside an existing function" ship
printf '\n\ndef test_zero_rate():\n    assert price_after_discount(10, 0) == 10\n' >> tests/test_billing.py
run "S5 tests only" ship
printf '\nEvery commit message here was written by measurement, not by a model.\n' >> README.md
run "S6 docs only" ship
printf '\n[tool.ship]\nnote = "no configuration is needed; this table exists to change a manifest"\n' >> pyproject.toml
run "S7 manifest only" ship
python3 -c "s=open('src/billing.py').read(); open('src/billing.py','w').write(s.replace('    ', '        '))"
run "S8 reformat only" ship
git checkout -q HEAD~1 -- src/billing.py; git reset -q
run "S9 that reformat undone by hand" ship
for d in alpha beta gamma delta epsilon; do mkdir -p src/$d; printf "def ${d}_new():\n    if x is None:\n        raise ValueError\n    return 1\n" > src/$d/service.py; done
run "S10 diffuse: five new modules in five directories" ship
printf 'AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE\n' > .env; printf '\n# pricing helpers\n' >> src/billing.py
before=$(git status --porcelain | sort | md5)
run "S11 a leaked key beside a real change" ship
after=$(git status --porcelain | sort | md5); echo "   tree identical after refusal: $([ "$before" = "$after" ] && echo yes || echo NO)"; rm .env
run "S12 the same change with the key removed" ship
git checkout -q main; printf '\n# main branch note\n' >> README.md
run "S13 a change on main" ship
git checkout -q feature
cd $T; rm -rf other; git clone -q -b feature scratch.git other; cd other; git config user.email t@x; git config user.name t
printf 'x\n' > elsewhere.txt; git add -A; git commit -q -m "elsewhere"; git push -q origin feature; cd $T/clone
printf '\n# after divergence\n' >> src/billing.py
run "S14 the remote moved ahead (diverged)" ship
git pull -q --rebase origin feature   # the human's job, done by hand
run "S15 after the human rebased: push the pending commits? no: clean tree" ship
printf '\n\ndef test_wrong():\n    from billing import total\n    assert total([1], 0) == 2\n' >> tests/test_billing.py
run "S16 a red test suite" ship
python3 - <<'PY'
s = open("tests/test_billing.py").read(); open("tests/test_billing.py", "w").write(s.replace("== 2\n", "== 1\n"))
PY
run "S17 the suite made green again: the held checkpoints travel" ship
mkdir -p dist; for i in $(seq 1 51); do echo x > dist/f$i.js; done
run "S18 an accidental 51-file build directory" ship
rm -rf dist
printf '\n# one more note\n' >> README.md
run "S19 dry run" ship -n
git checkout -q README.md
echo; echo "=== scratch remote log (origin/feature) ==="; git log --oneline origin/feature
echo "=== local main vs remote ==="; git log --oneline main | head -3; echo "remote main: $(git ls-remote origin main | cut -c1-7)"
echo "=== real GitHub remote, untouched? ==="; git ls-remote https://github.com/devkancheti4-design/test-case-.git > $T/real-remote-after.txt; diff $T/real-remote-before.txt $T/real-remote-after.txt && echo "identical (still empty)"
