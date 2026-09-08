"""The mechanical eyes: every bit measured in a real repository, every message well-formed."""
import pytest

from conftest import sh
from ship import measure as M
from ship import mechanical as X
from ship.say import (BLANK, BUILD, DEPSONLY, DOCS, DOCSONLY, FEAT, FIX, FOCUSED, GUARD, INVERSE, NEWDEF, PLAIN,
                      REVERT, STYLE, TEST, TESTSONLY)

BILLING_BEFORE = "def price_after_discount(p, rate):\n    return p * (1 - rate)\n"
BILLING_AFTER = (
    "def price_after_discount(p, rate):\n"
    "    if not 0 <= rate <= 1:\n"
    "        raise ValueError(f\"rate must be in [0, 1], got {rate}\")\n"
    "    return p * (1 - rate)\n\n\n"
    "def total(prices, rate=0.0):\n"
    "    return sum(price_after_discount(p, rate) for p in prices)\n"
)
TESTS_BEFORE = "from billing import price_after_discount\n\n\ndef test_discount():\n    assert price_after_discount(100, 0.25) == 75\n"
TESTS_AFTER = TESTS_BEFORE + (
    "\n\ndef test_rejects_bad_rate():\n    import pytest\n    with pytest.raises(ValueError):\n"
    "        price_after_discount(100, 1.5)\n\n\ndef test_total():\n    from billing import total\n"
    "    assert total([100, 50], 0.1) == 135\n"
)


def commit(repo, files, msg="setup"):
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    sh(repo, "add", "-A")
    sh(repo, "commit", "-q", "-m", msg)


def eyes(repo, hint=""):
    ch = M.collect(str(repo))
    facts = X.observe(ch)
    text, detail = X.summarize(ch, hint)
    assert not M.well_formed(text)[0], text          # every rendered message passes the SHIP law's BLIND check
    return facts, text, detail


@pytest.fixture
def billing(repo):
    commit(repo, {"billing.py": BILLING_BEFORE, "tests/test_billing.py": TESTS_BEFORE}, "billing")
    return repo


# ---- classification and line shapes
@pytest.mark.parametrize("path,cls", [
    ("tests/test_x.py", "test"), ("pkg/foo_test.go", "test"), ("src/app.spec.ts", "test"), ("conftest.py", "test"),
    ("tests/README.md", "test"), ("FooTest.java", "test"), ("spec/thing_spec.rb", "test"),
    ("README.md", "docs"), ("docs/guide.rst", "docs"), ("CHANGELOG", "docs"), ("notes.txt", "docs"), ("LICENSE", "docs"),
    ("pyproject.toml", "deps"), ("package-lock.json", "deps"), ("requirements-dev.txt", "deps"), ("Makefile", "deps"),
    (".github/workflows/ci.yml", "deps"), ("Dockerfile", "deps"), ("app/build.gradle", "deps"), ("docs/Makefile", "deps"),
    ("billing.py", "code"), ("src/ship/law.py", "code"), ("main.go", "code"), ("lib.rs", "code"), ("index.html", "code"),
])
def test_classify(path, cls):
    assert X.classify(path) == cls


@pytest.mark.parametrize("line,name", [
    ("def total(prices):", "total"), ("    def inner(self):", "inner"), ("async def fetch():", "fetch"),
    ("class Foo(Base):", "Foo"), ("export default function main() {", "main"), ("function* gen() {", "gen"),
    ("pub fn parse(s: &str) -> T {", "parse"), ("pub(crate) struct Node {", "Node"), ("func (s *Server) Start() {", "Start"),
    ("type Alias = string", "Alias"), ("const handler = (req) => {", "handler"), ("    public static void main(String[] a) {", "main"),
    ("int main(void) {", "main"), ("static void helper(int a)", "helper"),
    ("if (x) {", None), ("else if (y) {", None), ("    return foo(x)", None), ("x = 1", None), ("    total = 0", None),
    ("#define FOO(x) (x)", None), ("    print(value)", None),
])
def test_def_name(line, name):
    assert X.def_name(line) == name


@pytest.mark.parametrize("line,guard", [
    ("        raise ValueError('x')", True), ("    throw new Error('x');", True), ("    assert x > 0", True),
    ("    panic(\"bad\")", True), ("        return err", True), ("    if (!ok) {", True), ("    if value is None:", True),
    ("    if (x == null) return;", True), ("    return errors.New(\"no\")", True),
    ("    return p * (1 - rate)", False), ("    total += 1", False), ("    if x > 3:", False),
])
def test_is_guard(line, guard):
    assert X.is_guard(line) is guard


# ---- the situations, built for real
def test_situation_1_the_billing_change_is_feat(billing):
    (billing / "billing.py").write_text(BILLING_AFTER)
    (billing / "tests/test_billing.py").write_text(TESTS_AFTER)
    f, text, detail = eyes(billing)
    assert f.byte == 0xE0 and f.kind == FEAT
    assert text.splitlines()[0] == "feat(billing): add total"
    assert f.guard_defs == ["price_after_discount"] and f.new_defs == ["total"]
    assert "guards price_after_discount" in text and "defines test_rejects_bad_rate, test_total" in text
    assert detail.startswith("SAY law feat 0xE0 NEWDEF GUARD FOCUSED")


def test_situation_2_tests_only_is_test_not_feat(billing):
    (billing / "tests/test_billing.py").write_text(TESTS_AFTER)
    f, text, _ = eyes(billing)
    assert f.byte & TESTSONLY and f.kind == TEST
    assert text.splitlines()[0] == "test: add test_rejects_bad_rate, test_total"


def test_situation_3_reformat_is_style(billing):
    (billing / "billing.py").write_text("def price_after_discount(p, rate):\n        return p * (1 - rate)\n")
    f, text, _ = eyes(billing)
    assert f.byte & BLANK and f.kind == STYLE and text.splitlines()[0] == "style: reformat billing.py"


def test_situation_4_the_undo_is_revert(billing):
    (billing / "billing.py").write_text(BILLING_AFTER)
    sh(billing, "add", "-A")
    sh(billing, "commit", "-q", "-m", "Add total and a rate guard")
    sha = sh(billing, "rev-parse", "HEAD").strip()
    (billing / "billing.py").write_text(BILLING_BEFORE)            # undone by hand
    f, text, _ = eyes(billing)
    assert f.byte & INVERSE and f.kind == REVERT and f.inverse[0] == sha
    assert text.splitlines()[0] == "revert: Add total and a rate guard"
    assert f"This reverts commit {sha}." in text


def test_situation_5_lockfile_is_build(repo):
    (repo / "package-lock.json").write_text("{}\n")
    f, text, _ = eyes(repo)
    assert f.byte == DEPSONLY and f.kind == BUILD and text.splitlines()[0] == "build: add package-lock.json"


def test_situation_6_the_guard_is_fix(billing):
    (billing / "billing.py").write_text(
        "def price_after_discount(p, rate):\n    if not 0 <= rate <= 1:\n        raise ValueError(rate)\n    return p * (1 - rate)\n")
    f, text, _ = eyes(billing)
    assert f.byte == GUARD | FOCUSED and f.kind == FIX
    assert text.splitlines()[0] == "fix(billing): guard price_after_discount"


def test_situation_7_the_migration_is_plain(repo):
    for d in ("alpha", "beta", "gamma", "delta"):
        (repo / d).mkdir()
        (repo / d / "mod.py").write_text(f"def {d}_new():\n    if x is None:\n        raise ValueError\n")
    f, text, _ = eyes(repo)
    assert f.byte == NEWDEF and f.kind == PLAIN            # NEWDEF without FOCUSED, guards inside new defs
    assert text.splitlines()[0] == "add 4 files across 4 directories"


def test_situation_8_the_tweak_is_plain(billing):
    (billing / "billing.py").write_text(BILLING_BEFORE.replace("1 - rate", "1.0 - rate"))
    f, text, _ = eyes(billing)
    assert f.byte == FOCUSED and f.kind == PLAIN and text.splitlines()[0] == "update billing.py"


# ---- scoping rules the prompt insists on
def test_new_test_function_beside_a_code_tweak_is_not_feat(billing):
    (billing / "billing.py").write_text(BILLING_BEFORE.replace("1 - rate", "1.0 - rate"))
    (billing / "tests/test_billing.py").write_text(TESTS_AFTER)
    f, text, _ = eyes(billing)
    assert not f.byte & NEWDEF and f.kind == PLAIN
    assert text.splitlines()[0] == "update billing.py, tests/test_billing.py"


def test_guard_inside_a_new_definition_is_feat_not_fix(billing):
    (billing / "billing.py").write_text(BILLING_BEFORE + "\n\ndef checked(x):\n    if x is None:\n        raise ValueError\n    return x\n")
    f, text, _ = eyes(billing)
    assert f.byte == NEWDEF | FOCUSED and f.kind == FEAT and f.guard_defs == []


def test_reindenting_an_existing_guard_is_not_a_new_guard(billing):
    commit(billing, {"billing.py": BILLING_AFTER}, "with guard")
    (billing / "billing.py").write_text(BILLING_AFTER.replace("    ", "        "))
    f, text, _ = eyes(billing)
    assert f.byte == BLANK | FOCUSED and f.kind == STYLE and f.guard_defs == []


def test_moving_a_guard_between_lines_is_not_a_new_guard(billing):
    commit(billing, {"billing.py": BILLING_AFTER}, "with guard")
    moved = BILLING_AFTER.replace("    return p * (1 - rate)\n", "    y = 1\n    return p * (1 - rate)\n")
    (billing / "billing.py").write_text(moved)
    f, _, _ = eyes(billing)
    assert not f.byte & GUARD


def test_guard_in_an_untracked_file_never_counts(repo):
    (repo / "new.py").write_text("def f(x):\n    raise ValueError\n")
    f, _, _ = eyes(repo)
    assert not f.byte & GUARD and f.byte & NEWDEF


def test_scope_is_the_package_directory_when_there_is_one(repo):
    (repo / "src" / "pricing").mkdir(parents=True)
    (repo / "src" / "pricing" / "rules.py").write_text("def thing():\n    return 1\n")
    f, text, _ = eyes(repo)
    assert f.scope == "pricing" and text.splitlines()[0] == "feat(pricing): add thing"


def test_scope_is_the_module_stem_inside_a_generic_directory(repo):
    (repo / "src").mkdir()
    (repo / "src" / "billing.py").write_text("def thing():\n    return 1\n")
    f, text, _ = eyes(repo)
    assert f.scope == "billing" and text.splitlines()[0] == "feat(billing): add thing"


@pytest.mark.parametrize("paths,scope", [
    (["billing.py"], "billing"), (["src/billing.py"], "billing"), (["src/pricing/rules.py"], "pricing"),
    (["src/pricing/__init__.py"], "pricing"), (["src/__init__.py"], ""), (["src/a.py", "src/b.py"], ""),
    (["src/pricing/a.py", "src/pricing/b.py"], "pricing"), (["pkg/mod.py"], ""),
])
def test_scope_of(paths, scope):
    assert X.scope_of(paths) == scope


def test_hint_replaces_the_phrase_not_the_type(billing):
    (billing / "billing.py").write_text(BILLING_AFTER)
    f, text, _ = eyes(billing, hint="validate the discount rate and add a total helper")
    assert text.splitlines()[0] == "feat(billing): validate the discount rate and add a total helper"


def test_hint_on_a_plain_change_is_the_whole_subject(billing):
    (billing / "billing.py").write_text(BILLING_BEFORE.replace("1 - rate", "1.0 - rate"))
    _, text, _ = eyes(billing, hint="use a float literal")
    assert text.splitlines()[0] == "use a float literal"


def test_subject_is_clipped_to_72_at_a_word_boundary(billing):
    (billing / "billing.py").write_text(BILLING_AFTER)
    _, text, _ = eyes(billing, hint="a " * 60)
    s = text.splitlines()[0]
    assert len(s) <= 72 and s.endswith("…") and not s.endswith(" …")


def test_same_change_same_message(billing):
    (billing / "billing.py").write_text(BILLING_AFTER)
    assert eyes(billing)[1] == eyes(billing)[1]


def test_docs_only_and_the_removal_verb(repo):
    commit(repo, {"guide.md": "# guide\n", "notes.md": "# notes\n"}, "two docs")
    (repo / "guide.md").unlink()
    f, text, _ = eyes(repo)
    assert f.kind == DOCS and text.splitlines()[0] == "docs: remove guide.md"


def test_deleting_what_the_last_commit_added_is_a_revert(repo):
    """The fixture's only commit added README.md, so deleting it IS that commit's inverse."""
    (repo / "README.md").unlink()
    f, text, _ = eyes(repo)
    assert f.kind == REVERT and text.splitlines()[0] == "revert: init"


def test_emptying_a_file_is_an_update_not_a_removal(repo):
    (repo / "README.md").write_text("")
    _, text, _ = eyes(repo)
    assert text.splitlines()[0] == "docs: update README.md"


def test_secret_style_lines_are_not_the_eyes_business(billing):
    """The eyes never refuse: SECRET is the SHIP law's, measured elsewhere."""
    (billing / "billing.py").write_text(BILLING_BEFORE + "KEY = 'AKIAIOSFODNN7EXAMPLE'\n")
    _, text, _ = eyes(billing)
    assert text.splitlines()[0] == "update billing.py"
