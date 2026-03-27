import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Switch,
  TextInput,
  Alert,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAppStore } from '../../src/store/appStore';
import { apiService, VoiceCommand } from '../../src/services/api';

export default function SettingsScreen() {
  const {
    settings,
    setSettings,
    voiceCommands,
    setVoiceCommands,
    persistState,
    loadPersistedState,
  } = useAppStore();

  const [isLoading, setIsLoading] = useState(true);
  const [showAddCommand, setShowAddCommand] = useState(false);
  const [newTrigger, setNewTrigger] = useState('');
  const [newAction, setNewAction] = useState('');
  const [newActionType, setNewActionType] = useState<'text' | 'key' | 'macro'>('text');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      await loadPersistedState();
      
      // Fetch settings from server
      const serverSettings = await apiService.getSettings();
      if (serverSettings) {
        setSettings(serverSettings);
      }

      // Initialize default commands if needed
      await apiService.initDefaultCommands();

      // Fetch voice commands
      const commands = await apiService.getVoiceCommands();
      setVoiceCommands(commands);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateSetting = async (key: string, value: any) => {
    setSettings({ [key]: value });
    await apiService.updateSettings({ [key]: value });
    await persistState();
  };

  const addVoiceCommand = async () => {
    if (!newTrigger.trim() || !newAction.trim()) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    const command = await apiService.createVoiceCommand({
      trigger: newTrigger.toLowerCase(),
      action: newAction,
      action_type: newActionType,
      enabled: true,
    });

    if (command) {
      setVoiceCommands([...voiceCommands, command]);
      setNewTrigger('');
      setNewAction('');
      setShowAddCommand(false);
    } else {
      Alert.alert('Error', 'Failed to create voice command');
    }
  };

  const deleteCommand = async (commandId: string) => {
    Alert.alert(
      'Delete Command',
      'Are you sure you want to delete this command?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            const success = await apiService.deleteVoiceCommand(commandId);
            if (success) {
              setVoiceCommands(voiceCommands.filter((c) => c.id !== commandId));
            }
          },
        },
      ]
    );
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#00d4ff" />
          <Text style={styles.loadingText}>Loading settings...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.scrollView}>
        <View style={styles.header}>
          <Text style={styles.title}>Settings</Text>
          <Text style={styles.subtitle}>Configure voice transcription</Text>
        </View>

        {/* Transcription Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Transcription</Text>

          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={styles.settingLabel}>Immediate Insertion</Text>
              <Text style={styles.settingDescription}>
                Insert text as you speak (chunks every {settings.chunk_duration_ms / 1000}s)
              </Text>
            </View>
            <Switch
              value={settings.immediate_insertion}
              onValueChange={(value) => updateSetting('immediate_insertion', value)}
              trackColor={{ false: '#333', true: '#00d4ff' }}
              thumbColor="#fff"
            />
          </View>

          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={styles.settingLabel}>Auto Punctuation</Text>
              <Text style={styles.settingDescription}>
                Automatically add punctuation marks
              </Text>
            </View>
            <Switch
              value={settings.auto_punctuation}
              onValueChange={(value) => updateSetting('auto_punctuation', value)}
              trackColor={{ false: '#333', true: '#00d4ff' }}
              thumbColor="#fff"
            />
          </View>

          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={styles.settingLabel}>PC Connection</Text>
              <Text style={styles.settingDescription}>
                Enable sending text to connected PC
              </Text>
            </View>
            <Switch
              value={settings.pc_connection_enabled}
              onValueChange={(value) => updateSetting('pc_connection_enabled', value)}
              trackColor={{ false: '#333', true: '#00d4ff' }}
              thumbColor="#fff"
            />
          </View>
        </View>

        {/* Voice Commands */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Voice Commands</Text>
            <TouchableOpacity
              style={styles.addButton}
              onPress={() => setShowAddCommand(true)}
            >
              <Ionicons name="add" size={20} color="#fff" />
            </TouchableOpacity>
          </View>
          <Text style={styles.sectionDescription}>
            Map spoken phrases to actions
          </Text>

          {voiceCommands.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="mic-off" size={40} color="#444" />
              <Text style={styles.emptyText}>No voice commands configured</Text>
            </View>
          ) : (
            voiceCommands.map((command) => (
              <View key={command.id} style={styles.commandCard}>
                <View style={styles.commandInfo}>
                  <Text style={styles.commandTrigger}>"{command.trigger}"</Text>
                  <View style={styles.commandAction}>
                    <View style={[styles.actionTypeBadge, getActionTypeBadgeStyle(command.action_type)]}>
                      <Text style={styles.actionTypeText}>{command.action_type}</Text>
                    </View>
                    <Text style={styles.commandActionText}>{command.action}</Text>
                  </View>
                </View>
                <TouchableOpacity
                  style={styles.deleteButton}
                  onPress={() => deleteCommand(command.id)}
                >
                  <Ionicons name="trash-outline" size={18} color="#ff4444" />
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>

        {/* Chunk Duration */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Advanced</Text>
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={styles.settingLabel}>Chunk Duration</Text>
              <Text style={styles.settingDescription}>
                Audio chunk size for immediate mode
              </Text>
            </View>
            <View style={styles.durationButtons}>
              {[2000, 3000, 5000].map((duration) => (
                <TouchableOpacity
                  key={duration}
                  style={[
                    styles.durationButton,
                    settings.chunk_duration_ms === duration && styles.durationButtonActive,
                  ]}
                  onPress={() => updateSetting('chunk_duration_ms', duration)}
                >
                  <Text
                    style={[
                      styles.durationButtonText,
                      settings.chunk_duration_ms === duration && styles.durationButtonTextActive,
                    ]}
                  >
                    {duration / 1000}s
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>

        {/* About */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          <View style={styles.aboutCard}>
            <Text style={styles.aboutTitle}>VoiceKey AI</Text>
            <Text style={styles.aboutVersion}>Version 1.0.0</Text>
            <Text style={styles.aboutDescription}>
              AI-powered voice transcription with PC remote control capabilities.
              Uses OpenAI Whisper for accurate speech-to-text conversion.
            </Text>
          </View>
        </View>
      </ScrollView>

      {/* Add Command Modal */}
      <Modal
        visible={showAddCommand}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowAddCommand(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Voice Command</Text>
              <TouchableOpacity onPress={() => setShowAddCommand(false)}>
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>

            <Text style={styles.inputLabel}>Trigger Phrase</Text>
            <TextInput
              style={styles.modalInput}
              placeholder='e.g., "new paragraph"'
              placeholderTextColor="#555"
              value={newTrigger}
              onChangeText={setNewTrigger}
              autoCapitalize="none"
            />

            <Text style={styles.inputLabel}>Action</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="e.g., ENTER or custom text"
              placeholderTextColor="#555"
              value={newAction}
              onChangeText={setNewAction}
            />

            <Text style={styles.inputLabel}>Action Type</Text>
            <View style={styles.actionTypeSelector}>
              {(['text', 'key', 'macro'] as const).map((type) => (
                <TouchableOpacity
                  key={type}
                  style={[
                    styles.actionTypeButton,
                    newActionType === type && styles.actionTypeButtonActive,
                  ]}
                  onPress={() => setNewActionType(type)}
                >
                  <Text
                    style={[
                      styles.actionTypeButtonText,
                      newActionType === type && styles.actionTypeButtonTextActive,
                    ]}
                  >
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <TouchableOpacity style={styles.saveButton} onPress={addVoiceCommand}>
              <Text style={styles.saveButtonText}>Save Command</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const getActionTypeBadgeStyle = (type: string) => {
  switch (type) {
    case 'key':
      return { backgroundColor: 'rgba(255, 159, 64, 0.2)', borderColor: '#ff9f40' };
    case 'macro':
      return { backgroundColor: 'rgba(153, 102, 255, 0.2)', borderColor: '#9966ff' };
    default:
      return { backgroundColor: 'rgba(0, 212, 255, 0.2)', borderColor: '#00d4ff' };
  }
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#888',
    marginTop: 12,
  },
  header: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#888',
  },
  section: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  sectionDescription: {
    fontSize: 13,
    color: '#666',
    marginBottom: 16,
  },
  addButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#00d4ff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  settingInfo: {
    flex: 1,
    marginRight: 16,
  },
  settingLabel: {
    fontSize: 15,
    color: '#fff',
    marginBottom: 2,
  },
  settingDescription: {
    fontSize: 12,
    color: '#666',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyText: {
    color: '#555',
    marginTop: 12,
  },
  commandCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#222',
  },
  commandInfo: {
    flex: 1,
  },
  commandTrigger: {
    fontSize: 15,
    color: '#fff',
    fontWeight: '500',
    marginBottom: 4,
  },
  commandAction: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionTypeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    marginRight: 8,
  },
  actionTypeText: {
    fontSize: 10,
    color: '#888',
    textTransform: 'uppercase',
  },
  commandActionText: {
    fontSize: 13,
    color: '#888',
  },
  deleteButton: {
    padding: 8,
  },
  durationButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  durationButton: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
  },
  durationButtonActive: {
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    borderColor: '#00d4ff',
  },
  durationButtonText: {
    color: '#888',
    fontSize: 14,
  },
  durationButtonTextActive: {
    color: '#00d4ff',
  },
  aboutCard: {
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#222',
  },
  aboutTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  aboutVersion: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  aboutDescription: {
    fontSize: 13,
    color: '#888',
    marginTop: 12,
    lineHeight: 20,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#111',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 40,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  inputLabel: {
    fontSize: 14,
    color: '#888',
    marginBottom: 8,
  },
  modalInput: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
    paddingHorizontal: 16,
    height: 50,
    color: '#fff',
    fontSize: 16,
    marginBottom: 16,
  },
  actionTypeSelector: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 24,
  },
  actionTypeButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
    alignItems: 'center',
  },
  actionTypeButtonActive: {
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    borderColor: '#00d4ff',
  },
  actionTypeButtonText: {
    color: '#888',
    fontSize: 14,
  },
  actionTypeButtonTextActive: {
    color: '#00d4ff',
  },
  saveButton: {
    backgroundColor: '#00d4ff',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
