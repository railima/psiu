"""Configuração do usuário (chave da Deepgram, idiomas, preferências), fora da pasta do app."""

import json
import os
import sys
from pathlib import Path


def config_path():
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / "Library" / "Application Support"
    return base / "Psiu" / "config.json"


def load_config():
    path = config_path()
    return json.loads(path.read_text()) if path.exists() else {}


def save_config(**values):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**load_config(), **values}))
