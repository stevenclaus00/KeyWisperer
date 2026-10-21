# VoiceKey AI — Transcription Power-Up Plan

A voice-first productivity app that turns speech into text with professional-grade accuracy and sends it anywhere.
Built around a transcription engine strong enough that writers, coders, and support pros can trust it as their primary input.

## Who it's for

Personal productivity users and professionals who type for a living — writers, developers, customer support agents, consultants, researchers — people who want to talk faster than they type and have their words land in the right app, formatted correctly, the first time.

## Core features and experience

**Transcription history**
Every dictation session is saved automatically. Search past transcripts by keyword, date, or project. Resume, edit, or re-export any session. No more losing a thought because you forgot to copy it.

**Custom vocabulary / dictionary**
Teach the app your names, brands, jargon, and acronyms. "Kubernetes," your coworker "Siobhan," product names, drug names — all transcribed correctly instead of guessed. Especially critical for developers, medical pros, and legal.

**Smart punctuation and formatting**
Automatic sentence capitalization, paragraph breaks after natural pauses, smart quotes, number formatting ("twenty twenty six" → "2026"), and dates. Toggle each on or off per profile.

**Multi-language support**
Transcribe in 50+ languages. Auto-detect or manual select. Especially useful for bilingual professionals and support agents handling international calls.

**Profiles**
Save different setups for different work modes:
- **Code** — technical vocab, no auto-capitalize, aggressive punctuation
- **Email** — formal tone, full sentences, paragraph breaks
- **Chat** — casual, lowercase, short bursts
- **Notes** — raw dump, no formatting
One tap to swap. Each profile remembers its own vocabulary, PC target, and insertion mode.

**Export and share**
Every transcript can be exported as plain text, Markdown, Word doc, or SRT (for video subtitles). Share directly to email, messaging, or save to the Files app.

**Visual recording feedback**
Live waveform while recording so users know the mic is picking them up. Confidence indicator shows when transcription quality may be low (bad audio, background noise) so they can re-record that part.

## User flow

1. Open app, pick a profile (or stay on last-used)
2. Tap the big mic button → start talking
3. Words appear live, inserted into the active target (local text, PC, or clipboard)
4. Pause or stop → final transcript lands in history automatically
5. Edit if needed, export or share to any destination
6. For PC users: same text streams to the connected PC in real time

## UI/UX feel

Dark, focused, keyboard-adjacent — a tool, not a social app. One primary action per screen. The record button dominates the home screen. Everything else lives in tabs or quietly in the corner. Fast and quiet; no celebratory animations, no unnecessary chrome. The app should feel like a professional instrument, not a toy.

Three bottom tabs stay as today: **Voice**, **PC Connect**, **Settings**. History becomes a swipe-down drawer from the Voice screen so it never requires leaving the main flow. Profile switcher sits at the top of the Voice screen as a chip the user taps to cycle.

## Implementation phases

### Phase 1 — MVP (built now)
The transcription foundation professionals can rely on daily.

- **Transcription history** — every session auto-saved with timestamp and preview; list view, search by text, tap to open, edit, re-export, or delete
- **Custom vocabulary** — a list of words/phrases the user adds; fed to Whisper as a prompt to bias recognition
- **Smart punctuation and formatting** — auto-capitalize sentences, paragraph breaks on long pauses, number word → digit conversion, smart quotes; each toggleable
- **Profiles** — create, name, and switch between profiles; each profile stores its own vocabulary, insertion mode, chunk duration, auto-formatting toggles, and default export destination
- **Export** — copy to clipboard, share sheet (iOS/Android native), download as .txt or .md
- **Live waveform** — animated bars while recording so users see the mic is active

### Phase 2 — Later
- Multi-language transcription with auto-detect
- Speaker identification (two-person conversations, meetings)
- Transcript editing with AI (fix grammar, summarize, translate — one tap)
- Deep links to drop transcripts straight into Notion, Google Docs, Slack, Gmail
- Voice-triggered profile switching ("switch to code mode")

### Phase 3 — Later still
- Offline transcription using an on-device model, for privacy-sensitive users
- Meeting mode: long-form recording, auto-chapter, action-item extraction
- Team features: shared vocabulary, shared profiles, usage dashboards
- Browser extension so the PC server isn't needed for web apps

## Assumptions

- OpenAI Whisper remains the transcription engine; vocabulary is passed via Whisper's `prompt` parameter rather than training a custom model
- Transcription history is stored on the backend (MongoDB), not just the device, so it survives app reinstall and syncs across future devices
- A "profile" fully replaces today's single global Settings screen; existing settings become the default profile on first launch
- Smart formatting runs client-side after Whisper returns text, so toggles take effect without re-transcribing
- Phase 1 does not add any new third-party integrations or paid APIs beyond what's already wired up
- Monetization is deferred; the app stays free-feeling through Phase 1 and decisions about paid tiers wait until usage patterns are clearer
