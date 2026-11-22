"""Textos gerados pelo Python (erros, transcript, prompts) em inglês (padrão) e português.

Os textos da interface ficam em ui/index.html.
"""

from config import load_config

LANGUAGES = ("en", "pt-BR")

STRINGS = {
    "en": {
        "me": "Me",
        "speaker": "Speaker {n}",
        "marked_moment": "Marked moment",
        "md_title": "Meeting transcript — {title}",
        "md_summary": "Duration: {duration}. Participants: {participants}.",
        "md_unnamed_note": "(\"Speaker N\" are participants identified by voice, without a name.)",
        "md_marks_note": "⭐ marks a moment flagged as important during the meeting.",
        "err_no_key": "Deepgram API key not configured.",
        "err_deepgram": "Deepgram error ({code}): {detail}",
        "err_offline": "Could not reach Deepgram: {reason}",
        "err_no_audio": "No audio found in {folder}.",
        "err_not_transcribed": "This recording hasn't been transcribed yet.",
        "err_record_start": "Could not start recording: {detail}",
        "err_mac_permission": "Allow Psiu in System Settings → Privacy & Security → “Screen & System Audio "
                              "Recording” and “Microphone”, then reopen the app.",
        "err_no_loopback": "couldn't find the loopback device for the default audio output",
        "err_unsupported": "Unsupported system (use macOS or Windows).",
        "progress_transcribing": "Transcribing...",
        "progress_uploading": "Uploading {file} ({size:.1f} MB)...",
        "cli_folder": "Folder: {folder}",
        "cli_recording": "Recording... press Enter to stop.",
        "cli_done": "Done: {path}  (copied to clipboard)",
    },
    "pt-BR": {
        "me": "Eu",
        "speaker": "Pessoa {n}",
        "marked_moment": "Momento marcado",
        "md_title": "Transcrição da reunião — {title}",
        "md_summary": "Duração: {duration}. Participantes: {participants}.",
        "md_unnamed_note": "(\"Pessoa N\" são participantes identificados pela voz, sem nome.)",
        "md_marks_note": "⭐ indica um momento marcado como importante durante a reunião.",
        "err_no_key": "Chave da Deepgram não configurada.",
        "err_deepgram": "Erro da Deepgram ({code}): {detail}",
        "err_offline": "Sem conexão com a Deepgram: {reason}",
        "err_no_audio": "Nenhum áudio encontrado em {folder}.",
        "err_not_transcribed": "Esta gravação ainda não foi transcrita.",
        "err_record_start": "Não foi possível iniciar a gravação: {detail}",
        "err_mac_permission": "Libere o Psiu em Ajustes do Sistema → Privacidade e Segurança → “Gravação de Tela "
                              "e Áudio do Sistema” e “Microfone”, depois reabra o app.",
        "err_no_loopback": "não encontrei o dispositivo de loopback da saída de áudio padrão",
        "err_unsupported": "Sistema não suportado (use macOS ou Windows).",
        "progress_transcribing": "Transcrevendo...",
        "progress_uploading": "Enviando {file} ({size:.1f} MB)...",
        "cli_folder": "Pasta: {folder}",
        "cli_recording": "Gravando... pressione Enter para parar.",
        "cli_done": "Pronto: {path}  (copiado para a área de transferência)",
    },
}

# Prompts para colar junto com o transcript. {me} é o nome de quem gravou, como aparece no transcript.
PROMPTS = {
    "en": {
        "summary": (
            "Summary and decisions",
            "Below is a meeting transcript (it may be in English, Portuguese or mixed). \"{me}\" is me, the "
            "person who recorded it. Reply in English with:\n"
            "1. A short summary of what was discussed;\n"
            "2. The decisions made;\n"
            "3. Next steps, with owner and deadline when mentioned;\n"
            "4. Open questions or unresolved points.\n"
            "Pay special attention to the moments marked with ⭐.",
        ),
        "tasks": (
            "Task list",
            "Below is a meeting transcript. \"{me}\" is me, the person who recorded it. Extract every task and "
            "commitment made, in English, as a checklist grouped by person (starting with mine). Include "
            "deadlines and context when available. Don't invent tasks that weren't mentioned.",
        ),
        "brainstorm": (
            "Brainstorm",
            "Below is a conversation transcript. \"{me}\" is me, the person who recorded it. Use it as the "
            "starting point for a brainstorm in English: list the main ideas that came up, expand on the most "
            "promising ones, suggest new ideas that weren't mentioned and point out risks or blind spots.",
        ),
        "email": (
            "Follow-up email",
            "Below is a meeting transcript. \"{me}\" is me, the person who recorded it. Write a short, friendly "
            "follow-up email to the participants, in the meeting's predominant language, with a summary, the "
            "decisions and the next steps with owners.",
        ),
    },
    "pt-BR": {
        "summary": (
            "Resumo e decisões",
            "Abaixo está a transcrição de uma reunião (pode estar em português, inglês ou misturado). "
            "\"{me}\" sou eu, quem gravou. Responda em português com:\n"
            "1. Um resumo curto do que foi discutido;\n"
            "2. As decisões tomadas;\n"
            "3. Os próximos passos, com responsável e prazo quando mencionados;\n"
            "4. Pontos em aberto ou dúvidas que ficaram.\n"
            "Dê atenção especial aos momentos marcados com ⭐.",
        ),
        "tasks": (
            "Lista de tarefas",
            "Abaixo está a transcrição de uma reunião. \"{me}\" sou eu, quem gravou. Extraia todas as tarefas e "
            "compromissos assumidos, em português, como uma checklist agrupada por pessoa (comece pelas minhas). "
            "Inclua prazo e contexto quando houver. Não invente tarefas que não foram mencionadas.",
        ),
        "brainstorm": (
            "Brainstorm",
            "Abaixo está a transcrição de uma conversa. \"{me}\" sou eu, quem gravou. Use-a como ponto de partida "
            "para um brainstorm em português: liste as principais ideias que surgiram, aprofunde as mais "
            "promissoras, proponha ideias novas que não foram citadas e aponte riscos ou pontos cegos.",
        ),
        "email": (
            "E-mail de follow-up",
            "Abaixo está a transcrição de uma reunião. \"{me}\" sou eu, quem gravou. Escreva um e-mail de "
            "follow-up curto e cordial para os participantes, no idioma predominante da reunião, com um resumo, "
            "as decisões e os próximos passos com responsáveis.",
        ),
    },
}


def language():
    lang = load_config().get("ui_language")
    return lang if lang in LANGUAGES else "en"


def t(key, **values):
    return STRINGS[language()][key].format(**values)


def prompts():
    return PROMPTS[language()]
