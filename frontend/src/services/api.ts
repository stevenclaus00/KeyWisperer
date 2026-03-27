import Constants from 'expo-constants';

const API_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://voicekey-ai.preview.emergentagent.com';

interface TranscriptionResponse {
  text: string;
  success: boolean;
  error?: string;
}

interface VoiceCommand {
  id: string;
  trigger: string;
  action: string;
  action_type: string;
  enabled: boolean;
}

interface AppSettings {
  id?: string;
  immediate_insertion: boolean;
  chunk_duration_ms: number;
  language: string;
  auto_punctuation: boolean;
  pc_connection_enabled: boolean;
}

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = `${API_BASE_URL}/api`;
    console.log('API Base URL:', this.baseUrl);
  }

  async transcribeAudio(audioUri: string, fileType: string = 'wav'): Promise<TranscriptionResponse> {
    try {
      const formData = new FormData();
      formData.append('audio', {
        uri: audioUri,
        type: `audio/${fileType}`,
        name: `recording.${fileType}`,
      } as any);

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
      await fetch(`${this.baseUrl}/voice-commands/init-defaults`, {
        method: 'POST',
      });
    } catch (error) {
      console.error('Error initializing default commands:', error);
    }
  }

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
        body: JSON.stringify({
          command_type: commandType,
          payload: payload,
        }),
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
        body: JSON.stringify({
          command_type: commandType,
          payload: payload,
        }),
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
export type { TranscriptionResponse, VoiceCommand, AppSettings };
