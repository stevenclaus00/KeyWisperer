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
  - `{"type":"control","action":"send"|"undo"|"pause"|"resume"|"readback"}`
    (send = press Enter, undo = remove last typed chunk, pause/resume = stop/start acting on speech,
    readback = read the latest AI reply on screen aloud)

Companion to phone (JSON text frames):

- `{"type":"status","listening":true,"connected":true}` (sent on connect and when listening changes)
- `{"type":"utterance","text":"<raw transcript>"}`
- `{"type":"typed","text":"<what was typed>"}`
- `{"type":"error","message":"..."}`
- `{"type":"status_message","text":"Reading back…"}` (progress note to show the user)
- `{"type":"speak","text":"..."}` (the phone should speak this with Android text-to-speech)

## Read-back

Say "read it back" / "read that back" / "read back" (as the whole utterance), or press the
read-back button in the app. The companion takes a screenshot, asks a vision model for the
latest assistant reply, and sends it to the phone as a `speak` message. It runs in the
background, so dictation keeps working. Failures arrive as `error` events.

On GNOME Wayland the screenshot uses the xdg-desktop-portal (via `dbus-next`); GNOME may show
a one-time permission prompt. On other desktops set `screenshot_command` (e.g. `grim -`).
Try it at the desk with `keywhisperer readback-test`; check your setup with `keywhisperer doctor`.

## Configuration: `[ai]` and `[readback]`

```toml
[ai]
base_url = ""                    # "" = official OpenAI API
api_key_env = "OPENAI_API_KEY"   # name of the env var that holds the key

[readback]
enabled = true
model = "gpt-4o-mini"            # any cheap vision model; rename if your provider differs
max_chars = 4000
screenshot_command = ""          # "" = portal; else a command printing PNG to stdout
```

### Costs and keys

- Whisper is billed per minute of audio.
- Read-back is one small vision call each time you use it.
- Phone text-to-speech is free.
- A consumer chat subscription (ChatGPT Plus, Claude Pro, ...) is not the same as API access:
  you need an API key with billing enabled from your provider.

### LiteLLM or another OpenAI-compatible proxy

Point `base_url` at the proxy (e.g. `http://localhost:4000`) and set `[transcription] model`
and `[readback] model` to the model names the proxy exposes. If the proxy needs no key, leave
the env var unset; a dummy key is sent.

## Layout

- `segmenter.py` VAD-based utterance splitting (webrtcvad, energy fallback)
- `ai.py` shared OpenAI-compatible client factory
- `readback/` screenshot + vision extraction for read-back
- `transcribe/` speech-to-text providers (add a provider = one file + one line in `__init__.py`)
- `pipeline.py` ordered queue: transcribe, process text, run actions
- `server.py`, `pairing.py`, `config.py`, `cli.py`
