"""Transcreve uma pasta de gravação (mic + sistema) com a Deepgram e gera transcript.md.

Uso direto (re-transcrever uma gravação existente):
    python transcrever.py <pasta-da-gravacao> [--idioma multi|pt-BR|en] [--forcar]
"""

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from config import load_config
from i18n import t

ROOT = Path(__file__).resolve().parent
RECORDINGS_DIR = Path.home() / "Documents" / "Psiu"
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
CONTENT_TYPES = {".m4a": "audio/mp4", ".wav": "audio/wav", ".ogg": "audio/ogg"}


class TranscriptionError(Exception):
    pass


def api_key():
    key = os.environ.get("DEEPGRAM_API_KEY") or load_config().get("deepgram_key")
    key_file = ROOT / "deepgram_key.txt"
    if not key and key_file.exists():
        key = key_file.read_text().strip()
    if not key:
        raise TranscriptionError(t("err_no_key"))
    return key


def find_track(folder, name):
    for ext in (".m4a", ".ogg", ".wav"):
        path = folder / f"{name}{ext}"
        if path.exists():
            return path
    return None


def compress_if_possible(path):
    """WAV é grande (~115 MB/h). Se houver ffmpeg, converte para Opus (~15 MB/h) antes do upload."""
    if path.suffix != ".wav" or not shutil.which("ffmpeg"):
        return path
    out = path.with_suffix(".ogg")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
         "-ac", "1", "-ar", "16000", "-c:a", "libopus", "-b:a", "32k", str(out)],
        check=True,
    )
    path.unlink()
    return out


def deepgram(path, language, diarize):
    params = {
        "model": "nova-3",
        "language": language,
        "smart_format": "true",
        "punctuate": "true",
        "utterances": "true",
        "diarize": "true" if diarize else "false",
    }
    request = urllib.request.Request(
        f"{DEEPGRAM_URL}?{urllib.parse.urlencode(params)}",
        data=path.read_bytes(),
        headers={"Authorization": f"Token {api_key()}", "Content-Type": CONTENT_TYPES[path.suffix]},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        raise TranscriptionError(t("err_deepgram", code=e.code, detail=e.read().decode(errors="replace"))) from e
    except urllib.error.URLError as e:
        raise TranscriptionError(t("err_offline", reason=e.reason)) from e


def transcribe_track(folder, name, language, diarize, force, progress):
    """Retorna a resposta da Deepgram, reaproveitando o JSON salvo para não pagar de novo."""
    cache = folder / f"deepgram_{name}.json"
    if cache.exists() and not force:
        return json.loads(cache.read_text())
    path = find_track(folder, name)
    if path is None:
        return None
    path = compress_if_possible(path)
    progress(t("progress_uploading", file=path.name, size=path.stat().st_size / 1e6))
    result = deepgram(path, language, diarize)
    cache.write_text(json.dumps(result, ensure_ascii=False))
    return result


def utterances(result, label_for):
    if not result:
        return []
    return [
        {"start": u["start"], "end": u["end"], "speaker": label_for(u), "text": u["transcript"].strip()}
        for u in result["results"].get("utterances", [])
        if u["transcript"].strip()
    ]


def drop_echo(mine, others):
    """Sem fone de ouvido, o microfone também capta as vozes dos outros.
    Remove falas do mic que coincidem no tempo e no texto com falas do sistema."""
    kept = []
    for u in mine:
        overlapping = " ".join(o["text"] for o in others if o["start"] < u["end"] and o["end"] > u["start"])
        similar = difflib.SequenceMatcher(None, u["text"].lower(), overlapping.lower()).ratio()
        if not overlapping or similar < 0.6:
            kept.append(u)
    return kept


def merge(items, max_gap=2.0):
    """Ordena por tempo e junta falas consecutivas da mesma pessoa."""
    merged = []
    for u in sorted(items, key=lambda u: u["start"]):
        last = merged[-1] if merged else None
        if last and last["speaker"] == u["speaker"] and u["start"] - last["end"] <= max_gap:
            last["text"] += " " + u["text"]
            last["end"] = max(last["end"], u["end"])
        else:
            merged.append(dict(u))
    return merged


def timestamp(seconds):
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def load_meta(folder):
    """Dados editáveis da gravação: título, nomes dos falantes e momentos marcados."""
    path = Path(folder) / "meta.json"
    meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {"title": "", "names": {}, "marks": [], **meta}


def save_meta(folder, **values):
    path = Path(folder) / "meta.json"
    path.write_text(json.dumps({**load_meta(folder), **values}, ensure_ascii=False), encoding="utf-8")


# Falantes são guardados com identificadores neutros ("me", "speaker:1", ...) e traduzidos só na exibição.
ME = "me"


def speaker_id(n):
    return f"speaker:{n}"


def _legacy_speaker(speaker):
    """Converte rótulos das primeiras versões ("Eu", "Pessoa 2") para os identificadores atuais."""
    if speaker == "Eu":
        return ME
    match = re.fullmatch(r"Pessoa (\d+)", speaker)
    return speaker_id(match.group(1)) if match else speaker


def default_label(speaker):
    if speaker == ME:
        return t("me")
    if speaker.startswith("speaker:"):
        return t("speaker", n=speaker.split(":", 1)[1])
    return speaker


def display_name(speaker, names):
    return names.get(speaker) or default_label(speaker)


def load_lines(folder):
    path = Path(folder) / "transcript.json"
    if not path.exists():
        return None
    lines = json.loads(path.read_text(encoding="utf-8"))
    for u in lines:
        u["speaker"] = _legacy_speaker(u["speaker"])
    return lines


def render_markdown(folder, timestamps=True):
    """Monta o transcript em Markdown aplicando os nomes dos falantes e as marcações."""
    folder = Path(folder)
    meta = load_meta(folder)
    lines = load_lines(folder) or []
    names = meta["names"]

    items = [dict(u) for u in lines] + [{"start": s, "mark": True} for s in meta["marks"]]
    items.sort(key=lambda u: u["start"])

    speakers = list(dict.fromkeys(u["speaker"] for u in lines))
    duration = timestamp(lines[-1]["end"]) if lines else "00:00:00"
    participants = ", ".join(display_name(s, names) for s in speakers) or "—"
    out = [
        "# " + t("md_title", title=meta["title"] or folder.name),
        "",
        t("md_summary", duration=duration, participants=participants),
    ]
    if any(s.startswith("speaker:") and s not in names for s in speakers):
        out.append(t("md_unnamed_note"))
    if meta["marks"]:
        out.append(t("md_marks_note"))
    out.append("")
    for u in items:
        prefix = f"[{timestamp(u['start'])}] " if timestamps else ""
        if u.get("mark"):
            out.append(f"{prefix}⭐ **{t('marked_moment')}**")
        else:
            out.append(f"{prefix}**{display_name(u['speaker'], names)}:** {u['text']}")
    return "\n".join(out) + "\n"


def write_markdown(folder):
    md_path = Path(folder) / "transcript.md"
    md_path.write_text(render_markdown(folder), encoding="utf-8")
    return md_path


def copy_to_clipboard(text):
    if sys.platform == "darwin":
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    elif sys.platform == "win32":
        # clip.exe entende UTF-16 com BOM, preservando acentos.
        subprocess.run(["clip"], input=text.encode("utf-16"), check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)


def transcribe_folder(folder, language="multi", force=False, progress=print):
    folder = Path(folder)
    progress(t("progress_transcribing"))
    mic = transcribe_track(folder, "mic", language, diarize=False, force=force, progress=progress)
    system = transcribe_track(folder, "sistema", language, diarize=True, force=force, progress=progress)
    if mic is None and system is None:
        raise TranscriptionError(t("err_no_audio", folder=folder))

    others = utterances(system, lambda u: speaker_id(u.get("speaker", 0) + 1))
    mine = drop_echo(utterances(mic, lambda u: ME), others)
    lines = merge(mine + others)

    (folder / "transcript.json").write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
    return write_markdown(folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pasta")
    parser.add_argument("--idioma", default="multi", help="multi (PT+EN misturados, padrão), pt-BR ou en")
    parser.add_argument("--forcar", action="store_true", help="ignora o JSON salvo e envia de novo (cobra de novo)")
    args = parser.parse_args()
    try:
        md = transcribe_folder(args.pasta, args.idioma, args.forcar)
    except TranscriptionError as e:
        sys.exit(str(e))
    copy_to_clipboard(md.read_text(encoding="utf-8"))
    print(t("cli_done", path=md))
