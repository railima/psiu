# PyInstaller: gera Psiu.app (macOS) ou Psiu.exe (Windows).
# Use os scripts build_mac.sh / build_windows.bat em vez de chamar direto.
import os
import sys

VERSION = os.environ.get("PSIU_VERSION", "0.0.0-dev").lstrip("v")  # o workflow passa a tag (ex.: v0.1.0)
binaries = [("mac/mac-recorder", ".")] if sys.platform == "darwin" else []

a = Analysis(["app.py"], binaries=binaries, datas=[("ui/index.html", "ui"), ("ui/icon.png", "ui")])
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Psiu", console=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="Psiu")
    app = BUNDLE(
        coll,
        name="Psiu.app",
        icon="icon/Psiu.icns",
        bundle_identifier="io.github.railima.psiu",
        info_plist={
            "CFBundleShortVersionString": VERSION,
            "LSMinimumSystemVersion": "15.0",
            "NSHighResolutionCapable": True,
            "NSMicrophoneUsageDescription": "O Psiu grava o seu microfone durante as reuniões.",
            "NSScreenCaptureUsageDescription": "O Psiu grava o áudio do computador durante as reuniões.",
        },
    )
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Psiu", console=False,
              icon="icon/Psiu.ico")
