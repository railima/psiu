"""Gravação no Windows: áudio do sistema (WASAPI loopback, como o Audacity) + microfone.

Gera <pasta>/sistema.wav e <pasta>/mic.wav (mono, 16 bits).
"""

import threading
import wave

import numpy as np
import pyaudiowpatch as pyaudio

from i18n import t


class _Track:
    """Recebe blocos de áudio de um stream e grava em WAV mono, reduzido para 16 kHz quando possível."""

    def __init__(self, path, rate, channels):
        self.channels = channels
        # 48 kHz -> 16 kHz (fator 3) deixa o arquivo 3x menor; voz não perde nada para a transcrição.
        self.factor = rate // 16000 if rate % 16000 == 0 else 1
        self.pending = np.zeros(0, dtype=np.float32)
        self.level = 0.0  # volume RMS (0 a 1) do último bloco, para o medidor da interface
        self.peak = 0.0  # maior volume da gravação, para avisar quando o microfone não captou nada
        self.wav = wave.open(str(path), "wb")
        self.wav.setnchannels(1)
        self.wav.setsampwidth(2)
        self.wav.setframerate(rate // self.factor)
        self.lock = threading.Lock()

    def callback(self, in_data, frame_count, time_info, status):
        samples = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
        if self.channels > 1:
            samples = samples.reshape(-1, self.channels).mean(axis=1)
        if len(samples):
            self.level = float(np.sqrt(np.mean(samples ** 2)) / 32768)
            self.peak = max(self.peak, self.level)
        if self.factor > 1:
            samples = np.concatenate([self.pending, samples])
            usable = len(samples) - len(samples) % self.factor
            self.pending = samples[usable:]
            samples = samples[:usable].reshape(-1, self.factor).mean(axis=1)
        with self.lock:
            self.wav.writeframes(samples.astype(np.int16).tobytes())
        return (None, pyaudio.paContinue)

    def close(self):
        with self.lock:
            self.wav.close()


def _input_devices(pa):
    """Microfones do WASAPI (sem os dispositivos de loopback)."""
    wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)["index"]
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if dev["hostApi"] == wasapi and dev["maxInputChannels"] > 0 and not dev.get("isLoopbackDevice"):
            yield dev


def list_microphones():
    pa = pyaudio.PyAudio()
    try:
        return [dev["name"] for dev in _input_devices(pa)]
    finally:
        pa.terminate()


class WindowsRecorder:
    def __init__(self, output_dir, mic_name=None):
        self.output_dir = output_dir
        self.mic_name = mic_name  # None ou nome que não existe mais: usa o microfone padrão do Windows
        self.pa = pyaudio.PyAudio()
        self.streams = []
        self.tracks = []

    def start(self):
        try:
            self._start()
        except Exception as e:
            from gravador import RecorderError

            self.stop()
            raise RecorderError(t("err_record_start", detail=e)) from e

    def _start(self):
        wasapi = self.pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        speakers = self.pa.get_device_info_by_index(wasapi["defaultOutputDevice"])
        loopback = self._loopback_for(speakers)
        mic = next((d for d in _input_devices(self.pa) if d["name"] == self.mic_name), None) \
            or self.pa.get_device_info_by_index(wasapi["defaultInputDevice"])

        print(f"  Sistema: {speakers['name']}")
        print(f"  Microfone: {mic['name']}")

        # O loopback do WASAPI não entrega dados quando nada está tocando, o que
        # encurtaria a trilha e desalinharia os tempos. Tocar silêncio contínuo evita isso.
        silence_rate = int(speakers["defaultSampleRate"])
        silence_channels = speakers["maxOutputChannels"]
        self._open(
            format=pyaudio.paInt16,
            channels=silence_channels,
            rate=silence_rate,
            output=True,
            output_device_index=speakers["index"],
            stream_callback=lambda _d, n, _t, _s: (b"\x00" * n * silence_channels * 2, pyaudio.paContinue),
        )

        for name, dev in (("sistema", loopback), ("mic", mic)):
            rate = int(dev["defaultSampleRate"])
            channels = max(1, min(dev["maxInputChannels"], 2))
            track = _Track(self.output_dir / f"{name}.wav", rate, channels)
            self.tracks.append(track)
            self._open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=dev["index"],
                frames_per_buffer=1024,
                stream_callback=track.callback,
            )

    def levels(self):
        """Volume RMS atual (0 a 1) de cada trilha."""
        system, mic = self.tracks
        return {"system": system.level, "mic": mic.level}

    def peaks(self):
        """Maior volume de cada trilha durante a gravação."""
        system, mic = self.tracks
        return {"system": system.peak, "mic": mic.peak}

    def _loopback_for(self, speakers):
        if speakers.get("isLoopbackDevice"):
            return speakers
        for dev in self.pa.get_loopback_device_info_generator():
            if speakers["name"] in dev["name"]:
                return dev
        raise RuntimeError(t("err_no_loopback"))

    def _open(self, **kwargs):
        stream = self.pa.open(**kwargs)
        stream.start_stream()
        self.streams.append(stream)

    def stop(self):
        for stream in self.streams:
            stream.stop_stream()
            stream.close()
        for track in self.tracks:
            track.close()
        self.pa.terminate()
