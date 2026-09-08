#!/bin/bash
set -e
T=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/1e1664fd-1962-4d88-8a91-f786fbfbe0b6/scratchpad/testcase
cd $T; rm -rf clone scratch.git other
GIT_TERMINAL_PROMPT=0 git clone -q https://github.com/devkancheti4-design/test-case-.git clone 2>/dev/null
git init -q --bare scratch.git
cd clone; git remote set-url origin ../scratch.git
git config user.name "Devieswar Kancheti"; git config user.email "devkancheti4@gmail.com"
cp -R $T/seed/. .
echo "seeded a fresh clone (unborn $(git branch --show-current)); origin -> scratch.git"
