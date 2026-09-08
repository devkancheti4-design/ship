"""Generate the old-way-vs-ship tape. Usage: make_compare_tape.py DEMO_DIR > old-vs-new.tape
Both halves run for real against scratch bare remotes created in DEMO_DIR."""
import sys
demo = sys.argv[1]
shipbin = "/Users/kanchetidevieswar/neo/ship/.venv/bin"
setup = (f"setopt interactive_comments && export PATH={shipbin}:$PATH && rm -rf {demo} && mkdir -p {demo} && cd {demo} "
         "&& git init -q --bare old.git && git init -q --bare new.git && mkdir app-old app-new "
         "&& printf 'def greet(name):\\n    return f\"hello {name}\"\\n' > app-old/app.py && cp app-old/app.py app-new/app.py "
         "&& cd app-old && clear")
print(f'''# The same folder, pushed twice: the old way, then with ship. Both run for real.
Output old-vs-new.gif
Output old-vs-new.mp4
Set Shell zsh
Set Width 1240
Set Height 800
Set FontSize 24
Set LineHeight 1.25
Set Padding 30
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set CursorBlink false

Hide
Type `{setup}` Enter
Sleep 1s
Show

Type "# the old way: 5 commands, and a message you write yourself" Enter
Sleep 1.5s
Type "git init -b work" Enter
Sleep 1s
Type "git remote add origin ../old.git" Enter
Sleep 1s
Type "git add -A" Enter
Sleep 1s
Type `git commit -m "feat(app): add greet"` Enter
Sleep 1.5s
Type "git push -u origin work" Enter
Sleep 3.5s
Ctrl+L

Type "cd ../app-new" Enter
Type "# with ship: one line" Enter
Sleep 1.5s
Type "ship ../new.git" Enter
Sleep 6s
Type "# 5 commands and a message you write   vs   1 line, 0 tokens" Enter
Sleep 4s
''')
