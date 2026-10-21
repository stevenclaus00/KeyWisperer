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
import { apiService, VoiceCommand, Profile } from '../../src/services/api';

// ─── Helper ───

const getActionTypeBadgeStyle = (type: string) => {
  switch (type) {
    case 'key':
      return { backgroundColor: 'rgba(255, 159, 64, 0.15)', borderColor: '#ff9f40' };
    case 'macro':
      return { backgroundColor: 'rgba(153, 102, 255, 0.15)', borderColor: '#9966ff' };
    default:
      return { backgroundColor: 'rgba(0, 212, 255, 0.15)', borderColor: '#00d4ff' };
  }
};

// ─── Profile Edit Modal ───

interface ProfileEditModalProps {
  visible: boolean;
  profile: Profile | null;
  onClose: () => void;
  onSave: (profile: Profile) => void;
}

function ProfileEditModal({ visible, profile, onClose, onSave }: ProfileEditModalProps) {
  const [name, setName] = useState('');
  const [vocabText, setVocabText] = useState('');
  const [immediateInsertion, setImmediateInsertion] = useState(true);
  const [chunkDuration, setChunkDuration] = useState(3000);
  const [autoPunctuation, setAutoPunctuation] = useState(true);
  const [pcEnabled, setPcEnabled] = useState(true);
  const [autoCapitalize, setAutoCapitalize] = useState(true);
  const [numberFormatting, setNumberFormatting] = useState(true);
  const [smartQuotes, setSmartQuotes] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (profile) {
      setName(profile.name);
      setVocabText(profile.custom_vocabulary.join(', '));
      setImmediateInsertion(profile.immediate_insertion);
      setChunkDuration(profile.chunk_duration_ms);
      setAutoPunctuation(profile.auto_punctuation);
      setPcEnabled(profile.pc_connection_enabled);
      setAutoCapitalize(profile.auto_capitalize);
      setNumberFormatting(profile.number_formatting);
      setSmartQuotes(profile.smart_quotes);
    } else {
      setName('');
      setVocabText('');
      setImmediateInsertion(true);
      setChunkDuration(3000);
      setAutoPunctuation(true);
      setPcEnabled(true);
      setAutoCapitalize(true);
      setNumberFormatting(true);
      setSmartQuotes(false);
    }
  }, [profile, visible]);

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert('Error', 'Profile name is required');
      return;
    }

    setIsSaving(true);
    const vocab = vocabText
      .split(',')
      .map((w) => w.trim())
      .filter(Boolean);

    const data = {
      name: name.trim(),
      custom_vocabulary: vocab,
      immediate_insertion: immediateInsertion,
      chunk_duration_ms: chunkDuration,
      auto_punctuation: autoPunctuation,
      pc_connection_enabled: pcEnabled,
      auto_capitalize: autoCapitalize,
      number_formatting: numberFormatting,
      smart_quotes: smartQuotes,
      paragraph_breaks: true,
    };

    try {
      let result: Profile | null = null;
      if (profile) {
        result = await apiService.updateProfile(profile.id, data);
      } else {
        result = await apiService.createProfile(data);
      }
      if (result) {
        onSave(result);
      } else {
        Alert.alert('Error', 'Failed to save profile');
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={pStyles.overlay}>
        <View style={pStyles.sheet}>
          <View style={pStyles.header}>
            <Text style={pStyles.title}>{profile ? 'Edit Profile' : 'New Profile'}</Text>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={24} color="#888" />
            </TouchableOpacity>
          </View>

          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Name */}
            <Text style={pStyles.label}>Profile Name</Text>
            <TextInput
              style={pStyles.input}
              placeholder="e.g. Work, Personal, Medical"
              placeholderTextColor="#444"
              value={name}
              onChangeText={setName}
            />

            {/* Custom Vocabulary */}
            <Text style={pStyles.label}>Custom Vocabulary</Text>
            <Text style={pStyles.hint}>Comma-separated words/phrases Whisper will recognize better</Text>
            <TextInput
              style={[pStyles.input, { height: 80, textAlignVertical: 'top', paddingTop: 12 }]}
              placeholder="e.g. React Native, TypeScript, FastAPI"
              placeholderTextColor="#444"
              value={vocabText}
              onChangeText={setVocabText}
              multiline
            />

            {/* Chunk Duration */}
            <Text style={pStyles.label}>Chunk Duration</Text>
            <View style={pStyles.chipRow}>
              {[2000, 3000, 5000].map((d) => (
                <TouchableOpacity
                  key={d}
                  style={[pStyles.chip, chunkDuration === d && pStyles.chipActive]}
                  onPress={() => setChunkDuration(d)}
                >
                  <Text style={[pStyles.chipText, chunkDuration === d && pStyles.chipTextActive]}>
                    {d / 1000}s
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Toggles */}
            <Text style={pStyles.sectionLabel}>Behaviour</Text>
            {[
              { label: 'Immediate Insertion', sub: 'Type text as you speak in chunks', value: immediateInsertion, set: setImmediateInsertion },
              { label: 'Auto Punctuation', sub: 'Whisper adds commas & periods', value: autoPunctuation, set: setAutoPunctuation },
              { label: 'PC Connection', sub: 'Send text to connected PC', value: pcEnabled, set: setPcEnabled },
            ].map(({ label, sub, value, set }) => (
              <View key={label} style={pStyles.toggleRow}>
                <View style={{ flex: 1 }}>
                  <Text style={pStyles.toggleLabel}>{label}</Text>
                  <Text style={pStyles.toggleSub}>{sub}</Text>
                </View>
                <Switch value={value} onValueChange={set} trackColor={{ false: '#222', true: '#00d4ff' }} thumbColor="#fff" />
              </View>
            ))}

            <Text style={pStyles.sectionLabel}>Smart Formatting</Text>
            {[
              { label: 'Auto Capitalize', sub: 'Capitalize sentence beginnings', value: autoCapitalize, set: setAutoCapitalize },
              { label: 'Number Formatting', sub: 'Convert "twenty five" → 25', value: numberFormatting, set: setNumberFormatting },
              { label: 'Smart Quotes', sub: 'Convert " " to typographic quotes', value: smartQuotes, set: setSmartQuotes },
            ].map(({ label, sub, value, set }) => (
              <View key={label} style={pStyles.toggleRow}>
                <View style={{ flex: 1 }}>
                  <Text style={pStyles.toggleLabel}>{label}</Text>
                  <Text style={pStyles.toggleSub}>{sub}</Text>
                </View>
                <Switch value={value} onValueChange={set} trackColor={{ false: '#222', true: '#00d4ff' }} thumbColor="#fff" />
              </View>
            ))}
          </ScrollView>

          <TouchableOpacity
            style={[pStyles.saveBtn, isSaving && { opacity: 0.6 }]}
            onPress={handleSave}
            disabled={isSaving}
          >
            {isSaving ? <ActivityIndicator color="#fff" /> : <Text style={pStyles.saveBtnText}>Save Profile</Text>}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const pStyles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.75)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: '#111',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 36,
    maxHeight: '92%',
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  title: { fontSize: 20, fontWeight: '700', color: '#fff' },
  label: { fontSize: 13, color: '#888', marginBottom: 6, marginTop: 16 },
  hint: { fontSize: 11, color: '#555', marginBottom: 8, marginTop: -4 },
  sectionLabel: { fontSize: 13, color: '#00d4ff', fontWeight: '600', marginTop: 20, marginBottom: 4 },
  input: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#2a2a2a',
    paddingHorizontal: 14,
    height: 48,
    color: '#fff',
    fontSize: 15,
  },
  chipRow: { flexDirection: 'row', gap: 8 },
  chip: {
    paddingHorizontal: 18, paddingVertical: 8, borderRadius: 10,
    backgroundColor: '#1a1a1a', borderWidth: 1, borderColor: '#2a2a2a',
  },
  chipActive: { backgroundColor: 'rgba(0,212,255,0.1)', borderColor: '#00d4ff' },
  chipText: { color: '#666', fontSize: 14 },
  chipTextActive: { color: '#00d4ff' },
  toggleRow: {
    flexDirection: 'row', alignItems: 'center',
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#1a1a1a',
  },
  toggleLabel: { fontSize: 14, color: '#ddd', fontWeight: '500' },
  toggleSub: { fontSize: 11, color: '#555', marginTop: 2 },
  saveBtn: { backgroundColor: '#00d4ff', borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginTop: 24 },
  saveBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
});

// ─── Main Settings Screen ───

export default function SettingsScreen() {
  const {
    settings,
    setSettings,
    voiceCommands,
    setVoiceCommands,
    persistState,
    loadPersistedState,
    profiles,
    setProfiles,
    activeProfile,
    setActiveProfile,
  } = useAppStore();

  const [isLoading, setIsLoading] = useState(true);
  const [showAddCommand, setShowAddCommand] = useState(false);
  const [newTrigger, setNewTrigger] = useState('');
  const [newAction, setNewAction] = useState('');
  const [newActionType, setNewActionType] = useState<'text' | 'key' | 'macro'>('text');

  // Profiles
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      await loadPersistedState();

      const [serverSettings, commands, profilesData, activeProfileData] = await Promise.all([
        apiService.getSettings(),
        (await apiService.initDefaultCommands(), apiService.getVoiceCommands()),
        apiService.getProfiles(),
        apiService.getActiveProfile(),
      ]);

      if (serverSettings) setSettings(serverSettings);
      setVoiceCommands(commands);
      if (profilesData.length > 0) setProfiles(profilesData);
      if (activeProfileData) setActiveProfile(activeProfileData);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Voice Commands ──

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
    Alert.alert('Delete Command', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          const ok = await apiService.deleteVoiceCommand(commandId);
          if (ok) setVoiceCommands(voiceCommands.filter((c) => c.id !== commandId));
        },
      },
    ]);
  };

  // ── Profiles ──

  const handleProfileSave = (savedProfile: Profile) => {
    const updated = profiles.some((p) => p.id === savedProfile.id)
      ? profiles.map((p) => (p.id === savedProfile.id ? savedProfile : p))
      : [...profiles, savedProfile];
    setProfiles(updated);
    if (activeProfile?.id === savedProfile.id) setActiveProfile(savedProfile);
    setShowProfileModal(false);
    setEditingProfile(null);
  };

  const handleActivateProfile = async (profileId: string) => {
    const updated = await apiService.activateProfile(profileId);
    if (updated) {
      setProfiles(profiles.map((p) => ({ ...p, is_active: p.id === profileId })));
      setActiveProfile(updated);
    }
  };

  const handleDeleteProfile = async (profile: Profile) => {
    if (profiles.length <= 1) {
      Alert.alert('Cannot Delete', 'You need at least one profile.');
      return;
    }
    Alert.alert('Delete Profile', `Delete "${profile.name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          const ok = await apiService.deleteProfile(profile.id);
          if (ok) {
            const remaining = profiles.filter((p) => p.id !== profile.id);
            setProfiles(remaining);
            if (activeProfile?.id === profile.id) {
              const newActive = remaining.find((p) => p.is_active) ?? remaining[0];
              setActiveProfile(newActive ?? null);
            }
          }
        },
      },
    ]);
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#00d4ff" />
          <Text style={styles.loadingText}>Loading…</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Settings</Text>
          <Text style={styles.subtitle}>Profiles, formatting & commands</Text>
        </View>

        {/* ── Profiles Section ── */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Profiles</Text>
            <TouchableOpacity
              style={styles.addButton}
              onPress={() => { setEditingProfile(null); setShowProfileModal(true); }}
            >
              <Ionicons name="add" size={18} color="#fff" />
            </TouchableOpacity>
          </View>
          <Text style={styles.sectionDescription}>
            Switch contexts with different vocab and formatting
          </Text>

          {profiles.map((profile) => (
            <View key={profile.id} style={[styles.profileCard, profile.is_active && styles.profileCardActive]}>
              <TouchableOpacity
                style={styles.profileCardMain}
                onPress={() => handleActivateProfile(profile.id)}
              >
                <View style={[styles.profileActiveDot, profile.is_active && styles.profileActiveDotOn]} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.profileName, profile.is_active && styles.profileNameActive]}>
                    {profile.name}
                    {profile.is_active && <Text style={styles.activeLabel}> · Active</Text>}
                  </Text>
                  <Text style={styles.profileMeta}>
                    {profile.immediate_insertion ? 'Immediate' : 'Batch'} ·{' '}
                    {profile.chunk_duration_ms / 1000}s chunks
                    {profile.custom_vocabulary.length > 0
                      ? ` · ${profile.custom_vocabulary.length} words`
                      : ''}
                  </Text>
                  {profile.custom_vocabulary.length > 0 && (
                    <Text style={styles.profileVocabPreview} numberOfLines={1}>
                      {profile.custom_vocabulary.slice(0, 4).join(', ')}
                      {profile.custom_vocabulary.length > 4 ? '…' : ''}
                    </Text>
                  )}
                </View>
              </TouchableOpacity>

              <View style={styles.profileActions}>
                <TouchableOpacity
                  style={styles.profileActionBtn}
                  onPress={() => { setEditingProfile(profile); setShowProfileModal(true); }}
                >
                  <Ionicons name="pencil-outline" size={16} color="#666" />
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.profileActionBtn}
                  onPress={() => handleDeleteProfile(profile)}
                >
                  <Ionicons name="trash-outline" size={16} color="#ff4444" />
                </TouchableOpacity>
              </View>
            </View>
          ))}
        </View>

        {/* ── Active Profile Formatting ── */}
        {activeProfile && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Smart Formatting</Text>
            <Text style={styles.sectionDescription}>
              Applied after Whisper transcribes (profile: {activeProfile.name})
            </Text>

            <View style={styles.settingRow}>
              <View style={styles.settingInfo}>
                <Text style={styles.settingLabel}>Auto Capitalize</Text>
                <Text style={styles.settingDescription}>Capitalize sentence beginnings</Text>
              </View>
              <Switch
                value={activeProfile.auto_capitalize}
                onValueChange={async (v) => {
                  const updated = await apiService.updateProfile(activeProfile.id, { auto_capitalize: v });
                  if (updated) {
                    const { updateProfileLocally } = useAppStore.getState();
                    updateProfileLocally(updated);
                  }
                }}
                trackColor={{ false: '#333', true: '#00d4ff' }}
                thumbColor="#fff"
              />
            </View>

            <View style={styles.settingRow}>
              <View style={styles.settingInfo}>
                <Text style={styles.settingLabel}>Number Formatting</Text>
                <Text style={styles.settingDescription}>Convert "twenty five" → 25</Text>
              </View>
              <Switch
                value={activeProfile.number_formatting}
                onValueChange={async (v) => {
                  const updated = await apiService.updateProfile(activeProfile.id, { number_formatting: v });
                  if (updated) {
                    const { updateProfileLocally } = useAppStore.getState();
                    updateProfileLocally(updated);
                  }
                }}
                trackColor={{ false: '#333', true: '#00d4ff' }}
                thumbColor="#fff"
              />
            </View>

            <View style={styles.settingRow}>
              <View style={styles.settingInfo}>
                <Text style={styles.settingLabel}>Smart Quotes</Text>
                <Text style={styles.settingDescription}>Typographic " " instead of straight "</Text>
              </View>
              <Switch
                value={activeProfile.smart_quotes}
                onValueChange={async (v) => {
                  const updated = await apiService.updateProfile(activeProfile.id, { smart_quotes: v });
                  if (updated) {
                    const { updateProfileLocally } = useAppStore.getState();
                    updateProfileLocally(updated);
                  }
                }}
                trackColor={{ false: '#333', true: '#00d4ff' }}
                thumbColor="#fff"
              />
            </View>
          </View>
        )}

        {/* ── Voice Commands ── */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Voice Commands</Text>
            <TouchableOpacity style={styles.addButton} onPress={() => setShowAddCommand(true)}>
              <Ionicons name="add" size={18} color="#fff" />
            </TouchableOpacity>
          </View>
          <Text style={styles.sectionDescription}>Map spoken phrases to text/key actions</Text>

          {voiceCommands.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="mic-off" size={36} color="#2a2a2a" />
              <Text style={styles.emptyText}>No voice commands</Text>
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
                <TouchableOpacity style={styles.deleteButton} onPress={() => deleteCommand(command.id)}>
                  <Ionicons name="trash-outline" size={16} color="#ff4444" />
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>

        {/* ── About ── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          <View style={styles.aboutCard}>
            <Text style={styles.aboutTitle}>VoiceKey AI</Text>
            <Text style={styles.aboutVersion}>Version 2.0 — Phase 1 Power-Up</Text>
            <Text style={styles.aboutDescription}>
              AI-powered voice transcription with profiles, smart formatting, and transcription history.
              Powered by OpenAI Whisper.
            </Text>
          </View>
        </View>
      </ScrollView>

      {/* ── Add Voice Command Modal ── */}
      <Modal visible={showAddCommand} transparent animationType="slide" onRequestClose={() => setShowAddCommand(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Voice Command</Text>
              <TouchableOpacity onPress={() => setShowAddCommand(false)}>
                <Ionicons name="close" size={24} color="#888" />
              </TouchableOpacity>
            </View>

            <Text style={styles.inputLabel}>Trigger Phrase</Text>
            <TextInput
              style={styles.modalInput}
              placeholder='e.g. "new paragraph"'
              placeholderTextColor="#444"
              value={newTrigger}
              onChangeText={setNewTrigger}
              autoCapitalize="none"
            />

            <Text style={styles.inputLabel}>Action</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="e.g. ENTER or custom text"
              placeholderTextColor="#444"
              value={newAction}
              onChangeText={setNewAction}
            />

            <Text style={styles.inputLabel}>Action Type</Text>
            <View style={styles.actionTypeSelector}>
              {(['text', 'key', 'macro'] as const).map((type) => (
                <TouchableOpacity
                  key={type}
                  style={[styles.actionTypeButton, newActionType === type && styles.actionTypeButtonActive]}
                  onPress={() => setNewActionType(type)}
                >
                  <Text style={[styles.actionTypeButtonText, newActionType === type && styles.actionTypeButtonTextActive]}>
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

      {/* ── Profile Edit Modal ── */}
      <ProfileEditModal
        visible={showProfileModal}
        profile={editingProfile}
        onClose={() => { setShowProfileModal(false); setEditingProfile(null); }}
        onSave={handleProfileSave}
      />
    </SafeAreaView>
  );
}

// ─── Styles ───

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },
  scrollView: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: '#555', marginTop: 12, fontSize: 14 },
  header: { padding: 20, borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },
  title: { fontSize: 26, fontWeight: '700', color: '#fff', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#555' },
  section: { padding: 20, borderBottomWidth: 1, borderBottomColor: '#161616' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  sectionTitle: { fontSize: 15, fontWeight: '600', color: '#ccc' },
  sectionDescription: { fontSize: 12, color: '#555', marginBottom: 14 },
  addButton: {
    width: 30, height: 30, borderRadius: 15,
    backgroundColor: '#00d4ff', justifyContent: 'center', alignItems: 'center',
  },
  // Profile cards
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#1e1e1e',
    overflow: 'hidden',
  },
  profileCardActive: {
    borderColor: 'rgba(0,212,255,0.3)',
    backgroundColor: 'rgba(0,212,255,0.04)',
  },
  profileCardMain: { flex: 1, flexDirection: 'row', alignItems: 'center', padding: 14, gap: 10 },
  profileActiveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#333' },
  profileActiveDotOn: { backgroundColor: '#00d4ff' },
  profileName: { fontSize: 15, color: '#aaa', fontWeight: '600' },
  profileNameActive: { color: '#fff' },
  activeLabel: { color: '#00d4ff', fontWeight: '400', fontSize: 13 },
  profileMeta: { fontSize: 11, color: '#555', marginTop: 2 },
  profileVocabPreview: { fontSize: 11, color: '#444', marginTop: 3, fontStyle: 'italic' },
  profileActions: { flexDirection: 'column', paddingRight: 10, gap: 8 },
  profileActionBtn: { padding: 6 },
  // Settings rows
  settingRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#161616',
  },
  settingInfo: { flex: 1, marginRight: 16 },
  settingLabel: { fontSize: 14, color: '#ddd', fontWeight: '500' },
  settingDescription: { fontSize: 11, color: '#555', marginTop: 2 },
  // Voice commands
  emptyState: { alignItems: 'center', paddingVertical: 28 },
  emptyText: { color: '#444', marginTop: 10, fontSize: 14 },
  commandCard: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#111', borderRadius: 12, padding: 12,
    marginBottom: 8, borderWidth: 1, borderColor: '#1e1e1e',
  },
  commandInfo: { flex: 1 },
  commandTrigger: { fontSize: 14, color: '#ddd', fontWeight: '500', marginBottom: 4 },
  commandAction: { flexDirection: 'row', alignItems: 'center' },
  actionTypeBadge: {
    paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6,
    borderWidth: 1, marginRight: 8,
  },
  actionTypeText: { fontSize: 9, color: '#888', textTransform: 'uppercase', fontWeight: '600' },
  commandActionText: { fontSize: 12, color: '#666' },
  deleteButton: { padding: 8 },
  // About
  aboutCard: {
    backgroundColor: '#111', borderRadius: 14, padding: 16,
    borderWidth: 1, borderColor: '#1e1e1e',
  },
  aboutTitle: { fontSize: 17, fontWeight: '700', color: '#fff' },
  aboutVersion: { fontSize: 12, color: '#555', marginTop: 4 },
  aboutDescription: { fontSize: 13, color: '#666', marginTop: 10, lineHeight: 20 },
  // Modals
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.75)', justifyContent: 'flex-end' },
  modalContent: {
    backgroundColor: '#111', borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: 24, paddingBottom: 40,
  },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#fff' },
  inputLabel: { fontSize: 13, color: '#888', marginBottom: 8 },
  modalInput: {
    backgroundColor: '#1a1a1a', borderRadius: 12, borderWidth: 1, borderColor: '#2a2a2a',
    paddingHorizontal: 14, height: 48, color: '#fff', fontSize: 15, marginBottom: 16,
  },
  actionTypeSelector: { flexDirection: 'row', gap: 8, marginBottom: 24 },
  actionTypeButton: {
    flex: 1, paddingVertical: 12, borderRadius: 10,
    backgroundColor: '#1a1a1a', borderWidth: 1, borderColor: '#2a2a2a', alignItems: 'center',
  },
  actionTypeButtonActive: { backgroundColor: 'rgba(0,212,255,0.1)', borderColor: '#00d4ff' },
  actionTypeButtonText: { color: '#666', fontSize: 14 },
  actionTypeButtonTextActive: { color: '#00d4ff', fontWeight: '600' },
  saveButton: { backgroundColor: '#00d4ff', borderRadius: 14, paddingVertical: 16, alignItems: 'center' },
  saveButtonText: { color: '#fff', fontSize: 16, fontWeight: '700' },
});
