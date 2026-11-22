"""Gravador multiplataforma: escolhe a implementação do macOS ou do Windows."""

import re
import signal
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from i18n import t
from transcrever import ROOT, RECORDINGS_DIR


class RecorderError(Exception):
    pass


def session_folder(name=""):
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    slug = re.sub(r"[^\w-]+", "-", name.strip().lower()).strip("-") if name else ""
    folder = RECORDINGS_DIR / (f"{stamp}_{slug}" if slug else stamp)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _mac_recorder_binary():
    # Dentro do app empacotado (PyInstaller) o binário fica em sys._MEIPASS.
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "mac-recorder"
    if getattr(sys, "frozen", False) and bundled.exists():
        return bundled
    binary = ROOT / "mac" / "mac-recorder"
    if not binary.exists():
        subprocess.run([str(ROOT / "mac" / "build.sh")], check=True)
    return binary


class MacRecorder:
    def __init__(self, folder):
        self.folder = folder
        self.proc = None
        self._levels = {"system": 0.0, "mic": 0.0}

    def start(self):
        self.proc = subprocess.Popen(
            [str(_mac_recorder_binary()), str(self.folder)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if self.proc.stdout.readline().strip() != "GRAVANDO":
            self.proc.wait()
            detail = self.proc.stderr.readline().strip()
            raise RecorderError(t("err_record_start", detail=detail) + "\n\n" + t("err_mac_permission"))
        threading.Thread(target=self._read_levels, daemon=True).start()

    def _read_levels(self):
        for line in self.proc.stdout:
            parts = line.split()
            if len(parts) == 3 and parts[0] == "NIVEL":
                self._levels = {"system": float(parts[1]), "mic": float(parts[2])}

    def levels(self):
        """Volume RMS atual (0 a 1) de cada trilha."""
        return self._levels

    def stop(self):
        self.proc.send_signal(signal.SIGINT)
        self.proc.wait()


def create_recorder(folder):
    if sys.platform == "darwin":
        return MacRecorder(folder)
    if sys.platform == "win32":
        from gravar_windows import WindowsRecorder

        return WindowsRecorder(folder)
    raise RecorderError(t("err_unsupported"))
