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


# Volume RMS (0 a 1) que a voz ultrapassa com folga. Se o microfone nunca passou disso na reunião inteira,
# ele não captou ninguém (ex.: o padrão do sistema era um microfone virtual desligado).
MIC_SILENT_RMS = 0.002


def mic_was_silent(peaks):
    return peaks["mic"] < MIC_SILENT_RMS


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
        self._peaks = {"system": 0.0, "mic": 0.0}

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
                self._peaks = {k: max(self._peaks[k], v) for k, v in self._levels.items()}

    def levels(self):
        """Volume RMS atual (0 a 1) de cada trilha."""
        return self._levels

    def peaks(self):
        """Maior volume de cada trilha durante a gravação."""
        return self._peaks

    def stop(self):
        self.proc.send_signal(signal.SIGINT)
        self.proc.wait()


def list_microphones():
    """Microfones que o usuário pode escolher. No macOS o gravador usa o padrão do sistema (lista vazia)."""
    if sys.platform == "win32":
        from gravar_windows import list_microphones as windows_list

        return windows_list()
    return []


def create_recorder(folder, mic=None):
    """`mic`: nome do microfone escolhido (Windows); None usa o padrão do sistema."""
    if sys.platform == "darwin":
        return MacRecorder(folder)
    if sys.platform == "win32":
        from gravar_windows import WindowsRecorder

        return WindowsRecorder(folder, mic)
    raise RecorderError(t("err_unsupported"))
