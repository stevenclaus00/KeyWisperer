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
  Modal,
  Animated,
  TextInput,
  Share,
  FlatList,
  KeyboardAvoidingView,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { useAppStore } from '../../src/store/appStore';
import { apiService, Profile, TranscriptionHistoryItem } from '../../src/services/api';
import { applySmartFormatting, formatTimestamp, textPreview } from '../../src/utils/smartFormatting';

const NUM_BARS = 28;
const BAR_WIDTH = 3;
const BAR_GAP = 2;

// ─── Waveform Component ───

function WaveformBars({ isRecording, isProcessing }: { isRecording: boolean; isProcessing: boolean }) {
  const bars = useRef(
    Array.from({ length: NUM_BARS }, () => new Animated.Value(3))
  ).current;
  const animRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isRecording || isProcessing) {
      const animate = () => {
        bars.forEach((bar) => {
          const target = isProcessing
            ? 8 + Math.random() * 16
            : 4 + Math.random() * 40;
          Animated.timing(bar, {
            toValue: target,
            duration: 120 + Math.random() * 180,
            useNativeDriver: false,
          }).start();
        });
      };
      animate();
      animRef.current = setInterval(animate, 160);
    } else {
      if (animRef.current) clearInterval(animRef.current);
      bars.forEach((bar) => {
        Animated.timing(bar, {
          toValue: 3,
          duration: 400,
          useNativeDriver: false,
        }).start();
      });
    }
    return () => {
      if (animRef.current) clearInterval(animRef.current);
    };
  }, [isRecording, isProcessing]);

  const color = isProcessing ? '#ffaa00' : '#00d4ff';

  return (
    <View style={waveStyles.container}>
      {bars.map((bar, index) => (
        <Animated.View
          key={index}
          style={[
            waveStyles.bar,
            {
              height: bar,
              backgroundColor: color,
              opacity: isRecording || isProcessing ? 1 : 0.25,
            },
          ]}
        />
      ))}
    </View>
  );
}

const waveStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 56,
    paddingHorizontal: 8,
    justifyContent: 'center',
  },
  bar: {
    width: BAR_WIDTH,
    borderRadius: BAR_WIDTH / 2,
    marginHorizontal: BAR_GAP / 2,
  },
});

// ─── Profile Switcher Chip ───

function ProfileChip({
  activeProfile,
  onPress,
}: {
  activeProfile: Profile | null;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={chipStyles.chip} onPress={onPress} activeOpacity={0.75}>
      <View style={chipStyles.dot} />
      <Text style={chipStyles.text} numberOfLines={1}>
        {activeProfile?.name ?? 'Default'}
      </Text>
      <Ionicons name="chevron-down" size={12} color="#00d4ff" />
    </TouchableOpacity>
  );
}

const chipStyles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,212,255,0.12)',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: 'rgba(0,212,255,0.3)',
    maxWidth: 140,
    gap: 5,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: '#00d4ff',
  },
  text: {
    color: '#00d4ff',
    fontSize: 13,
    fontWeight: '600',
    flexShrink: 1,
  },
});

// ─── History Item Card ───

function HistoryCard({
  item,
  onSelect,
  onDelete,
}: {
  item: TranscriptionHistoryItem;
  onSelect: (item: TranscriptionHistoryItem) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <TouchableOpacity style={hStyles.card} onPress={() => onSelect(item)} activeOpacity={0.8}>
      <View style={hStyles.cardHeader}>
        <Text style={hStyles.timestamp}>{formatTimestamp(item.timestamp)}</Text>
        <View style={hStyles.metaRow}>
          {item.profile_name !== 'Default' && (
            <Text style={hStyles.profileBadge}>{item.profile_name}</Text>
          )}
          <Text style={hStyles.wordCount}>{item.word_count} words</Text>
        </View>
      </View>
      <Text style={hStyles.preview} numberOfLines={2}>
        {textPreview(item.text, 120)}
      </Text>
      <TouchableOpacity
        style={hStyles.deleteBtn}
        onPress={() => onDelete(item.id)}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <Ionicons name="trash-outline" size={16} color="#ff4444" />
      </TouchableOpacity>
    </TouchableOpacity>
  );
}

const hStyles = StyleSheet.create({
  card: {
    backgroundColor: '#141414',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#242424',
    position: 'relative',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  timestamp: {
    color: '#666',
    fontSize: 12,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  profileBadge: {
    backgroundColor: 'rgba(0,212,255,0.15)',
    color: '#00d4ff',
    fontSize: 10,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    overflow: 'hidden',
  },
  wordCount: {
    color: '#555',
    fontSize: 12,
  },
  preview: {
    color: '#aaa',
    fontSize: 14,
    lineHeight: 20,
    paddingRight: 28,
  },
  deleteBtn: {
    position: 'absolute',
    bottom: 12,
    right: 12,
  },
});

// ─── Main Voice Screen ───

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
    // Profiles
    profiles,
    setProfiles,
    activeProfile,
    setActiveProfile,
    // History
    history,
    setHistory,
    prependHistory,
    removeHistoryItem,
    historyLoaded,
    setHistoryLoaded,
    // Session
    sessionStartTime,
    setSessionStartTime,
  } = useAppStore();

  const insets = useSafeAreaInsets();

  // Local state
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Tap microphone to start');

  // Profile switcher
  const [showProfileModal, setShowProfileModal] = useState(false);

  // History drawer
  const [showHistory, setShowHistory] = useState(false);
  const historySlide = useRef(new Animated.Value(0)).current;
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<TranscriptionHistoryItem | null>(null);
  const [editingText, setEditingText] = useState('');
  const [isEditMode, setIsEditMode] = useState(false);
  const [historySearch, setHistorySearch] = useState('');

  // Export modal
  const [showExport, setShowExport] = useState(false);

  const recordingRef = useRef<Audio.Recording | null>(null);
  const chunkIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const sessionTextRef = useRef('');  // accumulates text in current session

  useEffect(() => {
    requestPermissions();
    loadInitialData();
    return () => {
      if (chunkIntervalRef.current) clearInterval(chunkIntervalRef.current);
    };
  }, []);

  const loadInitialData = async () => {
    try {
      const [profilesData, activeProfileData] = await Promise.all([
        apiService.getProfiles(),
        apiService.getActiveProfile(),
      ]);
      if (profilesData.length > 0) setProfiles(profilesData);
      if (activeProfileData) setActiveProfile(activeProfileData);
    } catch (err) {
      console.error('Error loading initial data:', err);
    }
  };

  const loadHistory = async () => {
    if (historyLoaded) return;
    try {
      const items = await apiService.getHistory(50);
      setHistory(items);
      setHistoryLoaded(true);
    } catch (err) {
      console.error('Error loading history:', err);
    }
  };

  const requestPermissions = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      setPermissionGranted(status === 'granted');
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Microphone access is needed for transcription.');
      }
    } catch (error) {
      console.error('Permission error:', error);
    }
  };

  // ── Smart Formatting ──

  const formatText = useCallback(
    (raw: string): string => {
      if (!activeProfile) return raw;
      return applySmartFormatting(raw, {
        autoCapitalize: activeProfile.auto_capitalize,
        paragraphBreaks: activeProfile.paragraph_breaks,
        numberFormatting: activeProfile.number_formatting,
        smartQuotes: activeProfile.smart_quotes,
      });
    },
    [activeProfile]
  );

  // ── Voice Command Processing ──

  const processVoiceCommands = (text: string): string => {
    let processed = text;
    voiceCommands.forEach((cmd) => {
      if (cmd.enabled && cmd.action_type === 'text') {
        const regex = new RegExp(`\\b${cmd.trigger}\\b`, 'gi');
        processed = processed.replace(regex, cmd.action);
      }
    });
    return processed;
  };

  // ── PC Send ──

  const sendToPC = async (text: string) => {
    const profile = activeProfile;
    const pcEnabled = profile ? profile.pc_connection_enabled : settings.pc_connection_enabled;
    if (pcConnection.isConnected && pcEnabled) {
      try {
        await apiService.broadcastToPCs('text', { text });
      } catch (err) {
        console.error('Error sending to PC:', err);
      }
    }
  };

  // ── Recording ──

  const getEffectiveSettings = () => {
    if (activeProfile) {
      return {
        immediate_insertion: activeProfile.immediate_insertion,
        chunk_duration_ms: activeProfile.chunk_duration_ms,
      };
    }
    return settings;
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
      setSessionStartTime(Date.now());
      sessionTextRef.current = '';
      setStatusMessage('Listening…');

      const effective = getEffectiveSettings();
      if (effective.immediate_insertion) {
        chunkIntervalRef.current = setInterval(async () => {
          await processChunk();
        }, effective.chunk_duration_ms);
      }
    } catch (error) {
      console.error('Failed to start recording:', error);
      Alert.alert('Error', 'Failed to start recording');
    }
  };

  const processChunk = async () => {
    if (!recordingRef.current) return;
    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(newRecording);
      recordingRef.current = newRecording;

      if (uri) {
        setIsProcessing(true);
        const response = await apiService.transcribeAudio(uri, 'm4a', activeProfile?.id);
        if (response.success && response.text.trim()) {
          const withCommands = processVoiceCommands(response.text);
          const formatted = formatText(withCommands);
          sessionTextRef.current += (sessionTextRef.current ? ' ' : '') + formatted;
          appendTranscribedText(formatted);
          await sendToPC(formatted);
        }
        setIsProcessing(false);
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
      setStatusMessage('Processing…');
      setIsProcessing(true);

      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      setRecording(null);
      recordingRef.current = null;
      setIsRecording(false);

      if (uri) {
        const response = await apiService.transcribeAudio(uri, 'm4a', activeProfile?.id);
        if (response.success && response.text.trim()) {
          const withCommands = processVoiceCommands(response.text);
          const formatted = formatText(withCommands);
          sessionTextRef.current += (sessionTextRef.current ? ' ' : '') + formatted;
          appendTranscribedText(formatted);
          await sendToPC(formatted);
        }
        await FileSystem.deleteAsync(uri, { idempotent: true });
      }

      // Auto-save session to history
      const sessionText = sessionTextRef.current.trim();
      if (sessionText) {
        const durationSec = sessionStartTime
          ? (Date.now() - sessionStartTime) / 1000
          : undefined;
        const historyItem = await apiService.saveToHistory(
          sessionText,
          activeProfile?.id ?? '',
          activeProfile?.name ?? 'Default',
          durationSec
        );
        if (historyItem) {
          prependHistory(historyItem);
          setHistoryLoaded(false); // allow refresh next open
        }
      }

      setStatusMessage('Tap microphone to start');
    } catch (error) {
      console.error('Failed to stop recording:', error);
      setStatusMessage('Tap microphone to start');
    } finally {
      setIsProcessing(false);
      setSessionStartTime(null);
    }
  };

  const toggleRecording = () => {
    if (isRecording) stopRecording();
    else startRecording();
  };

  // ── History Drawer ──

  const openHistory = async () => {
    await loadHistory();
    setShowHistory(true);
    Animated.spring(historySlide, {
      toValue: 1,
      useNativeDriver: true,
      tension: 65,
      friction: 10,
    }).start();
  };

  const closeHistory = () => {
    Animated.timing(historySlide, {
      toValue: 0,
      duration: 250,
      useNativeDriver: true,
    }).start(() => {
      setShowHistory(false);
      setSelectedHistoryItem(null);
      setIsEditMode(false);
      setHistorySearch('');
    });
  };

  const handleSelectHistoryItem = (item: TranscriptionHistoryItem) => {
    setSelectedHistoryItem(item);
    setEditingText(item.text);
    setIsEditMode(false);
  };

  const handleDeleteHistoryItem = async (id: string) => {
    Alert.alert('Delete', 'Remove this history entry?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          await apiService.deleteHistoryItem(id);
          removeHistoryItem(id);
          if (selectedHistoryItem?.id === id) setSelectedHistoryItem(null);
        },
      },
    ]);
  };

  const handleSaveEdit = async () => {
    if (!selectedHistoryItem) return;
    const updated = await apiService.updateHistoryItem(selectedHistoryItem.id, editingText);
    if (updated) {
      const { updateHistoryItemLocally } = useAppStore.getState();
      updateHistoryItemLocally(updated);
      setSelectedHistoryItem(updated);
      setIsEditMode(false);
      Alert.alert('Saved', 'Transcription updated.');
    }
  };

  const handleRestoreFromHistory = (item: TranscriptionHistoryItem) => {
    appendTranscribedText(item.text);
    closeHistory();
  };

  const filteredHistory = history.filter((h) =>
    historySearch
      ? h.text.toLowerCase().includes(historySearch.toLowerCase()) ||
        h.profile_name.toLowerCase().includes(historySearch.toLowerCase())
      : true
  );

  // ── Export ──

  const handleExport = async (format: 'clipboard' | 'share' | 'txt' | 'md') => {
    if (!transcribedText.trim()) {
      Alert.alert('Nothing to export', 'Transcribe some audio first.');
      return;
    }

    setShowExport(false);

    if (format === 'clipboard') {
      Clipboard.setString(transcribedText);
      Alert.alert('Copied!', 'Text copied to clipboard.');
      return;
    }

    if (format === 'share') {
      try {
        await Share.share({ message: transcribedText });
      } catch (err) {
        console.error('Share error:', err);
      }
      return;
    }

    // File export (txt or md)
    const ext = format === 'md' ? 'md' : 'txt';
    const filename = `voicekey-${Date.now()}.${ext}`;
    const fileUri = `${FileSystem.cacheDirectory}${filename}`;
    const content =
      format === 'md'
        ? `# VoiceKey Transcription\n\n*${new Date().toLocaleString()}*\n\n---\n\n${transcribedText}`
        : transcribedText;

    try {
      await FileSystem.writeAsStringAsync(fileUri, content, {
        encoding: FileSystem.EncodingType.UTF8,
      });
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(fileUri, {
          mimeType: format === 'md' ? 'text/markdown' : 'text/plain',
          dialogTitle: `Save as .${ext}`,
        });
      } else {
        Alert.alert('Saved', `File saved to ${fileUri}`);
      }
    } catch (err) {
      console.error('Export error:', err);
      Alert.alert('Export failed', String(err));
    }
  };

  // ── Profile Switch ──

  const handleActivateProfile = async (profileId: string) => {
    const updated = await apiService.activateProfile(profileId);
    if (updated) {
      setProfiles(profiles.map((p) => ({ ...p, is_active: p.id === profileId })));
      setActiveProfile(updated);
    }
    setShowProfileModal(false);
  };

  // ── Render ──

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* ─── Header ─── */}
      <View style={styles.header}>
        <Text style={styles.title}>VoiceKey AI</Text>
        <View style={styles.headerRight}>
          <View style={styles.statusBadge}>
            <View style={[styles.statusDot, { backgroundColor: pcConnection.isConnected ? '#00ff88' : '#444' }]} />
            <Text style={styles.statusText}>{pcConnection.isConnected ? 'PC' : 'PC Off'}</Text>
          </View>
          <ProfileChip activeProfile={activeProfile} onPress={() => setShowProfileModal(true)} />
        </View>
      </View>

      {/* ─── Text Area ─── */}
      <ScrollView style={styles.textContainer} contentContainerStyle={styles.textContent}>
        {transcribedText ? (
          <Text style={styles.transcribedText}>{transcribedText}</Text>
        ) : (
          <Text style={styles.placeholderText}>
            Your transcribed text will appear here…{'\n'}Tap the mic to begin.
          </Text>
        )}
      </ScrollView>

      {/* ─── Controls ─── */}
      <View style={styles.controlsContainer}>
        {/* Waveform */}
        <WaveformBars isRecording={isRecording} isProcessing={isProcessing} />

        {/* Status */}
        <Text style={styles.statusMessage}>{statusMessage}</Text>

        {/* Main button row */}
        <View style={styles.buttonRow}>
          {/* History */}
          <TouchableOpacity
            style={styles.sideButton}
            onPress={openHistory}
            accessibilityLabel="History"
          >
            <Ionicons name="time-outline" size={22} color="#888" />
            <Text style={styles.sideButtonLabel}>History</Text>
          </TouchableOpacity>

          {/* Mic */}
          <TouchableOpacity
            style={[styles.micButton, isRecording && styles.micButtonActive]}
            onPress={toggleRecording}
            disabled={!permissionGranted}
            activeOpacity={0.85}
          >
            {isProcessing && !isRecording ? (
              <ActivityIndicator size="large" color="#fff" />
            ) : (
              <Ionicons name={isRecording ? 'stop' : 'mic'} size={36} color="#fff" />
            )}
          </TouchableOpacity>

          {/* Export */}
          <TouchableOpacity
            style={styles.sideButton}
            onPress={() => setShowExport(true)}
            disabled={!transcribedText}
            accessibilityLabel="Export"
          >
            <Ionicons name="share-outline" size={22} color={transcribedText ? '#888' : '#333'} />
            <Text style={[styles.sideButtonLabel, !transcribedText && { color: '#333' }]}>Export</Text>
          </TouchableOpacity>
        </View>

        {/* Secondary row */}
        <View style={styles.secondaryRow}>
          <TouchableOpacity
            style={styles.secondaryBtn}
            onPress={() => {
              clearTranscribedText();
              setStatusMessage('Tap microphone to start');
            }}
            disabled={!transcribedText || isRecording}
          >
            <Ionicons name="trash-outline" size={18} color={transcribedText && !isRecording ? '#888' : '#333'} />
            <Text style={[styles.secondaryLabel, (!transcribedText || isRecording) && { color: '#333' }]}>Clear</Text>
          </TouchableOpacity>

          {activeProfile?.immediate_insertion || settings.immediate_insertion ? (
            <View style={styles.modeIndicator}>
              <Ionicons name="flash" size={13} color="#00d4ff" />
              <Text style={styles.modeText}>Immediate</Text>
            </View>
          ) : null}

          <TouchableOpacity
            style={styles.secondaryBtn}
            onPress={() => {
              if (transcribedText) {
                Clipboard.setString(transcribedText);
                Alert.alert('Copied!', 'Text copied to clipboard.');
              }
            }}
            disabled={!transcribedText}
          >
            <Ionicons name="copy-outline" size={18} color={transcribedText ? '#888' : '#333'} />
            <Text style={[styles.secondaryLabel, !transcribedText && { color: '#333' }]}>Copy</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ─────────────────────────────────────────
          Profile Switcher Modal
      ───────────────────────────────────────── */}
      <Modal visible={showProfileModal} transparent animationType="fade" onRequestClose={() => setShowProfileModal(false)}>
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setShowProfileModal(false)}>
          <View style={styles.profileModal}>
            <Text style={styles.profileModalTitle}>Switch Profile</Text>
            {profiles.map((p) => (
              <TouchableOpacity
                key={p.id}
                style={[styles.profileOption, p.is_active && styles.profileOptionActive]}
                onPress={() => handleActivateProfile(p.id)}
              >
                <View style={[styles.profileOptionDot, p.is_active && styles.profileOptionDotActive]} />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.profileOptionName, p.is_active && styles.profileOptionNameActive]}>
                    {p.name}
                  </Text>
                  {p.custom_vocabulary.length > 0 && (
                    <Text style={styles.profileOptionVocab}>
                      {p.custom_vocabulary.length} custom words
                    </Text>
                  )}
                </View>
                {p.is_active && <Ionicons name="checkmark" size={18} color="#00d4ff" />}
              </TouchableOpacity>
            ))}
            <TouchableOpacity style={styles.profileModalClose} onPress={() => setShowProfileModal(false)}>
              <Text style={styles.profileModalCloseText}>Done</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* ─────────────────────────────────────────
          Export Modal
      ───────────────────────────────────────── */}
      <Modal visible={showExport} transparent animationType="slide" onRequestClose={() => setShowExport(false)}>
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setShowExport(false)}>
          <View style={styles.exportSheet}>
            <View style={styles.exportHandle} />
            <Text style={styles.exportTitle}>Export Transcription</Text>

            <TouchableOpacity style={styles.exportOption} onPress={() => handleExport('clipboard')}>
              <Ionicons name="clipboard-outline" size={22} color="#00d4ff" />
              <View style={{ flex: 1 }}>
                <Text style={styles.exportOptionTitle}>Copy to Clipboard</Text>
                <Text style={styles.exportOptionSub}>Paste anywhere instantly</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#444" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.exportOption} onPress={() => handleExport('share')}>
              <Ionicons name="share-social-outline" size={22} color="#00d4ff" />
              <View style={{ flex: 1 }}>
                <Text style={styles.exportOptionTitle}>Share</Text>
                <Text style={styles.exportOptionSub}>Send via any app</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#444" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.exportOption} onPress={() => handleExport('txt')}>
              <Ionicons name="document-text-outline" size={22} color="#00d4ff" />
              <View style={{ flex: 1 }}>
                <Text style={styles.exportOptionTitle}>Download as .txt</Text>
                <Text style={styles.exportOptionSub}>Plain text file</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#444" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.exportOption} onPress={() => handleExport('md')}>
              <Ionicons name="code-slash-outline" size={22} color="#00d4ff" />
              <View style={{ flex: 1 }}>
                <Text style={styles.exportOptionTitle}>Download as .md</Text>
                <Text style={styles.exportOptionSub}>Markdown with metadata</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#444" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.exportCancel} onPress={() => setShowExport(false)}>
              <Text style={styles.exportCancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* ─────────────────────────────────────────
          History Bottom Sheet
      ───────────────────────────────────────── */}
      <Modal visible={showHistory} transparent animationType="none" onRequestClose={closeHistory}>
        <View style={{ flex: 1 }}>
          <TouchableOpacity style={styles.historyOverlay} activeOpacity={1} onPress={closeHistory} />
          <Animated.View
            style={[
              styles.historySheet,
              {
                transform: [
                  {
                    translateY: historySlide.interpolate({
                      inputRange: [0, 1],
                      outputRange: [700, 0],
                    }),
                  },
                ],
              },
            ]}
          >
            {/* Handle */}
            <View style={styles.historyHandle} />

            {/* Header */}
            <View style={styles.historyHeader}>
              <Text style={styles.historyTitle}>Transcription History</Text>
              <TouchableOpacity onPress={closeHistory}>
                <Ionicons name="close" size={22} color="#888" />
              </TouchableOpacity>
            </View>

            {selectedHistoryItem ? (
              /* ── Detail view ── */
              <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
                <TouchableOpacity
                  style={styles.historyBackBtn}
                  onPress={() => { setSelectedHistoryItem(null); setIsEditMode(false); }}
                >
                  <Ionicons name="arrow-back" size={16} color="#888" />
                  <Text style={styles.historyBackText}>Back</Text>
                </TouchableOpacity>

                <View style={styles.detailMeta}>
                  <Text style={styles.detailTimestamp}>{formatTimestamp(selectedHistoryItem.timestamp)}</Text>
                  <Text style={styles.detailMeta2}>{selectedHistoryItem.word_count} words · {selectedHistoryItem.profile_name}</Text>
                </View>

                <ScrollView style={{ flex: 1, marginHorizontal: 16 }}>
                  {isEditMode ? (
                    <TextInput
                      style={styles.detailEditInput}
                      multiline
                      value={editingText}
                      onChangeText={setEditingText}
                      autoFocus
                      textAlignVertical="top"
                    />
                  ) : (
                    <Text style={styles.detailText}>{selectedHistoryItem.text}</Text>
                  )}
                </ScrollView>

                <View style={styles.detailActions}>
                  {isEditMode ? (
                    <>
                      <TouchableOpacity style={[styles.detailBtn, styles.detailBtnPrimary]} onPress={handleSaveEdit}>
                        <Ionicons name="checkmark" size={18} color="#fff" />
                        <Text style={styles.detailBtnPrimaryText}>Save</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.detailBtn} onPress={() => { setIsEditMode(false); setEditingText(selectedHistoryItem.text); }}>
                        <Text style={styles.detailBtnText}>Cancel</Text>
                      </TouchableOpacity>
                    </>
                  ) : (
                    <>
                      <TouchableOpacity style={styles.detailBtn} onPress={() => { Clipboard.setString(selectedHistoryItem.text); Alert.alert('Copied!', ''); }}>
                        <Ionicons name="copy-outline" size={18} color="#888" />
                        <Text style={styles.detailBtnText}>Copy</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.detailBtn} onPress={() => handleRestoreFromHistory(selectedHistoryItem)}>
                        <Ionicons name="arrow-redo-outline" size={18} color="#888" />
                        <Text style={styles.detailBtnText}>Restore</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.detailBtn} onPress={() => setIsEditMode(true)}>
                        <Ionicons name="pencil-outline" size={18} color="#888" />
                        <Text style={styles.detailBtnText}>Edit</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={[styles.detailBtn, styles.detailBtnDanger]} onPress={() => handleDeleteHistoryItem(selectedHistoryItem.id)}>
                        <Ionicons name="trash-outline" size={18} color="#ff4444" />
                        <Text style={styles.detailBtnDangerText}>Delete</Text>
                      </TouchableOpacity>
                    </>
                  )}
                </View>
              </KeyboardAvoidingView>
            ) : (
              /* ── List view ── */
              <>
                {/* Search */}
                <View style={styles.historySearch}>
                  <Ionicons name="search-outline" size={16} color="#555" style={{ marginRight: 8 }} />
                  <TextInput
                    style={styles.historySearchInput}
                    placeholder="Search transcriptions…"
                    placeholderTextColor="#444"
                    value={historySearch}
                    onChangeText={setHistorySearch}
                  />
                  {historySearch ? (
                    <TouchableOpacity onPress={() => setHistorySearch('')}>
                      <Ionicons name="close-circle" size={16} color="#555" />
                    </TouchableOpacity>
                  ) : null}
                </View>

                {filteredHistory.length === 0 ? (
                  <View style={styles.historyEmpty}>
                    <Ionicons name="mic-off-outline" size={44} color="#2a2a2a" />
                    <Text style={styles.historyEmptyText}>
                      {historySearch ? 'No results' : 'No transcriptions yet'}
                    </Text>
                  </View>
                ) : (
                  <FlatList
                    data={filteredHistory}
                    keyExtractor={(item) => item.id}
                    renderItem={({ item }) => (
                      <HistoryCard
                        item={item}
                        onSelect={handleSelectHistoryItem}
                        onDelete={handleDeleteHistoryItem}
                      />
                    )}
                    contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 40 }}
                    showsVerticalScrollIndicator={false}
                  />
                )}
              </>
            )}
          </Animated.View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// ─── Styles ───

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
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#1c1c1c',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: 0.3,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#161616',
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 14,
    gap: 5,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  statusText: {
    color: '#555',
    fontSize: 11,
    fontWeight: '500',
  },
  textContainer: {
    flex: 1,
    marginHorizontal: 16,
    marginVertical: 12,
    backgroundColor: '#0e0e0e',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#1e1e1e',
  },
  textContent: {
    padding: 18,
    minHeight: 180,
  },
  transcribedText: {
    fontSize: 17,
    color: '#e8e8e8',
    lineHeight: 26,
    letterSpacing: 0.2,
  },
  placeholderText: {
    fontSize: 15,
    color: '#3a3a3a',
    fontStyle: 'italic',
    lineHeight: 24,
    textAlign: 'center',
    paddingTop: 24,
  },
  controlsContainer: {
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 4,
    paddingBottom: 16,
    borderTopWidth: 1,
    borderTopColor: '#1c1c1c',
    backgroundColor: '#0a0a0a',
  },
  statusMessage: {
    color: '#444',
    fontSize: 13,
    marginBottom: 14,
    height: 18,
  },
  buttonRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 32,
    marginBottom: 16,
  },
  sideButton: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 60,
    gap: 4,
  },
  sideButtonLabel: {
    color: '#666',
    fontSize: 11,
    fontWeight: '500',
  },
  micButton: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: '#00d4ff',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#00d4ff',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 12,
    elevation: 10,
  },
  micButtonActive: {
    backgroundColor: '#ff3b3b',
    shadowColor: '#ff3b3b',
  },
  secondaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    paddingHorizontal: 8,
  },
  secondaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  secondaryLabel: {
    color: '#666',
    fontSize: 12,
  },
  modeIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,212,255,0.08)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    gap: 4,
    borderWidth: 1,
    borderColor: 'rgba(0,212,255,0.15)',
  },
  modeText: {
    color: '#00d4ff',
    fontSize: 11,
    fontWeight: '600',
  },

  // ── Modal Overlay ──
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.65)',
    justifyContent: 'flex-end',
  },

  // ── Profile Modal ──
  profileModal: {
    backgroundColor: '#121212',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 36,
  },
  profileModalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 20,
    textAlign: 'center',
  },
  profileOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 14,
    marginBottom: 8,
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#242424',
    gap: 12,
  },
  profileOptionActive: {
    backgroundColor: 'rgba(0,212,255,0.08)',
    borderColor: 'rgba(0,212,255,0.3)',
  },
  profileOptionDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#333',
  },
  profileOptionDotActive: {
    backgroundColor: '#00d4ff',
  },
  profileOptionName: {
    fontSize: 15,
    color: '#aaa',
    fontWeight: '500',
  },
  profileOptionNameActive: {
    color: '#fff',
  },
  profileOptionVocab: {
    fontSize: 11,
    color: '#555',
    marginTop: 2,
  },
  profileModalClose: {
    marginTop: 8,
    backgroundColor: '#1e1e1e',
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
  },
  profileModalCloseText: {
    color: '#888',
    fontSize: 15,
    fontWeight: '600',
  },

  // ── Export Sheet ──
  exportSheet: {
    backgroundColor: '#121212',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 36,
  },
  exportHandle: {
    width: 36,
    height: 4,
    backgroundColor: '#333',
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 20,
  },
  exportTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 20,
  },
  exportOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    gap: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#1e1e1e',
  },
  exportOptionTitle: {
    fontSize: 15,
    color: '#e0e0e0',
    fontWeight: '500',
  },
  exportOptionSub: {
    fontSize: 12,
    color: '#555',
    marginTop: 2,
  },
  exportCancel: {
    marginTop: 16,
    alignItems: 'center',
    paddingVertical: 14,
  },
  exportCancelText: {
    color: '#666',
    fontSize: 15,
    fontWeight: '600',
  },

  // ── History Sheet ──
  historyOverlay: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  historySheet: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '82%',
    backgroundColor: '#0e0e0e',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
  historyHandle: {
    width: 36,
    height: 4,
    backgroundColor: '#2a2a2a',
    borderRadius: 2,
    alignSelf: 'center',
    marginTop: 12,
    marginBottom: 4,
  },
  historyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  historyTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#fff',
  },
  historySearch: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#161616',
    borderRadius: 12,
    marginHorizontal: 16,
    marginVertical: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: '#222',
  },
  historySearchInput: {
    flex: 1,
    color: '#ccc',
    fontSize: 14,
    padding: 0,
  },
  historyEmpty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    paddingBottom: 80,
  },
  historyEmptyText: {
    color: '#333',
    fontSize: 15,
  },
  historyBackBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 4,
  },
  historyBackText: {
    color: '#888',
    fontSize: 14,
  },
  detailMeta: {
    paddingHorizontal: 16,
    paddingBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  detailTimestamp: {
    color: '#555',
    fontSize: 13,
  },
  detailMeta2: {
    color: '#444',
    fontSize: 12,
  },
  detailText: {
    color: '#d0d0d0',
    fontSize: 16,
    lineHeight: 26,
    paddingBottom: 32,
  },
  detailEditInput: {
    color: '#d0d0d0',
    fontSize: 16,
    lineHeight: 26,
    backgroundColor: '#141414',
    borderRadius: 12,
    padding: 14,
    minHeight: 180,
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  detailActions: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: '#1a1a1a',
  },
  detailBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: '#161616',
    borderWidth: 1,
    borderColor: '#222',
    gap: 5,
  },
  detailBtnPrimary: {
    backgroundColor: '#00d4ff',
    borderColor: '#00d4ff',
  },
  detailBtnDanger: {
    borderColor: 'rgba(255,68,68,0.3)',
  },
  detailBtnText: {
    color: '#888',
    fontSize: 13,
    fontWeight: '500',
  },
  detailBtnPrimaryText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
  detailBtnDangerText: {
    color: '#ff4444',
    fontSize: 13,
    fontWeight: '500',
  },
});
