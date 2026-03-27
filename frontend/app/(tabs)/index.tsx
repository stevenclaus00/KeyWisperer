import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Platform,
  Alert,
  ActivityIndicator,
  Clipboard,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { useAppStore } from '../../src/store/appStore';
import { apiService } from '../../src/services/api';

export default function VoiceScreen() {
  const {
    isRecording,
    setIsRecording,
    transcribedText,
    appendTranscribedText,
    clearTranscribedText,
    isProcessing,
    setIsProcessing,
    settings,
    pcConnection,
    voiceCommands,
  } = useAppStore();

  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Tap microphone to start');
  const recordingRef = useRef<Audio.Recording | null>(null);
  const chunkIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    requestPermissions();
    return () => {
      if (chunkIntervalRef.current) {
        clearInterval(chunkIntervalRef.current);
      }
    };
  }, []);

  const requestPermissions = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      setPermissionGranted(status === 'granted');
      if (status !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Microphone permission is required for voice transcription.'
        );
      }
    } catch (error) {
      console.error('Permission error:', error);
    }
  };

  const processVoiceCommands = (text: string): string => {
    let processedText = text;
    voiceCommands.forEach((cmd) => {
      if (cmd.enabled && cmd.action_type === 'text') {
        const regex = new RegExp(`\\b${cmd.trigger}\\b`, 'gi');
        processedText = processedText.replace(regex, cmd.action);
      }
    });
    return processedText;
  };

  const sendToPC = async (text: string) => {
    if (pcConnection.isConnected && settings.pc_connection_enabled) {
      try {
        await apiService.broadcastToPCs('text', { text });
      } catch (error) {
        console.error('Error sending to PC:', error);
      }
    }
  };

  const startRecording = async () => {
    if (!permissionGranted) {
      Alert.alert('Permission Denied', 'Please grant microphone permission.');
      return;
    }

    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      setRecording(newRecording);
      recordingRef.current = newRecording;
      setIsRecording(true);
      setStatusMessage('Listening...');

      // For immediate insertion, set up chunk processing
      if (settings.immediate_insertion) {
        chunkIntervalRef.current = setInterval(async () => {
          await processChunk();
        }, settings.chunk_duration_ms);
      }
    } catch (error) {
      console.error('Failed to start recording:', error);
      Alert.alert('Error', 'Failed to start recording');
    }
  };

  const processChunk = async () => {
    if (!recordingRef.current) return;

    try {
      // Stop current recording
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();

      // Start a new recording immediately
      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(newRecording);
      recordingRef.current = newRecording;

      // Process the chunk
      if (uri) {
        setIsProcessing(true);
        const response = await apiService.transcribeAudio(uri, 'm4a');
        
        if (response.success && response.text.trim()) {
          const processedText = processVoiceCommands(response.text);
          appendTranscribedText(processedText);
          await sendToPC(processedText);
        }
        setIsProcessing(false);

        // Clean up the file
        await FileSystem.deleteAsync(uri, { idempotent: true });
      }
    } catch (error) {
      console.error('Error processing chunk:', error);
      setIsProcessing(false);
    }
  };

  const stopRecording = async () => {
    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current);
      chunkIntervalRef.current = null;
    }

    if (!recordingRef.current) {
      setIsRecording(false);
      return;
    }

    try {
      setStatusMessage('Processing...');
      setIsProcessing(true);

      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();

      setRecording(null);
      recordingRef.current = null;
      setIsRecording(false);

      if (uri) {
        const response = await apiService.transcribeAudio(uri, 'm4a');
        
        if (response.success && response.text.trim()) {
          const processedText = processVoiceCommands(response.text);
          appendTranscribedText(processedText);
          await sendToPC(processedText);
        } else if (response.error) {
          console.error('Transcription error:', response.error);
        }

        // Clean up
        await FileSystem.deleteAsync(uri, { idempotent: true });
      }

      setStatusMessage('Tap microphone to start');
    } catch (error) {
      console.error('Failed to stop recording:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const copyToClipboard = () => {
    if (transcribedText) {
      Clipboard.setString(transcribedText);
      Alert.alert('Copied', 'Text copied to clipboard!');
    }
  };

  const handleClear = () => {
    clearTranscribedText();
    setStatusMessage('Tap microphone to start');
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>VoiceKey AI</Text>
        <View style={styles.statusBadge}>
          <View
            style={[
              styles.statusDot,
              { backgroundColor: pcConnection.isConnected ? '#00ff88' : '#666' },
            ]}
          />
          <Text style={styles.statusText}>
            {pcConnection.isConnected ? 'PC Connected' : 'PC Disconnected'}
          </Text>
        </View>
      </View>

      <ScrollView style={styles.textContainer} contentContainerStyle={styles.textContent}>
        {transcribedText ? (
          <Text style={styles.transcribedText}>{transcribedText}</Text>
        ) : (
          <Text style={styles.placeholderText}>
            Your transcribed text will appear here...
          </Text>
        )}
        {isProcessing && (
          <View style={styles.processingIndicator}>
            <ActivityIndicator size="small" color="#00d4ff" />
            <Text style={styles.processingText}>Processing...</Text>
          </View>
        )}
      </ScrollView>

      <View style={styles.controlsContainer}>
        <Text style={styles.statusMessage}>{statusMessage}</Text>
        
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={handleClear}
            disabled={!transcribedText || isRecording}
          >
            <Ionicons name="trash-outline" size={24} color="#888" />
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.micButton,
              isRecording && styles.micButtonActive,
            ]}
            onPress={toggleRecording}
            disabled={!permissionGranted}
          >
            <Ionicons
              name={isRecording ? 'stop' : 'mic'}
              size={40}
              color="#fff"
            />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={copyToClipboard}
            disabled={!transcribedText}
          >
            <Ionicons name="copy-outline" size={24} color="#888" />
          </TouchableOpacity>
        </View>

        {settings.immediate_insertion && (
          <View style={styles.modeIndicator}>
            <Ionicons name="flash" size={16} color="#00d4ff" />
            <Text style={styles.modeText}>Immediate Mode</Text>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  statusText: {
    color: '#888',
    fontSize: 12,
  },
  textContainer: {
    flex: 1,
    margin: 16,
    backgroundColor: '#111',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#222',
  },
  textContent: {
    padding: 16,
    minHeight: 200,
  },
  transcribedText: {
    fontSize: 18,
    color: '#fff',
    lineHeight: 28,
  },
  placeholderText: {
    fontSize: 16,
    color: '#555',
    fontStyle: 'italic',
  },
  processingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
  },
  processingText: {
    color: '#00d4ff',
    marginLeft: 8,
    fontSize: 14,
  },
  controlsContainer: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 20,
    borderTopWidth: 1,
    borderTopColor: '#222',
  },
  statusMessage: {
    color: '#888',
    fontSize: 14,
    marginBottom: 20,
  },
  buttonRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 32,
  },
  micButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#00d4ff',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#00d4ff',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  micButtonActive: {
    backgroundColor: '#ff4444',
    shadowColor: '#ff4444',
  },
  secondaryButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333',
  },
  modeIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  modeText: {
    color: '#00d4ff',
    fontSize: 12,
    marginLeft: 6,
  },
});
