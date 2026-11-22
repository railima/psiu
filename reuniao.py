"""Grava uma reunião pelo terminal (seu microfone + áudio do computador) e gera a transcrição.

Uso:
    python reuniao.py ["nome da reunião"] [--idioma multi|pt-BR|en]

Pressione Enter (ou Ctrl+C) para parar. O transcript.md fica em ~/Documents/Psiu/<data>_<nome>/
e já vai para a área de transferência, pronto para colar no Claude.
"""

import argparse
import sys

from gravador import RecorderError, create_recorder, session_folder
from transcrever import TranscriptionError, copy_to_clipboard, transcribe_folder


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("nome", nargs="?", default="")
    parser.add_argument("--idioma", default="multi", help="multi (PT+EN misturados, padrão), pt-BR ou en")
    args = parser.parse_args()

    folder = session_folder(args.nome)
    print(f"Pasta: {folder}")
    recorder = create_recorder(folder)
    try:
        recorder.start()
    except RecorderError as e:
        sys.exit(str(e))
    try:
        input("Gravando... pressione Enter para parar.\n")
    except (KeyboardInterrupt, EOFError):
        print()
    recorder.stop()

    try:
        md = transcribe_folder(folder, args.idioma)
    except TranscriptionError as e:
        sys.exit(str(e))
    copy_to_clipboard(md.read_text(encoding="utf-8"))
    print(f"Pronto: {md}  (copiado para a área de transferência)")


if __name__ == "__main__":
    main()
