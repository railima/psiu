"""Interface gráfica do Psiu (pywebview): gravar, parar e ver o transcript."""

import math
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import webview

import atalhos
import i18n
from config import load_config, save_config
from gravador import RecorderError, create_recorder, session_folder
from i18n import t
from transcrever import (
    ME,
    RECORDINGS_DIR,
    TranscriptionError,
    copy_to_clipboard,
    default_label,
    display_name,
    load_lines,
    load_meta,
    render_markdown,
    save_meta,
    transcribe_folder,
    write_markdown,
)

UI_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "ui"
DEEPGRAM_PRICE_PER_MINUTE = 0.0052  # Nova-3 multilíngue, pré-gravado; cobrado por trilha (mic + sistema)

def _in_recordings(folder):
    path = Path(folder).resolve()
    if RECORDINGS_DIR.resolve() not in path.parents:
        raise ValueError(f"Folder outside {RECORDINGS_DIR}: {folder}")
    return path


class Api:
    """Métodos chamados pelo JavaScript da interface (window.pywebview.api.*)."""

    def __init__(self):
        self.recorder = None
        self.folder = None
        self.started = None
        self.lock = threading.Lock()
        self.hotkeys_ok = None
        self._window = None  # com "_" para o pywebview não expor a janela ao JavaScript

    # Estado geral e configuração

    def state(self):
        config = load_config()
        return {
            "has_key": bool(config.get("deepgram_key") or os.environ.get("DEEPGRAM_API_KEY")),
            "language": config.get("language", "multi"),
            "timestamps": config.get("timestamps", True),
            "recordings": self._recordings(),
            "ui_language": i18n.language(),
            "prompts": [{"id": k, "label": label} for k, (label, _) in i18n.prompts().items()],
            "hotkeys": atalhos.labels() if self.hotkeys_ok else None,
        }

    def _recordings(self):
        if not RECORDINGS_DIR.exists():
            return []
        folders = sorted((f for f in RECORDINGS_DIR.iterdir() if f.is_dir()), reverse=True)
        return [
            {
                "folder": str(f),
                "name": f.name,
                "title": load_meta(f)["title"],
                "done": (f / "transcript.json").exists() or (f / "transcript.md").exists(),
            }
            for f in folders
        ]

    def save_key(self, key):
        save_config(deepgram_key=key.strip())
        return self.state()

    def set_ui_language(self, lang):
        if lang in i18n.LANGUAGES:
            save_config(ui_language=lang)
        return self.state()

    def set_timestamps(self, enabled):
        save_config(timestamps=bool(enabled))

    # Gravação

    def start(self, name, language):
        with self.lock:
            save_config(language=language)
            self.folder = session_folder(name)
            if name.strip():
                save_meta(self.folder, title=name.strip())
            self.recorder = create_recorder(self.folder)
            try:
                self.recorder.start()
            except RecorderError as e:
                self.recorder = None
                shutil.rmtree(self.folder, ignore_errors=True)
                return {"error": str(e)}
            self.started = time.monotonic()
            return {"ok": True}

    def levels(self):
        """Volume atual das trilhas em escala de 0 a 1 (−60 dB a 0 dB), para o medidor."""
        recorder = self.recorder
        if not recorder:
            return {"system": 0, "mic": 0}

        def scale(rms):
            return max(0.0, min(1.0, (20 * math.log10(rms) + 60) / 60)) if rms > 0 else 0.0

        return {k: scale(v) for k, v in recorder.levels().items()}

    def mark(self):
        """Marca o momento atual da gravação como importante."""
        if not self.recorder:
            return 0
        marks = load_meta(self.folder)["marks"] + [round(time.monotonic() - self.started, 1)]
        save_meta(self.folder, marks=marks)
        return len(marks)

    def stop(self, language):
        with self.lock:
            if self.recorder:
                self.recorder.stop()
                self.recorder = None
        return self.transcribe(str(self.folder), language)

    # Atalhos globais e retorno ao usuário com o app em segundo plano

    def register_hotkeys(self):
        self.hotkeys_ok = atalhos.register({
            "toggle": lambda: self._window.evaluate_js("toggleRecording(true)"),
            "mark": lambda: self._window.evaluate_js("mark(true)"),
        })
        # A interface pode ter carregado antes do registro; atualiza a dica dos atalhos.
        threading.Thread(target=lambda: self._window.evaluate_js("window.refresh && api && refresh()"), daemon=True).start()

    def sound(self, kind):
        """Som curto de confirmação para ações feitas pelo atalho, sem olhar para a janela."""
        if sys.platform == "darwin":
            name = {"start": "Blow", "stop": "Bottle", "mark": "Tink", "error": "Basso"}[kind]
            subprocess.Popen(["afplay", f"/System/Library/Sounds/{name}.aiff"])
        elif sys.platform == "win32":
            import winsound

            alias = {"start": "SystemAsterisk", "stop": "SystemExclamation", "mark": "SystemDefault", "error": "SystemHand"}[kind]
            winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)

    def bring_to_front(self):
        self._window.restore()
        self._window.show()
        if sys.platform == "darwin":
            from AppKit import NSApp
            from PyObjCTools import AppHelper

            AppHelper.callAfter(lambda: NSApp.activateIgnoringOtherApps_(True))

    def shutdown(self):
        with self.lock:
            if self.recorder:
                self.recorder.stop()
                self.recorder = None

    # Transcrições

    def transcribe(self, folder, language):
        try:
            transcribe_folder(_in_recordings(folder), language, progress=lambda _msg: None)
        except TranscriptionError as e:
            return {"error": str(e), "folder": folder}
        return self._payload(folder)

    def open_recording(self, folder):
        folder = _in_recordings(folder)
        if load_lines(folder) is None:
            # Gravações de versões anteriores: regera a partir das respostas salvas da Deepgram (sem custo).
            if (folder / "deepgram_sistema.json").exists() or (folder / "deepgram_mic.json").exists():
                return self.transcribe(str(folder), load_config().get("language", "multi"))
            return {"error": t("err_not_transcribed"), "folder": str(folder)}
        return self._payload(folder)

    def _payload(self, folder):
        folder = Path(folder)
        lines = load_lines(folder) or []
        meta = load_meta(folder)
        minutes = (lines[-1]["end"] / 60) if lines else 0
        speakers = list(dict.fromkeys(u["speaker"] for u in lines))
        return {
            "ok": True,
            "folder": str(folder),
            "name": folder.name,
            "title": meta["title"],
            "marks": meta["marks"],
            "lines": lines,
            "speakers": speakers,
            "me": ME,
            # Nome exibido de cada falante (renomeado ou o padrão traduzido) e o padrão, para o placeholder.
            "labels": {s: display_name(s, meta["names"]) for s in speakers},
            "defaults": {s: default_label(s) for s in speakers},
            "duration": minutes * 60,
            "cost": minutes * DEEPGRAM_PRICE_PER_MINUTE * 2,
        }

    def rename_speaker(self, folder, speaker, name):
        folder = _in_recordings(folder)
        names = load_meta(folder)["names"]
        if name.strip() and name.strip() != default_label(speaker):
            names[speaker] = name.strip()
        else:
            names.pop(speaker, None)
        save_meta(folder, names=names)
        write_markdown(folder)
        return self._payload(folder)

    def set_title(self, folder, title):
        folder = _in_recordings(folder)
        save_meta(folder, title=title.strip())
        write_markdown(folder)
        return self.state()["recordings"]

    def copy(self, folder, prompt_id, timestamps):
        folder = _in_recordings(folder)
        text = render_markdown(folder, timestamps=timestamps)
        prompts = i18n.prompts()
        if prompt_id in prompts:
            me = display_name(ME, load_meta(folder)["names"])
            text = f"{prompts[prompt_id][1].format(me=me)}\n\n---\n\n{text}"
        copy_to_clipboard(text)
        return True

    def delete(self, folder):
        shutil.rmtree(_in_recordings(folder))
        return self.state()["recordings"]

    def open_folder(self, folder):
        folder = str(_in_recordings(folder))
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            subprocess.run(["open", folder])


def main():
    api = Api()
    window = webview.create_window(
        "Psiu", url=str(UI_DIR / "index.html"), js_api=api,
        width=900, height=720, min_size=(640, 540),
    )
    window.events.closing += api.shutdown
    api._window = window

    def on_start():
        if sys.platform == "darwin":
            # Os atalhos do Carbon precisam ser registrados na thread principal.
            from PyObjCTools import AppHelper

            AppHelper.callAfter(api.register_hotkeys)
        else:
            api.register_hotkeys()

    webview.start(on_start)


if __name__ == "__main__":
    main()
