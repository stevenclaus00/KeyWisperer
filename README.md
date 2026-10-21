# VoiceKey AI

> AI-powered voice transcription with smart formatting, profiles, transcription history, and PC remote control — all from your phone.

---

## Architecture — 3 Pieces

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   📱 Mobile App          🖥️ Backend          💻 PC Server │
│   (Expo React Native)   (FastAPI + MongoDB)  (Python)   │
│                                                         │
│   Your Phone        ←→  Your Server     ←→  Your PC    │
│   port: 3000 (dev)      port: 8001          port: 8765  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

| Piece | Folder | Purpose |
|---|---|---|
| **Frontend** | `/frontend` | Expo React Native app — mic, waveform, profiles, history |
| **Backend** | `/backend` | FastAPI server — Whisper transcription, profiles, history API |
| **PC Server** | `/pc-server` | Lightweight Python WebSocket server — types text & sends keystrokes on your PC |

---

## Prerequisites

- **Node.js** ≥ 18 + **Yarn** (`npm install -g yarn`)
- **Python** ≥ 3.10
- **MongoDB** running locally (`mongodb://localhost:27017`)
- **Expo Go** app on your phone (iOS or Android)
- An **OpenAI API key** (or Emergent LLM key) for Whisper transcription

---

## 1. Backend Setup

```bash
cd backend

# Create a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in `/backend`:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=voicekey_db
EMERGENT_LLM_KEY=your_openai_or_emergent_key_here
```

> **Note:** The `EMERGENT_LLM_KEY` is your OpenAI API key. If you have an Emergent account, you can use your Emergent Universal Key here — it works across OpenAI, Anthropic, and Gemini.

Start the backend:

```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Verify it works:

```bash
curl http://localhost:8001/api/health
# {"status":"healthy","stt_available":true,"pc_connections":0}
```

---

## 2. Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install
```

Create a `.env` file in `/frontend`:

```env
EXPO_PUBLIC_BACKEND_URL=http://YOUR_LOCAL_IP:8001
```

> Replace `YOUR_LOCAL_IP` with your machine's local IP (e.g. `192.168.1.10`). Use `ipconfig` (Windows) or `ifconfig` / `ip a` (macOS/Linux) to find it. **Do not use `localhost`** — your phone needs the actual IP to reach your computer.

Start the frontend:

```bash
yarn expo start
```

This will show a QR code. Scan it with the **Expo Go** app on your phone to launch the app.

> **Web preview:** also accessible at `http://localhost:3000` in your browser.

---

## 3. PC Server Setup

Run this **on your PC** (the machine you want to control with your voice):

```bash
cd pc-server

# Install dependencies
pip install websockets pynput

# Start the server
python voicekey_server.py
```

Output will show your PC's local IP:

```
==================================================
       VoiceKey PC Server
==================================================

  Server started on port 8765

  Connect from VoiceKey app using:
  --> 192.168.1.10:8765
```

In the VoiceKey app, go to the **PC Connect** tab and enter that IP address to pair your phone with your PC.

---

## Running All Three Together

```bash
# Terminal 1 — Backend
cd backend && source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 — Frontend
cd frontend
yarn expo start

# Terminal 3 — PC Server (on your PC)
cd pc-server
python voicekey_server.py
```

---

## Features (Phase 1)

- 🎤 **Voice Transcription** — OpenAI Whisper via microphone
- 🔵 **Profiles** — Switch between Work, Personal, Medical, etc. Each stores its own vocabulary, formatting settings, and chunk duration
- 📚 **Custom Vocabulary** — Feed domain terms to Whisper's `prompt` for better accuracy (e.g. "React Native, TypeScript, FastAPI")
- ✨ **Smart Formatting** — Auto-capitalize sentences, convert spoken numbers to digits (`twenty five → 25`), smart quotes — all client-side
- 🕐 **Transcription History** — Auto-saved after every session. Search, edit, copy, restore, or export
- 📤 **Export** — Copy to clipboard, native Share sheet, save as `.txt` or `.md`
- 💻 **PC Remote Control** — Pair your phone with your PC; transcribed text is typed directly into whatever app is focused on your PC
- ⌨️ **Voice Commands** — Map spoken phrases to keystrokes (e.g. "new line" → Enter, "select all" → Ctrl+A)

---

## Environment Variables Reference

### Backend (`/backend/.env`)

| Variable | Description | Example |
|---|---|---|
| `MONGO_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `voicekey_db` |
| `EMERGENT_LLM_KEY` | OpenAI / Emergent API key for Whisper | `sk-...` |

### Frontend (`/frontend/.env`)

| Variable | Description | Example |
|---|---|---|
| `EXPO_PUBLIC_BACKEND_URL` | Backend URL visible to the phone | `http://192.168.1.10:8001` |

---

## Building a Standalone App

To generate an `.apk` (Android) or `.ipa` (iOS), deploy via the **Emergent Publish** button (top-right in the editor), or use EAS CLI:

```bash
cd frontend
npm install -g eas-cli
eas build --platform android   # or ios
```

---

## PC Server — Building an `.exe` (Windows)

To share the PC server as a standalone executable (no Python required on the recipient's PC):

```bash
cd pc-server
pip install pyinstaller
python build_exe.py
# Output: dist/VoiceKeyServer.exe
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| App can't reach backend | Make sure phone and computer are on the **same WiFi**. Use local IP, not `localhost`. |
| Transcription not working | Check `EMERGENT_LLM_KEY` is set in backend `.env` and the backend is running. |
| PC server not receiving text | Make sure firewall allows port 8765. On Windows: `netsh advfirewall firewall add rule name="VoiceKey" dir=in action=allow protocol=TCP localport=8765` |
| MongoDB connection error | Ensure MongoDB is running: `mongod --dbpath /data/db` |
| Expo Go can't find the app | Run `yarn expo start --tunnel` to use a tunnel URL instead of local IP |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile | React Native (Expo), Expo Router, Zustand |
| Backend | FastAPI, Motor (async MongoDB), Pydantic |
| AI | OpenAI Whisper (`whisper-1`) via `emergentintegrations` |
| Database | MongoDB |
| PC Control | Python `websockets`, `pynput` |
