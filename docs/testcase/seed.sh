#!/bin/bash
set -e
T=$SHIP_DEMO_DIR/testcase
cd $T; rm -rf clone scratch.git other
GIT_TERMINAL_PROMPT=0 git clone -q https://github.com/devkancheti4-design/test-case-.git clone 2>/dev/null
git init -q --bare scratch.git
cd clone; git remote set-url origin ../scratch.git
git config user.name "Devieswar Kancheti"; git config user.email "devkancheti4@gmail.com"
cp -R $T/seed/. .
echo "seeded a fresh clone (unborn $(git branch --show-current)); origin -> scratch.git"
