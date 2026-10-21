import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Profile, TranscriptionHistoryItem } from '../services/api';

// ─── Interfaces ───

export interface VoiceCommand {
  id: string;
  trigger: string;
  action: string;
  action_type: string;
  enabled: boolean;
}

export interface AppSettings {
  immediate_insertion: boolean;
  chunk_duration_ms: number;
  language: string;
  auto_punctuation: boolean;
  pc_connection_enabled: boolean;
}

export interface PCConnection {
  isConnected: boolean;
  serverUrl: string;
  clientId: string;
}

interface AppState {
  // Transcription
  isRecording: boolean;
  transcribedText: string;
  isProcessing: boolean;
  sessionStartTime: number | null;

  // Legacy settings (for PC connect screen backward compat)
  settings: AppSettings;
  voiceCommands: VoiceCommand[];

  // PC Connection
  pcConnection: PCConnection;

  // Profiles
  profiles: Profile[];
  activeProfile: Profile | null;

  // History
  history: TranscriptionHistoryItem[];
  historyLoaded: boolean;

  // Actions – transcription
  setIsRecording: (recording: boolean) => void;
  setTranscribedText: (text: string) => void;
  appendTranscribedText: (text: string) => void;
  clearTranscribedText: () => void;
  setIsProcessing: (processing: boolean) => void;
  setSessionStartTime: (time: number | null) => void;

  // Actions – settings
  setSettings: (settings: Partial<AppSettings>) => void;
  setVoiceCommands: (commands: VoiceCommand[]) => void;

  // Actions – PC
  setPCConnection: (connection: Partial<PCConnection>) => void;

  // Actions – profiles
  setProfiles: (profiles: Profile[]) => void;
  setActiveProfile: (profile: Profile | null) => void;
  updateProfileLocally: (profile: Profile) => void;

  // Actions – history
  setHistory: (items: TranscriptionHistoryItem[]) => void;
  prependHistory: (item: TranscriptionHistoryItem) => void;
  removeHistoryItem: (id: string) => void;
  updateHistoryItemLocally: (item: TranscriptionHistoryItem) => void;
  setHistoryLoaded: (loaded: boolean) => void;

  // Persistence
  loadPersistedState: () => Promise<void>;
  persistState: () => Promise<void>;
}

// ─── Defaults ───

const DEFAULT_SETTINGS: AppSettings = {
  immediate_insertion: true,
  chunk_duration_ms: 3000,
  language: 'en',
  auto_punctuation: true,
  pc_connection_enabled: true,
};

const DEFAULT_PC_CONNECTION: PCConnection = {
  isConnected: false,
  serverUrl: '',
  clientId: `mobile-${Date.now()}`,
};

// ─── Store ───

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  isRecording: false,
  transcribedText: '',
  isProcessing: false,
  sessionStartTime: null,
  settings: DEFAULT_SETTINGS,
  voiceCommands: [],
  pcConnection: DEFAULT_PC_CONNECTION,
  profiles: [],
  activeProfile: null,
  history: [],
  historyLoaded: false,

  // ── Transcription actions ──
  setIsRecording: (recording) => set({ isRecording: recording }),
  setTranscribedText: (text) => set({ transcribedText: text }),
  appendTranscribedText: (text) =>
    set((state) => ({
      transcribedText:
        state.transcribedText + (state.transcribedText ? ' ' : '') + text,
    })),
  clearTranscribedText: () => set({ transcribedText: '' }),
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  setSessionStartTime: (time) => set({ sessionStartTime: time }),

  // ── Settings actions ──
  setSettings: (newSettings) =>
    set((state) => ({ settings: { ...state.settings, ...newSettings } })),
  setVoiceCommands: (commands) => set({ voiceCommands: commands }),

  // ── PC actions ──
  setPCConnection: (connection) =>
    set((state) => ({
      pcConnection: { ...state.pcConnection, ...connection },
    })),

  // ── Profile actions ──
  setProfiles: (profiles) => set({ profiles }),
  setActiveProfile: (profile) => set({ activeProfile: profile }),
  updateProfileLocally: (updatedProfile) =>
    set((state) => ({
      profiles: state.profiles.map((p) =>
        p.id === updatedProfile.id ? updatedProfile : p
      ),
      activeProfile:
        state.activeProfile?.id === updatedProfile.id
          ? updatedProfile
          : state.activeProfile,
    })),

  // ── History actions ──
  setHistory: (items) => set({ history: items }),
  prependHistory: (item) =>
    set((state) => ({ history: [item, ...state.history] })),
  removeHistoryItem: (id) =>
    set((state) => ({ history: state.history.filter((h) => h.id !== id) })),
  updateHistoryItemLocally: (updatedItem) =>
    set((state) => ({
      history: state.history.map((h) =>
        h.id === updatedItem.id ? updatedItem : h
      ),
    })),
  setHistoryLoaded: (loaded) => set({ historyLoaded: loaded }),

  // ── Persistence ──
  loadPersistedState: async () => {
    try {
      const settingsJson = await AsyncStorage.getItem('app_settings');
      const pcConnectionJson = await AsyncStorage.getItem('pc_connection');

      if (settingsJson) {
        set({ settings: JSON.parse(settingsJson) });
      }
      if (pcConnectionJson) {
        const pcData = JSON.parse(pcConnectionJson);
        set({ pcConnection: { ...pcData, isConnected: false } });
      }
    } catch (error) {
      console.error('Error loading persisted state:', error);
    }
  },

  persistState: async () => {
    try {
      const state = get();
      await AsyncStorage.setItem('app_settings', JSON.stringify(state.settings));
      await AsyncStorage.setItem(
        'pc_connection',
        JSON.stringify({
          serverUrl: state.pcConnection.serverUrl,
          clientId: state.pcConnection.clientId,
        })
      );
    } catch (error) {
      console.error('Error persisting state:', error);
    }
  },
}));
