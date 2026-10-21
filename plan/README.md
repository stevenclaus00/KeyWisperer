# VoiceKey AI

> Real-time AI voice transcription on your phone — streamed as keyboard input to your PC over WiFi.

Turn your Android or iPhone into a voice-powered keyboard and macro launcher for your Windows, macOS, or Linux desktop. Speak naturally, see the text appear on your PC a second later. Trigger macros, open apps, type anywhere.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Running the apps](#running-the-apps)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Voice commands](#voice-commands)
- [PC server & macros](#pc-server--macros)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- 🎙️ **AI transcription** via OpenAI Whisper — professional accuracy
- ⚡ **Near real-time insertion** — 3-second chunks, text appears as you talk
- 💻 **Streams to any PC** — Windows, macOS, Linux
- 🎯 **Custom voice macros** — "show my calendar," "select all," "new line"
- 🔗 **URL triggers** — speak a phrase, open any webpage
- ⌨️ **Full keyboard control** — Enter, Tab, Ctrl+C, Ctrl+V, function keys
- 🖱️ **Mouse control** — move, click, scroll
- ⚙️ **Configurable chunk size** — tune latency vs. transcription quality
- 📱 **Cross-platform mobile app** — one codebase, iOS + Android

---

## Architecture

```
┌─────────────────┐      HTTPS       ┌──────────────────┐    OpenAI    ┌──────────┐
│  Mobile App     │ ───────────────▶ │  FastAPI Backend │ ───────────▶ │  Whisper │
│  (Expo RN)      │ ◀─────────────── │  + MongoDB       │ ◀─────────── │          │
└─────────────────┘   transcription  └──────────────────┘              └──────────┘
         │                                     │
         │ WebSocket (WiFi)                    │
         ▼                                     ▼
┌─────────────────┐                   ┌──────────────────┐
│  PC Server      │                   │  MongoDB         │
│  (Python)       │                   │  settings/macros │
│  pynput         │                   └──────────────────┘
└─────────────────┘
         │
         ▼
    Your keyboard,
    your mouse,
    your browser
```

Three independent processes, three deploy targets.

---

## Project structure

```
voicekey-ai/
├── frontend/              # Expo React Native app (iOS + Android)
│   ├── app/               # expo-router screens
│   │   ├── (tabs)/
│   │   │   ├── index.tsx          # Voice recording
│   │   │   ├── pc-connect.tsx     # PC pairing
│   │   │   └── settings.tsx       # Macros & config
│   │   └── _layout.tsx
│   ├── src/
│   │   ├── services/api.ts        # Backend client
│   │   ├── store/appStore.ts      # Zustand state
│   │   └── theme.ts
│   └── package.json
│
├── backend/               # FastAPI server (cloud)
│   ├── server.py          # All routes, STT, WS manager
│   ├── requirements.txt
│   └── .env.example
│
├── pc-server/             # Companion app (runs on user's PC)
│   ├── voicekey_server.py # WebSocket listener + keyboard driver
│   ├── build_exe.py       # PyInstaller script → VoiceKey-Server.exe
│   ├── requirements.txt
│   └── README.md
│
└── plan/                  # Planning docs
    ├── plan.md
    ├── technical-brief-owner.md
    └── technical-brief-agents.md
```

---

## Prerequisites

- **Node.js** 18+ and **Yarn** 1.22+
- **Python** 3.9+
- **MongoDB** 5+ (local or Atlas)
- An **OpenAI API key** (for Whisper) OR the **Emergent Universal Key** (if developing on Emergent)
- A phone with **Expo Go** installed, OR Android Studio / Xcode for simulators
- A PC on the **same WiFi network** as the phone (for PC server use)

---

## Local setup

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/voicekey-ai.git
cd voicekey-ai
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

cp .env.example .env
# Edit .env:
#   MONGO_URL="mongodb://localhost:27017"
#   DB_NAME="voicekey_db"
#   EMERGENT_LLM_KEY="sk-..."       # or your OpenAI key
```

### 3. Frontend

```bash
cd ../frontend
yarn install

cp .env.example .env
# Edit .env:
#   EXPO_PUBLIC_BACKEND_URL=http://YOUR_LAN_IP:8001
```

> Find your LAN IP: `ipconfig` (Windows) or `ifconfig` / `ip addr` (macOS/Linux).

### 4. PC server (on your desktop, not the dev machine)

```bash
cd ../pc-server
pip install -r requirements.txt
# Or build the .exe:
# python build_exe.py
```

---

## Running the apps

### Terminal 1 — MongoDB

```bash
mongod --dbpath ~/data/db
```

### Terminal 2 — Backend

```bash
cd backend
source venv/bin/activate
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

Backend is now at `http://localhost:8001/api/health`.

### Terminal 3 — Frontend

```bash
cd frontend
npx expo start
```

Scan the QR with Expo Go, or press `a` / `i` for emulator, `w` for web.

### Terminal 4 — PC server (on your desktop)

```bash
cd pc-server
python voicekey_server.py
```

The server prints its LAN IP and port. Enter those in the mobile app's **PC Connect** tab.

---

## Configuration

### Backend `.env`

| Key | Required | Description |
|-----|----------|-------------|
| `MONGO_URL` | ✅ | MongoDB connection string |
| `DB_NAME` | ✅ | Database name (e.g. `voicekey_db`) |
| `EMERGENT_LLM_KEY` | ✅ | OpenAI/Emergent key for Whisper |

### Frontend `.env`

| Key | Required | Description |
|-----|----------|-------------|
| `EXPO_PUBLIC_BACKEND_URL` | ✅ | Backend URL reachable from the phone |
| `EXPO_PACKAGER_PROXY_URL` | 🔒 | Managed — do not edit |
| `EXPO_PACKAGER_HOSTNAME` | 🔒 | Managed — do not edit |

### In-app settings

Settings UI (`Settings` tab) exposes:
- `immediate_insertion` — send text as each chunk returns (vs. buffer and send on stop)
- `chunk_duration_ms` — 2000 / 3000 / 5000
- `language` — currently `en` only
- `auto_punctuation` — toggle Whisper punctuation
- `pc_connection_enabled` — master switch for the WS send

---

## API reference

Base URL: `${EXPO_PUBLIC_BACKEND_URL}/api`

| Method | Path | Body / Params | Returns |
|--------|------|---------------|---------|
| `GET` | `/health` | — | `{status, stt_available, pc_connections}` |
| `POST` | `/transcribe` | multipart `audio` | `{text, success, error?}` |
| `GET` | `/voice-commands` | — | `VoiceCommand[]` |
| `POST` | `/voice-commands` | `VoiceCommandCreate` | `VoiceCommand` |
| `PUT` | `/voice-commands/{id}` | `VoiceCommandCreate` | `VoiceCommand` |
| `DELETE` | `/voice-commands/{id}` | — | `{message}` |
| `POST` | `/voice-commands/init-defaults` | — | seeds the macros below |
| `GET` | `/settings` | — | `AppSettings` |
| `PUT` | `/settings` | `AppSettingsUpdate` | `AppSettings` |
| `POST` | `/send-to-pc/{client_id}` | `PCCommand` | `{success}` |
| `POST` | `/broadcast-to-pcs` | `PCCommand` | `{success, clients}` |
| `GET` | `/connected-pcs` | — | `{count, client_ids}` |

**WebSocket:** `ws://host:8001/ws/pc/{client_id}` (no `/api` prefix) — the PC server connects here.

### `PCCommand` shape

```json
{
  "command_type": "text" | "key" | "mouse" | "macro",
  "payload": { ... }
}
```

Payload shapes:
- `text`: `{"text": "hello world"}`
- `key`: `{"key": "CTRL+A"}` or `{"key": "ENTER"}`
- `mouse`: `{"action": "move", "x": 10, "y": 20}`
- `macro`: `{"macro": "OPEN_CALENDAR"}` or `{"macro": "OPEN_URL:https://..."}`

---

## Voice commands

Seed defaults via `POST /api/voice-commands/init-defaults`:

| Say | Does |
|-----|------|
| "new line" / "newline" | Press Enter |
| "period" | Insert `.` |
| "comma" | Insert `,` |
| "question mark" | Insert `?` |
| "tab" | Press Tab |
| "backspace" | Press Backspace |
| "select all" | Ctrl+A |
| "copy" | Ctrl+C |
| "paste" | Ctrl+V |
| "delete that" | Select all + delete |
| "show my calendar" | Open Google Calendar |
| "open outlook" | Open outlook.live.com/calendar |

Add your own via **Settings → Add Command**. `action_type` is `text`, `key`, or `macro`.

---

## PC server & macros

The PC server (`pc-server/voicekey_server.py`) listens on port **8765** and uses `pynput` for keyboard + mouse control.

### Supported keys (`KEY_MAP`)

`ENTER, TAB, BACKSPACE, DELETE, SPACE, ESCAPE, UP, DOWN, LEFT, RIGHT, HOME, END, PAGE_UP, PAGE_DOWN, CTRL, ALT, SHIFT, F1–F12`

### Built-in macros

| Macro | Action |
|-------|--------|
| `SELECT_ALL_DELETE` | Ctrl+A then Delete |
| `OPEN_CALENDAR` | Opens `https://calendar.google.com` |
| `OPEN_OUTLOOK_CALENDAR` | Opens Outlook web calendar |
| `OPEN_URL:https://...` | Opens any URL |
| `OPEN_WINDOWS_CALENDAR` | Launches Windows Calendar (Windows only) |

### Build the .exe (Windows)

```bash
cd pc-server
pip install pyinstaller
python build_exe.py
# → dist/VoiceKey-Server.exe
```

---

## Deployment

The mobile app and backend can run on your own infrastructure or stay on Emergent.

- **Backend:** any VPS, Fly.io, Railway, Render — needs Python 3.9+, Mongo, outbound HTTPS to OpenAI.
- **Mobile app:** build via EAS (`eas build -p android`) or publish to App Store / Play Store.
- **PC server:** distributed as a Python script or a bundled `.exe` — the user installs it on their machine.

> ⚠️ The PC server has no authentication by default. For public release, add a shared-token handshake before shipping.

---

## Roadmap

See `/plan/plan.md` for the full roadmap.

**Phase 1 (next build):**
- Transcription history (searchable, exportable)
- Custom vocabulary (jargon, names, acronyms)
- Smart formatting (auto-capitalize, paragraph breaks, number formatting)
- Profiles (Code / Email / Chat / Notes)
- Export to .txt / .md / share sheet
- Live waveform during recording

**Phase 2:**
- Multi-language transcription + auto-detect
- Speaker identification
- AI post-processing (summarize, translate, fix grammar)
- Deep links to Notion / Google Docs / Slack / Gmail

**Phase 3:**
- Offline transcription (on-device model)
- Meeting mode (long-form, auto-chapter, action items)
- Team features (shared vocabulary & profiles)
- Browser extension (replace PC server for web apps)

---

## Troubleshooting

**"Transcription failed" / 500 from `/api/transcribe`**
Backend can't reach Whisper. Check `EMERGENT_LLM_KEY` in `backend/.env` and your network.

**Phone can't reach backend**
Make sure `EXPO_PUBLIC_BACKEND_URL` is your **LAN IP** (not `localhost`) when testing on a physical device.

**PC server not receiving commands**
- Phone and PC on the **same WiFi**?
- Firewall allowing inbound TCP 8765 on the PC?
- Did you enter `ws://PC_IP:8765` (or just the IP) in the PC Connect screen?

**"Unsupported FormDataPart implementation" on physical device**
Audio upload is using the wrong FormData shape. The frontend must use `@/src/utils/upload`'s `uploadForm` helper, not a bare `fetch(uri).blob()`.

**pynput asks for Accessibility access on macOS**
Expected. Grant **System Settings → Privacy → Accessibility → Terminal/Python** and restart the PC server.

**Expo build errors about `expo-av`**
Known deprecation. Migrate to `expo-audio` + `expo-video` when touching audio code.

---

## License

TBD — the owner is undecided on monetization. Default to private / all rights reserved until a license is explicitly added.

---

## Credits

Built on top of Emergent, OpenAI Whisper, Expo, FastAPI, MongoDB, and pynput.
