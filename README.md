<p align="center">
  <a href="README.pt-BR.md"><img src="https://img.shields.io/badge/Leia%20em-Portugu%C3%AAs-2e9e5b?style=for-the-badge" alt="Leia em Português"></a>
</p>

<p align="center">
  <img src="icon/icon.png" width="128" alt="Psiu icon">
</p>

<h1 align="center">Psiu</h1>

<p align="center">
  Record and transcribe your meetings <b>without a bot joining the call</b>.<br>
  macOS and Windows · English and Portuguese · Speaker identification
</p>

---

Psiu records **your microphone** and **your computer's audio** straight from the operating system, the same
way Audacity records "what comes out of the sound card". It works with Google Meet, Zoom, Teams, Slack or
anything else, and nobody sees a "Notetaker" joining the meeting. When you're done, you get a transcript
with the speakers separated, ready to paste into Claude (or another AI) to ask for a summary, a task list
or a brainstorm.

> *Psiu* (pronounced "pee-SEW") is how Brazilians say "psst!": the quiet app that stays out of your meetings.

## Features

- **No bot**: local capture of the system audio (ScreenCaptureKit on macOS, WASAPI loopback on Windows).
- **"Me" is always identified**: microphone and system audio are recorded as separate tracks, so only the
  other voices go through speaker diarization.
- **English, Portuguese or mixed**, with speaker diarization, via [Deepgram](https://deepgram.com) (Nova-3).
- **Global hotkeys** that work while the app is minimized: `⌃⌥R` / `Ctrl+Alt+R` starts and stops recording;
  `⌃⌥M` / `Ctrl+Alt+M` marks an important moment. A sound confirms each action.
- **Live level meters** for both tracks (warns you if one of them is silent).
- **⭐ Mark moments** during the meeting; they are highlighted in the transcript.
- **Rename speakers** ("Speaker 1" → "Ana") across the whole transcript.
- **Copy with a prompt**: summary and decisions, task list, brainstorm or follow-up email, with or without
  timestamps.
- Searchable history, editable titles and an estimated cost for each recording.
- **Interface in English or Portuguese** (switch at the bottom of the sidebar); transcript labels and prompts
  follow the chosen language.

## Cost

Psiu is free; you bring your own Deepgram API key. Nova-3 multilingual for pre-recorded audio costs about
**US$ 0.0052/min per track**, so roughly **US$ 0.60 per hour of meeting** (two tracks). Check current
prices at [deepgram.com/pricing](https://deepgram.com/pricing). New accounts usually get free credits.

## Installation

**Download a ready-made build** from the [Releases](https://github.com/railima/psiu/releases) page:
`Psiu.exe` (Windows) or `Psiu.dmg` (macOS 15+). Or build it yourself:

### macOS (15 or later)

Requires the Xcode Command Line Tools (`xcode-select --install`) and [uv](https://docs.astral.sh/uv/).

```sh
./build_mac.sh        # creates dist/Psiu.app and dist/Psiu.dmg
```

Open the `.dmg` and drag Psiu into Applications. Since the app isn't signed by Apple, the first time you
open it right-click → **Open**. On the first recording, allow **Microphone** and **Screen & System Audio
Recording** in System Settings → Privacy & Security, then reopen the app.

### Windows 11

Install Python (`winget install Python.Python.3.12`), download this repository and double-click
`build_windows.bat`. It creates `dist\Psiu.exe`, a single executable you can keep anywhere.
SmartScreen may warn you the first time: **More info → Run anyway**.

Optional: `winget install ffmpeg` lets Psiu compress the audio before uploading (~8x smaller upload).

## Usage

1. Open Psiu and paste your Deepgram API key ([console.deepgram.com](https://console.deepgram.com) →
   API Keys). It is stored only on your computer.
2. Click the red button (or press `⌃⌥R` / `Ctrl+Alt+R`) to record, and again to stop.
3. The transcript shows up on screen. Rename the speakers, pick a prompt and click **Copy**.

Recordings are saved in `~/Documents/Psiu/`. **Tip:** wear headphones. Without them, your microphone also
picks up the other voices (Psiu tries to remove that echo, but the result is better with headphones).

## Privacy and responsibility

- Audio is recorded on your computer and sent **only to Deepgram** for transcription. Nothing goes through
  Psiu servers (there are none).
- The Deepgram key is stored in `~/Library/Application Support/Psiu/config.json` (macOS) or
  `%APPDATA%\Psiu\config.json` (Windows).
- **Let participants know** the meeting is being recorded. Consent rules vary by country and state, and
  complying with them is the responsibility of whoever records.

## How it works

```
mac/Recorder.swift     native macOS recorder (ScreenCaptureKit: system audio + microphone)
gravar_windows.py      Windows recorder (WASAPI loopback + microphone)
gravador.py            picks the recorder for the current platform
transcrever.py         sends audio to Deepgram, merges the tracks, removes echo and builds the Markdown
atalhos.py             global hotkeys (Carbon on macOS, RegisterHotKey on Windows)
app.py + ui/           user interface (pywebview)
i18n.py                English/Portuguese strings used by the Python side (the UI's are in ui/index.html)
config.py              user settings (API key, languages)
reuniao.py             command-line version
icon/make_icon.py      generates the icon
```

To run without packaging: `uv run --with pywebview python app.py` (macOS, after `./mac/build.sh`).
From the command line: `python reuniao.py "meeting name"` (press Enter to stop).

### Publishing a release

The [`build.yml`](.github/workflows/build.yml) workflow builds the `.exe` and the `.dmg` on every pull
request and when run manually (Actions tab). To publish a Release with both files attached:

```sh
git tag v0.1.0 && git push --tags
```

## License

[MIT](LICENSE)
