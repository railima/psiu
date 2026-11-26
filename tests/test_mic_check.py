import app
import transcrever
from gravador import MIC_SILENT_RMS, mic_was_silent


class FakeRecorder:
    def __init__(self, mic_peak):
        self._peaks = {"system": 0.2, "mic": mic_peak}

    def stop(self):
        pass

    def peaks(self):
        return self._peaks


def test_mic_was_silent():
    assert mic_was_silent({"system": 0.3, "mic": 0.0})
    assert mic_was_silent({"system": 0.3, "mic": MIC_SILENT_RMS / 2})
    assert not mic_was_silent({"system": 0.3, "mic": 0.05})


def stop_with_mic_peak(tmp_path, monkeypatch, peak):
    monkeypatch.setattr(app, "RECORDINGS_DIR", tmp_path)
    folder = tmp_path / "2026-11-26_100000"
    folder.mkdir()
    api = app.Api()
    api.folder, api.recorder = folder, FakeRecorder(peak)
    monkeypatch.setattr(api, "transcribe", lambda folder, language: api._payload(folder))
    return folder, api.stop("multi")


def test_silent_mic_is_flagged_and_reported(tmp_path, monkeypatch):
    # Ex.: o microfone padrão do Windows era uma webcam virtual desligada (só entrega silêncio).
    folder, payload = stop_with_mic_peak(tmp_path, monkeypatch, 0.0)
    assert transcrever.load_meta(folder)["mic_silent"] is True
    assert payload["mic_silent"] is True


def test_working_mic_is_not_flagged(tmp_path, monkeypatch):
    folder, payload = stop_with_mic_peak(tmp_path, monkeypatch, 0.08)
    assert transcrever.load_meta(folder)["mic_silent"] is False
    assert payload["mic_silent"] is False
