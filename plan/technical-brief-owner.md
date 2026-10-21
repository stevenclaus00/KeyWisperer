# VoiceKey AI — Technical Brief (Owner)

A plain-English technical summary for the project owner. No code, no jargon dumps — just what the system is, how its parts talk to each other, what it can and can't do today, and what the trade-offs are.

---

## What you've built

A three-part voice-to-text system aimed at personal productivity and professionals.

**The pieces:**

1. **Mobile app** (iOS + Android, built with Expo/React Native) — the thing in your hand. Records your voice, shows transcripts, lets you set up voice commands.
2. **Backend server** (Python/FastAPI, cloud) — the middleman. Takes your audio, sends it to OpenAI's Whisper for transcription, saves your settings and voice commands in a database.
3. **PC server** (Python, runs on your Windows/Mac) — the receiver. A small program you install on your computer that listens for commands from the mobile app and acts them out: typing text, pressing keys, opening websites.

The three parts talk to each other over the internet (phone ↔ backend) and your local WiFi (phone ↔ PC).

---

## How a sentence flows through the system

1. You press the mic button in the app and talk.
2. The app chops your voice into 3-second clips and uploads each clip to the backend.
3. The backend forwards the clip to OpenAI Whisper, which returns the text.
4. The text comes back to the app and gets shown on screen.
5. If the PC is connected, the same text is sent over WiFi to your PC server, which types it into whatever window you had focused.
6. If you said a trigger phrase like "show my calendar," the backend/app detects it and sends a command instead of text — your PC opens Google Calendar.

Total round-trip: usually 1–3 seconds per clip.

---

## What it can do today

- Transcribe English speech with Whisper-level accuracy
- Insert text into any app on your PC that accepts typing
- Press key combinations (Ctrl+C, Enter, Tab, etc.)
- Trigger macros (open Calendar, Outlook, custom URLs)
- Store and edit your own voice commands
- Settings for chunk size, auto-punctuation, immediate insertion

## What it can't do today

- No login system — anyone with the backend URL hits the same database
- No history of past transcripts — once a clip is transcribed, the text isn't saved
- No multi-language or language auto-detect — English only
- No custom vocabulary — can't teach it names, jargon, acronyms
- No offline mode — needs internet for Whisper
- No model choice — hardcoded to Whisper via the Emergent key
- No speaker separation — treats everything as one voice
- No actual Bluetooth HID (you asked about this originally) — the PC server is the workaround, and it requires WiFi + the PC companion app running

---

## The important trade-offs

**Expo vs. Native Android**
You originally wanted an Android system keyboard (IME) and a true Bluetooth HID peripheral. Those require native Android code (Java/Kotlin) and can't be built in Expo. The current WiFi + PC-server design is the workaround. It works, but:
- The user has to install a Python server on their PC.
- Phone and PC must be on the same network (or you port-forward).
- It doesn't work when the PC is off, or on a plane, or on a different network.

If you ever want this to be a Play Store product that "just works" with no PC software, you'll eventually need to leave Expo and go to a bare React Native or native Android project.

**Cloud transcription vs. local**
Whisper via OpenAI is accurate and fast but means every word you speak leaves your device. For professionals handling confidential material (lawyers, doctors, finance), that's a non-starter. An on-device model (whisper.cpp or similar) would fix this but is much slower and less accurate on phone hardware.

**Single backend, single database**
Right now there's no concept of users. Settings and commands are global. If you want to ship this to more than one person, you need accounts and per-user data isolation. OAuth (Google/Apple) is the cleanest path.

---

## What's on the roadmap (per the current plan)

**Phase 1 — MVP (next build):**
Transcription history, custom vocabulary, smart formatting, profiles, export, live waveform.

**Phase 2:**
Multi-language, speaker ID, AI editing (summarize/translate/fix grammar), deep links to Notion/Docs/Slack.

**Phase 3:**
Offline transcription, meeting mode, team features, browser extension (replacement for the PC server).

---

## Open decisions you still need to make

1. **OAuth or local-only or both?** You said "OAuth or local" — I need to know which, or whether users pick on first launch.
2. **Which models should be swappable?** Transcription only, or AI editing too, or everything?
3. **Monetization.** You said undecided. That's fine for now, but it changes what we build in Phase 2 (gated features vs. free).
4. **Who hosts the backend when you ship this?** Today it runs on Emergent. For a public release you'll need your own hosting or stay on Emergent's deployment.

---

## Rough cost shape

- **OpenAI Whisper:** ~$0.006 per minute of audio. A heavy user doing 2 hours/day = ~$22/month per user in API costs alone.
- **Backend hosting:** Minimal — a small VPS or Emergent deployment handles hundreds of users easily.
- **MongoDB:** Free tier covers a lot; paid tier starts around $9/month.
- **Not free to run.** If you monetize, Whisper costs set your floor.
