import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface VoiceCommand {
  id: string;
  trigger: string;
  action: string;
  action_type: string;
  enabled: boolean;
}

interface AppSettings {
  immediate_insertion: boolean;
  chunk_duration_ms: number;
  language: string;
  auto_punctuation: boolean;
  pc_connection_enabled: boolean;
}

interface PCConnection {
  isConnected: boolean;
  serverUrl: string;
  clientId: string;
}

interface AppState {
  // Transcription
  isRecording: boolean;
  transcribedText: string;
  isProcessing: boolean;
  
  // Settings
  settings: AppSettings;
  voiceCommands: VoiceCommand[];
  
  // PC Connection
  pcConnection: PCConnection;
  
  // Actions
  setIsRecording: (recording: boolean) => void;
  setTranscribedText: (text: string) => void;
  appendTranscribedText: (text: string) => void;
  clearTranscribedText: () => void;
  setIsProcessing: (processing: boolean) => void;
  
  setSettings: (settings: Partial<AppSettings>) => void;
  setVoiceCommands: (commands: VoiceCommand[]) => void;
  
  setPCConnection: (connection: Partial<PCConnection>) => void;
  
  // Persistence
  loadPersistedState: () => Promise<void>;
  persistState: () => Promise<void>;
}

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

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  isRecording: false,
  transcribedText: '',
  isProcessing: false,
  settings: DEFAULT_SETTINGS,
  voiceCommands: [],
  pcConnection: DEFAULT_PC_CONNECTION,
  
  // Actions
  setIsRecording: (recording) => set({ isRecording: recording }),
  
  setTranscribedText: (text) => set({ transcribedText: text }),
  
  appendTranscribedText: (text) => set((state) => ({
    transcribedText: state.transcribedText + (state.transcribedText ? ' ' : '') + text
  })),
  
  clearTranscribedText: () => set({ transcribedText: '' }),
  
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  
  setSettings: (newSettings) => set((state) => ({
    settings: { ...state.settings, ...newSettings }
  })),
  
  setVoiceCommands: (commands) => set({ voiceCommands: commands }),
  
  setPCConnection: (connection) => set((state) => ({
    pcConnection: { ...state.pcConnection, ...connection }
  })),
  
  // Persistence
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
      await AsyncStorage.setItem('pc_connection', JSON.stringify({
        serverUrl: state.pcConnection.serverUrl,
        clientId: state.pcConnection.clientId,
      }));
    } catch (error) {
      console.error('Error persisting state:', error);
    }
  },
}));
