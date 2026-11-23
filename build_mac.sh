#!/bin/sh
# Gera dist/Psiu.app e dist/Psiu.dmg (requer Xcode Command Line Tools e uv).
set -e
cd "$(dirname "$0")"

./mac/build.sh
uv venv --python 3.12 --allow-existing .venv
uv pip install --python .venv/bin/python pywebview pyinstaller dmgbuild
.venv/bin/pyinstaller --noconfirm --clean psiu.spec

rm -f dist/Psiu.dmg
.venv/bin/dmgbuild -s dmg_settings.py Psiu dist/Psiu.dmg >/dev/null
echo "Pronto: $(pwd)/dist/Psiu.app e dist/Psiu.dmg"
