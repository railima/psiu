#!/bin/sh
# Gera dist/Psiu.app e dist/Psiu.dmg (requer Xcode Command Line Tools e uv).
set -e
cd "$(dirname "$0")"

./mac/build.sh
uv venv --python 3.12 --allow-existing .venv
uv pip install --python .venv/bin/python pywebview pyinstaller
.venv/bin/pyinstaller --noconfirm --clean psiu.spec

rm -f dist/Psiu.dmg
hdiutil create -volname Psiu -srcfolder dist/Psiu.app -ov -format UDZO dist/Psiu.dmg >/dev/null
echo "Pronto: $(pwd)/dist/Psiu.app e dist/Psiu.dmg"
