# KeyWhisperer companion

An Android phone acts as a wireless microphone and streams audio over WiFi to this
Python app on your Linux desktop. The companion splits speech at pauses, transcribes
each utterance with OpenAI, turns the text into actions (type, press keys, undo...),
and types into the focused window.

## Install

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e companion          # add '.[dev]' for the tests
export OPENAI_API_KEY=sk-...      # read from the environment
```

Optionally copy `config.example.toml` to `~/.config/keywhisperer/config.toml`.

## Output setup

Output backends (clipboard, ydotool, stdout) and the Wayland/GNOME setup are
documented in `keywhisperer/output/README.md`. Short version: on Wayland/GNOME,
real typing needs `ydotool`.

## Run and pair

```bash
keywhisperer run [--config PATH] [--output clipboard|ydotool|stdout]
keywhisperer pair        # print the pairing URI + QR code again
```

Pairing URI: `kw://<lan-ip>:<port>?token=<token>`. The token is generated on first run
and stored in `~/.config/keywhisperer/token` (chmod 600). Scan the terminal QR code
from the phone app.

## Test without the phone

```bash
python companion/tools/send_wav.py speech.wav --host 127.0.0.1   # streams in real time
keywhisperer test-wav speech.wav                                  # no typing, prints actions
```

WAV files must be 16 kHz, mono, 16-bit. Run tests with `pytest -q companion/tests`.

## WebSocket protocol

Connect to `ws://<ip>:<port>/audio?token=<token>`. A wrong token or path closes the
connection with code **4001**. Only one phone at a time; a new connection replaces the old one.

Phone to companion:

- **Binary frames**: raw 16 kHz, mono, 16-bit little-endian PCM, any frame size.
- **Text frames (JSON)**:
  - `{"type":"hello","device":"<name>"}`
  - `{"type":"control","action":"send"|"undo"|"pause"|"resume"}`
    (send = press Enter, undo = remove last typed chunk, pause/resume = stop/start acting on speech)

Companion to phone (JSON text frames):

- `{"type":"status","listening":true,"connected":true}` (sent on connect and when listening changes)
- `{"type":"utterance","text":"<raw transcript>"}`
- `{"type":"typed","text":"<what was typed>"}`
- `{"type":"error","message":"..."}`

## Layout

- `segmenter.py` VAD-based utterance splitting (webrtcvad, energy fallback)
- `transcribe/` speech-to-text providers (add a provider = one file + one line in `__init__.py`)
- `pipeline.py` ordered queue: transcribe, process text, run actions
- `server.py`, `pairing.py`, `config.py`, `cli.py`
