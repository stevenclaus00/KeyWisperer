import Constants from 'expo-constants';

const API_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://voicekey-ai.preview.emergentagent.com';

// ─── Interfaces ───

export interface TranscriptionResponse {
  text: string;
  success: boolean;
  error?: string;
  history_id?: string;
}

export interface VoiceCommand {
  id: string;
  trigger: string;
  action: string;
  action_type: string;
  enabled: boolean;
}

export interface AppSettings {
  id?: string;
  immediate_insertion: boolean;
  chunk_duration_ms: number;
  language: string;
  auto_punctuation: boolean;
  pc_connection_enabled: boolean;
}

export interface Profile {
  id: string;
  name: string;
  custom_vocabulary: string[];
  immediate_insertion: boolean;
  chunk_duration_ms: number;
  language: string;
  auto_punctuation: boolean;
  pc_connection_enabled: boolean;
  auto_capitalize: boolean;
  paragraph_breaks: boolean;
  number_formatting: boolean;
  smart_quotes: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileCreate {
  name: string;
  custom_vocabulary?: string[];
  immediate_insertion?: boolean;
  chunk_duration_ms?: number;
  language?: string;
  auto_punctuation?: boolean;
  pc_connection_enabled?: boolean;
  auto_capitalize?: boolean;
  paragraph_breaks?: boolean;
  number_formatting?: boolean;
  smart_quotes?: boolean;
}

export interface ProfileUpdate {
  name?: string;
  custom_vocabulary?: string[];
  immediate_insertion?: boolean;
  chunk_duration_ms?: number;
  language?: string;
  auto_punctuation?: boolean;
  pc_connection_enabled?: boolean;
  auto_capitalize?: boolean;
  paragraph_breaks?: boolean;
  number_formatting?: boolean;
  smart_quotes?: boolean;
}

export interface TranscriptionHistoryItem {
  id: string;
  text: string;
  profile_id: string;
  profile_name: string;
  timestamp: string;
  word_count: number;
  duration_seconds?: number;
}

// ─── API Service ───

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = `${API_BASE_URL}/api`;
    console.log('API Base URL:', this.baseUrl);
  }

  // ── Transcription ──

  async transcribeAudio(
    audioUri: string,
    fileType: string = 'wav',
    profileId?: string,
  ): Promise<TranscriptionResponse> {
    try {
      const formData = new FormData();
      formData.append('audio', {
        uri: audioUri,
        type: `audio/${fileType}`,
        name: `recording.${fileType}`,
      } as any);

      if (profileId) {
        formData.append('profile_id', profileId);
      }

      const response = await fetch(`${this.baseUrl}/transcribe`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Transcription error:', error);
      return {
        text: '',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // ── Voice Commands ──

  async getVoiceCommands(): Promise<VoiceCommand[]> {
    try {
      const response = await fetch(`${this.baseUrl}/voice-commands`);
      if (!response.ok) throw new Error('Failed to fetch voice commands');
      return await response.json();
    } catch (error) {
      console.error('Error fetching voice commands:', error);
      return [];
    }
  }

  async createVoiceCommand(command: Omit<VoiceCommand, 'id'>): Promise<VoiceCommand | null> {
    try {
      const response = await fetch(`${this.baseUrl}/voice-commands`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(command),
      });
      if (!response.ok) throw new Error('Failed to create voice command');
      return await response.json();
    } catch (error) {
      console.error('Error creating voice command:', error);
      return null;
    }
  }

  async deleteVoiceCommand(commandId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/voice-commands/${commandId}`, {
        method: 'DELETE',
      });
      return response.ok;
    } catch (error) {
      console.error('Error deleting voice command:', error);
      return false;
    }
  }

  async initDefaultCommands(): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/voice-commands/init-defaults`, { method: 'POST' });
    } catch (error) {
      console.error('Error initializing default commands:', error);
    }
  }

  // ── Legacy Settings ──

  async getSettings(): Promise<AppSettings | null> {
    try {
      const response = await fetch(`${this.baseUrl}/settings`);
      if (!response.ok) throw new Error('Failed to fetch settings');
      return await response.json();
    } catch (error) {
      console.error('Error fetching settings:', error);
      return null;
    }
  }

  async updateSettings(settings: Partial<AppSettings>): Promise<AppSettings | null> {
    try {
      const response = await fetch(`${this.baseUrl}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!response.ok) throw new Error('Failed to update settings');
      return await response.json();
    } catch (error) {
      console.error('Error updating settings:', error);
      return null;
    }
  }

  // ── Profiles ──

  async getProfiles(): Promise<Profile[]> {
    try {
      const response = await fetch(`${this.baseUrl}/profiles`);
      if (!response.ok) throw new Error('Failed to fetch profiles');
      return await response.json();
    } catch (error) {
      console.error('Error fetching profiles:', error);
      return [];
    }
  }

  async getActiveProfile(): Promise<Profile | null> {
    try {
      const response = await fetch(`${this.baseUrl}/profiles/active`);
      if (!response.ok) throw new Error('Failed to fetch active profile');
      return await response.json();
    } catch (error) {
      console.error('Error fetching active profile:', error);
      return null;
    }
  }

  async createProfile(profile: ProfileCreate): Promise<Profile | null> {
    try {
      const response = await fetch(`${this.baseUrl}/profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
      if (!response.ok) throw new Error('Failed to create profile');
      return await response.json();
    } catch (error) {
      console.error('Error creating profile:', error);
      return null;
    }
  }

  async updateProfile(profileId: string, update: ProfileUpdate): Promise<Profile | null> {
    try {
      const response = await fetch(`${this.baseUrl}/profiles/${profileId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update),
      });
      if (!response.ok) throw new Error('Failed to update profile');
      return await response.json();
    } catch (error) {
      console.error('Error updating profile:', error);
      return null;
    }
  }

  async activateProfile(profileId: string): Promise<Profile | null> {
    try {
      const response = await fetch(`${this.baseUrl}/profiles/${profileId}/activate`, {
        method: 'PUT',
      });
      if (!response.ok) throw new Error('Failed to activate profile');
      return await response.json();
    } catch (error) {
      console.error('Error activating profile:', error);
      return null;
    }
  }

  async deleteProfile(profileId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/profiles/${profileId}`, {
        method: 'DELETE',
      });
      return response.ok;
    } catch (error) {
      console.error('Error deleting profile:', error);
      return false;
    }
  }

  // ── Transcription History ──

  async getHistory(limit: number = 50): Promise<TranscriptionHistoryItem[]> {
    try {
      const response = await fetch(`${this.baseUrl}/history?limit=${limit}`);
      if (!response.ok) throw new Error('Failed to fetch history');
      return await response.json();
    } catch (error) {
      console.error('Error fetching history:', error);
      return [];
    }
  }

  async saveToHistory(
    text: string,
    profileId: string = '',
    profileName: string = 'Default',
    durationSeconds?: number,
  ): Promise<TranscriptionHistoryItem | null> {
    try {
      const response = await fetch(`${this.baseUrl}/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          profile_id: profileId,
          profile_name: profileName,
          duration_seconds: durationSeconds,
        }),
      });
      if (!response.ok) throw new Error('Failed to save to history');
      return await response.json();
    } catch (error) {
      console.error('Error saving to history:', error);
      return null;
    }
  }

  async updateHistoryItem(itemId: string, text: string): Promise<TranscriptionHistoryItem | null> {
    try {
      const response = await fetch(`${this.baseUrl}/history/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) throw new Error('Failed to update history item');
      return await response.json();
    } catch (error) {
      console.error('Error updating history item:', error);
      return null;
    }
  }

  async deleteHistoryItem(itemId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/history/${itemId}`, {
        method: 'DELETE',
      });
      return response.ok;
    } catch (error) {
      console.error('Error deleting history item:', error);
      return false;
    }
  }

  async clearHistory(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/history`, { method: 'DELETE' });
      return response.ok;
    } catch (error) {
      console.error('Error clearing history:', error);
      return false;
    }
  }

  // ── PC Connection ──

  async getConnectedPCs(): Promise<{ count: number; client_ids: string[] }> {
    try {
      const response = await fetch(`${this.baseUrl}/connected-pcs`);
      if (!response.ok) throw new Error('Failed to get connected PCs');
      return await response.json();
    } catch (error) {
      console.error('Error getting connected PCs:', error);
      return { count: 0, client_ids: [] };
    }
  }

  async sendToPC(clientId: string, commandType: string, payload: any): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/send-to-pc/${clientId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command_type: commandType, payload }),
      });
      return response.ok;
    } catch (error) {
      console.error('Error sending to PC:', error);
      return false;
    }
  }

  async broadcastToPCs(commandType: string, payload: any): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/broadcast-to-pcs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command_type: commandType, payload }),
      });
      return response.ok;
    } catch (error) {
      console.error('Error broadcasting to PCs:', error);
      return false;
    }
  }

  async healthCheck(): Promise<{ status: string; stt_available: boolean; pc_connections: number } | null> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      if (!response.ok) throw new Error('Health check failed');
      return await response.json();
    } catch (error) {
      console.error('Health check error:', error);
      return null;
    }
  }
}

export const apiService = new ApiService();
