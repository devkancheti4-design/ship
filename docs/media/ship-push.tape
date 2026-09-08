# ship: one word, one safely pushed commit. A real terminal, the real tool, a real
# push to a real remote. Every command runs live while recording; nothing is generated.
Output ship-push.mp4
Set Shell zsh
Set Width 1920
Set Height 1080
Set FontSize 28
Set LineHeight 1.25
Set Padding 44
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms
Set CursorBlink false

Hide
Type "setopt interactive_comments && mkdir -p /Users/kanchetidevieswar/neo/demo && cd /Users/kanchetidevieswar/neo/demo && rm -rf test-case- && export PATH=/Users/kanchetidevieswar/neo/ship/.venv/bin:$PATH && clear" Enter
Sleep 1s
Show

# 1 - an empty repository on the remote
Type "git clone https://github.com/devkancheti4-design/test-case-.git test-case-" Enter
Sleep 3s
Type "cd test-case- && git log --oneline 2>&1 | head -1" Enter
Sleep 3s
Type "# ship never pushes main: work on a branch" Enter
Type "git checkout -b feature" Enter
Sleep 2.5s
Ctrl+L

# 2 - two machine-authored laws, re-proved on this machine in under a second
Type "ship selfcheck | grep -E 'law|TOTAL'" Enter
Sleep 5s
Ctrl+L

# 3 - write code, type one word
Set TypingSpeed 22ms
Type `cat > billing.py <<'EOF'` Enter
Type `def price_after_discount(p, rate):` Enter
Type `    return p * (1 - rate)` Enter
Type `EOF` Enter
Type `mkdir tests` Enter
Type `cat > tests/test_billing.py <<'EOF'` Enter
Type `from billing import price_after_discount` Enter
Enter
Type `def test_discount():` Enter
Type `    assert price_after_discount(100, 0.25) == 75` Enter
Type `EOF` Enter
Set TypingSpeed 45ms
Sleep 1s
Type "ship" Enter
Sleep 7s
Ctrl+L

# 4 - a guard inside an existing function: it is a fix, and it says so
Set TypingSpeed 22ms
Type `cat > billing.py <<'EOF'` Enter
Type `def price_after_discount(p, rate):` Enter
Type `    if not 0 <= rate <= 1:` Enter
Type `        raise ValueError(rate)` Enter
Type `    return p * (1 - rate)` Enter
Type `EOF` Enter
Set TypingSpeed 45ms
Sleep 1s
Type "ship" Enter
Sleep 7s
Ctrl+L

# 5 - a leaked key: refused before the index, nothing written
Type `echo 'AWS_KEY=AKIAIOSFODNN7EXAMPLE' > .env` Enter
Sleep 1s
Type "ship" Enter
Sleep 5s
Type "echo exit=$? && git status --short" Enter
Sleep 3.5s
Type "rm .env" Enter
Ctrl+L

# 6 - your words become the subject; the law still names the kind
Set TypingSpeed 22ms
Type `cat >> billing.py <<'EOF'` Enter
Enter
Enter
Type `def total(prices, rate=0.0):` Enter
Type `    return sum(price_after_discount(p, rate) for p in prices)` Enter
Type `EOF` Enter
Set TypingSpeed 45ms
Sleep 1s
Type `ship "add the total helper"` Enter
Sleep 7s
Ctrl+L

# 7 - it is on the remote; main stays a human decision
Type "git log --oneline origin/feature" Enter
Sleep 3.5s
Type "git ls-remote origin feature && git rev-parse HEAD" Enter
Sleep 3.5s
Type "# main stays a human decision: one plain git command" Enter
Type "git push -q origin feature:main && git ls-remote origin" Enter
Sleep 5s

