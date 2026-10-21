# VoiceKey AI — Technical Brief (Coding Agents)

Context handoff for any coding agent (Cursor, Claude Code, Copilot, another Emergent session, etc.) picking up this codebase. Assumes the reader can read code and docs independently but has zero project context.

---

## Project identity

- **Name:** VoiceKey AI
- **Purpose:** Real-time speech-to-text on mobile that streams transcribed text to a desktop PC over WebSocket, acting as a soft keyboard/macro peripheral.
- **Repo layout:** monorepo with three independently runnable units: `frontend/` (Expo), `backend/` (FastAPI), `pc-server/` (Python daemon).

---

## Stack

### Frontend (`frontend/`)
- **Framework:** Expo SDK 54, React Native 0.81.5, React 19.1
- **Router:** `expo-router` v6 (file-based)
- **State:** Zustand (`src/store/appStore.ts`)
- **Audio capture:** `expo-av`
- **HTTP:** fetch; service wrapper at `src/services/api.ts`
- **Env:** `EXPO_PUBLIC_BACKEND_URL` consumed via `process.env.EXPO_PUBLIC_BACKEND_URL`
- **Package manager:** Yarn 1.22 (declared via `packageManager` field — respect it)

### Backend (`backend/`)
- **Framework:** FastAPI, uvicorn
- **DB driver:** motor (async MongoDB)
- **STT provider:** `emergentintegrations.llm.openai.OpenAISpeechToText` → OpenAI Whisper (`model="whisper-1"`, hardcoded, English-only)
- **Auth:** key gated by `EMERGENT_LLM_KEY` env var; no user auth
- **Routing convention:** every public route prefixed with `/api` (K8s ingress rule). WebSocket endpoint is the one exception: `/ws/pc/{client_id}`.
- **Env file:** `backend/.env` with `MONGO_URL`, `DB_NAME`, `EMERGENT_LLM_KEY`

### PC Server (`pc-server/`)
- **Runtime:** Python 3.9+, `websockets`, `pynput`, stdlib `webbrowser`/`subprocess`
- **Port:** 8765 (WebSocket, no TLS)
- **Builds to EXE via** `build_exe.py` → PyInstaller
- **Not deployed server-side.** Ships as source + optional .exe to the end user.

---

## File map (significant files only)

```
frontend/
├── app/
│   ├── _layout.tsx                 # Root layout; icon pre-warm logic — DO NOT REMOVE
│   ├── (tabs)/
│   │   ├── _layout.tsx             # Tab navigator
│   │   ├── index.tsx               # Voice recording UI, chunked upload loop
│   │   ├── pc-connect.tsx          # WS connection to PC server, IP input
│   │   └── settings.tsx            # Macro CRUD + settings form
├── src/
│   ├── services/api.ts             # fetch wrappers for backend
│   ├── store/appStore.ts           # Zustand store: settings, commands, PC conn state
│   └── theme.ts                    # Design tokens (color block from design_guidelines.json)

backend/
├── server.py                        # Everything: STT, CRUD, WS manager
├── requirements.txt
└── .env

pc-server/
├── voicekey_server.py              # WS server, keyboard/mouse/macro dispatcher
├── build_exe.py                    # PyInstaller script
└── README.md                       # End-user setup instructions
```

---

## Data model (MongoDB)

Three collections, all with UUID `id` field (not `_id`):

### `app_settings` (singleton)
```python
{
  "id": str,
  "immediate_insertion": bool,       # True = send text to PC as each chunk returns
  "chunk_duration_ms": int,          # Default 3000
  "language": str,                   # "en"
  "auto_punctuation": bool,
  "pc_connection_enabled": bool,
  "updated_at": datetime
}
```

### `voice_commands`
```python
{
  "id": str,
  "trigger": str,                    # Case-insensitive phrase match on transcription
  "action": str,                     # "ENTER", "CTRL+A", "OPEN_CALENDAR", "OPEN_URL:https://..."
  "action_type": str,                # "text" | "key" | "macro"
  "enabled": bool,
  "created_at": datetime
}
```

### `status_checks` (legacy, unused — leave or purge)

**Mongo rules:**
- Always exclude `_id` from responses (`find({}, {"_id": 0})` or project through Pydantic).
- Pydantic models with `BaseModel(**doc)` work only if you strip `_id` first OR the model ignores unknown fields.
- UTC-aware timestamps: `datetime.now(timezone.utc)`, never `datetime.utcnow()`.

---

## API surface

All HTTP routes under `/api`, all return `application/json`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check; returns STT availability + PC connection count |
| POST | `/api/transcribe` | multipart `audio` file → `{text, success, error?}` |
| GET | `/api/voice-commands` | List all macros |
| POST | `/api/voice-commands` | Create macro |
| PUT | `/api/voice-commands/{id}` | Update macro |
| DELETE | `/api/voice-commands/{id}` | Delete macro |
| POST | `/api/voice-commands/init-defaults` | Seed default macros (idempotent) |
| GET | `/api/settings` | Get (creates default on first call) |
| PUT | `/api/settings` | Partial update |
| POST | `/api/send-to-pc/{client_id}` | Push command to specific PC |
| POST | `/api/broadcast-to-pcs` | Push to all connected PCs |
| GET | `/api/connected-pcs` | List connected `client_id`s |
| WS | `/ws/pc/{client_id}` | PC server connects here (no `/api` prefix) |

### Audio upload contract
- Field name: `audio`
- Accepted extensions: `mp3, mp4, mpeg, mpga, m4a, wav, webm`
- Server defaults to `wav` if unknown.
- Mobile uploads **must** go through `@/src/utils/upload` (`uploadForm`) — do NOT `form.append(field, {uri, name, type})`, do NOT `fetch(uri).blob()` on native. The `expo/fetch` native global will throw `Unsupported FormDataPart implementation`.

### PC command protocol (mobile → backend → PC)
Backend forwards JSON over WS to the PC:
```json
{"type": "text" | "key" | "mouse" | "macro", "payload": {...}}
```

**text:** `{"text": "hello world"}`
**key:** `{"key": "CTRL+A"}` or `{"key": "ENTER"}` (see `KEY_MAP` in `pc-server/voicekey_server.py`)
**mouse:** `{"action": "move"|"click"|"scroll", "x", "y", "button", "dx", "dy"}`
**macro:** `{"macro": "OPEN_CALENDAR"}` or `{"macro": "OPEN_URL:https://..."}`

---

## Runtime assumptions / environment

- **Container:** Kubernetes pod on Emergent preview; supervisor manages `expo` + `backend` services.
- **Metro port:** 3000/8081; backend binds `0.0.0.0:8001`.
- **Ingress:** `/api/*` → backend:8001, everything else → frontend:3000.
- **Protected env vars:** `EXPO_PACKAGER_PROXY_URL`, `EXPO_PACKAGER_HOSTNAME` in `frontend/.env`; `MONGO_URL` in `backend/.env`. Never modify.
- **Never modify:** `metro.config.js`, `eas.json`, the icon pre-warm block in `app/_layout.tsx`.

---

## Known limitations (keep in mind before "fixing")

1. **No user auth.** Settings and commands are global. Adding users requires schema migration (add `user_id` to both collections) + an auth layer. Owner has not committed to OAuth vs. local yet.
2. **No transcript persistence.** Transcriptions return and are discarded. Adding history is Phase 1 of the next plan.
3. **No streaming STT.** Whisper is batch — the chunked-upload approach fakes streaming at 3s granularity. True streaming requires Deepgram/AssemblyAI/local VAD.
4. **Hardcoded `whisper-1`, `language="en"`, `response_format="json"`** in `backend/server.py` → `transcribe_audio`. Making these configurable is pending.
5. **PC server has zero authentication.** Anyone on the local network can connect to port 8765 and type on the user's PC. Fine for MVP, must be solved before public release (shared token at minimum).
6. **No rate limiting.** `/api/transcribe` is unprotected; a loop can rack up OpenAI costs.
7. **CORS is `*`.** OK for preview, needs tightening for production.

---

## When adding features — rules of the house

- Any auth work (login, OAuth, JWT, sessions, password reset, admin seed, brute-force protection) **MUST** go through `integration_expert` before writing code. No exceptions.
- Any 3rd-party integration (new model provider, Stripe, Resend, etc.) **MUST** go through `integration_expert`. Do not install SDKs blind.
- Local key-value storage on device: use `@/src/utils/storage`. Do not import `@react-native-async-storage/async-storage`, `expo-secure-store`, `expo-sqlite/kv-store`, or `react-native-mmkv` directly.
- File uploads: `@/src/utils/upload` only.
- Colors: `src/theme.ts` only. Literal hex only when the color must stay identical light/dark (e.g. third-party brand).
- `requirements.txt`: `pip install X && pip freeze > backend/requirements.txt`. Never hand-edit.
- `package.json`: `yarn expo install <pkg>`. Never hand-edit versions.
- Every interactive element needs a `testID` in kebab-case by role (`login-submit-button`, not `blue-button`).
- Soft-delete only. Never destroy data. `deleted_at` flag.

---

## Known deprecated packages — do not use

- `expo-av` (currently used, but migrate to `expo-audio` + `expo-video` when touching audio code)
- `expo-barcode-scanner` → `expo-camera`
- `expo-background-fetch` → `expo-background-task`
- `@expo-google-fonts/*` → load via `expo-font` directly
- `@expo/vector-icons` → `@react-native-vector-icons/*`

---

## Testing

- `/app/test_result.md` holds the latest backend test report.
- Testing credentials (if auth is added): `/app/memory/test_credentials.md` — update whenever auth seed data changes.
- For any new feature touching backend + frontend, dispatch `testing_agent` after implementation. Do not self-certify UI by taking a web screenshot — NativeTabs don't render on web preview.

---

## Immediate next build (Phase 1 of current plan)

See `/app/plan/plan.md`. Scope:
- Transcription history (new collection, list/search/export)
- Custom vocabulary (array passed as Whisper `prompt`)
- Smart formatting (client-side post-processing)
- Profiles (replaces singleton `app_settings` with a `profiles` collection + active profile pointer)
- Export (.txt, .md, share sheet)
- Live waveform during recording

Two open decisions block Phase 2 and should be answered before Phase 1 ships:
1. OAuth vs. local-only vs. user-choice-on-first-launch
2. Which AI tasks should be model-swappable

---

## Starting a session (quick orientation checklist)

1. Read `/app/plan/plan.md` for current roadmap.
2. Read `/app/test_result.md` for last test state.
3. `backend/server.py` is intentionally single-file; split only if it exceeds ~800 lines.
4. Frontend: start at `app/(tabs)/index.tsx` — that's the recording loop and the heart of the app.
5. If a feature touches audio capture, read `expo-av` → `expo-audio` migration notes before writing code.
