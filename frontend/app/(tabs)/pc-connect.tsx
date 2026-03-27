import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAppStore } from '../../src/store/appStore';
import { apiService } from '../../src/services/api';

export default function PCConnectScreen() {
  const { pcConnection, setPCConnection, persistState } = useAppStore();
  const [serverUrl, setServerUrl] = useState(pcConnection.serverUrl);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectedPCs, setConnectedPCs] = useState<string[]>([]);
  const [testText, setTestText] = useState('');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetchConnectedPCs();
    const interval = setInterval(fetchConnectedPCs, 5000);
    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const fetchConnectedPCs = async () => {
    const result = await apiService.getConnectedPCs();
    setConnectedPCs(result.client_ids);
  };

  const connectToServer = async () => {
    if (!serverUrl.trim()) {
      Alert.alert('Error', 'Please enter a server URL');
      return;
    }

    setIsConnecting(true);

    try {
      // Clean up the URL
      let wsUrl = serverUrl.trim();
      if (!wsUrl.startsWith('ws://') && !wsUrl.startsWith('wss://')) {
        wsUrl = `ws://${wsUrl}`;
      }
      if (!wsUrl.includes(':')) {
        wsUrl += ':8765';
      }

      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Connected to PC server');
        setPCConnection({
          isConnected: true,
          serverUrl: wsUrl,
        });
        persistState();
        setIsConnecting(false);
        Alert.alert('Connected', 'Successfully connected to PC server!');
      };

      ws.onclose = () => {
        console.log('Disconnected from PC server');
        setPCConnection({ isConnected: false });
        setIsConnecting(false);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setPCConnection({ isConnected: false });
        setIsConnecting(false);
        Alert.alert('Connection Failed', 'Could not connect to PC server. Make sure the server is running.');
      };

      ws.onmessage = (event) => {
        console.log('Received message:', event.data);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Connection error:', error);
      setIsConnecting(false);
      Alert.alert('Error', 'Failed to connect to server');
    }
  };

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setPCConnection({ isConnected: false });
  };

  const sendTestText = async () => {
    if (!testText.trim()) {
      Alert.alert('Error', 'Please enter some text to send');
      return;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'text',
        payload: { text: testText },
      }));
      Alert.alert('Sent', 'Text sent to PC!');
      setTestText('');
    } else {
      Alert.alert('Not Connected', 'Please connect to a PC server first');
    }
  };

  const sendKeyCommand = (key: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'key',
        payload: { key },
      }));
    } else {
      Alert.alert('Not Connected', 'Please connect to a PC server first');
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.scrollView}>
        <View style={styles.header}>
          <Text style={styles.title}>PC Connection</Text>
          <Text style={styles.subtitle}>Connect to control your PC</Text>
        </View>

        {/* Connection Status */}
        <View style={styles.section}>
          <View style={styles.statusCard}>
            <View style={styles.statusRow}>
              <View
                style={[
                  styles.statusIndicator,
                  { backgroundColor: pcConnection.isConnected ? '#00ff88' : '#ff4444' },
                ]}
              />
              <Text style={styles.statusLabel}>
                {pcConnection.isConnected ? 'Connected' : 'Disconnected'}
              </Text>
            </View>
            {pcConnection.isConnected && (
              <Text style={styles.serverInfo}>{pcConnection.serverUrl}</Text>
            )}
          </View>
        </View>

        {/* Server URL Input */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Server Address</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="desktop-outline" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="192.168.1.100:8765"
              placeholderTextColor="#555"
              value={serverUrl}
              onChangeText={setServerUrl}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
          </View>
          <Text style={styles.hint}>
            Enter the IP address of the PC running the VoiceKey server
          </Text>

          {pcConnection.isConnected ? (
            <TouchableOpacity style={styles.disconnectButton} onPress={disconnect}>
              <Ionicons name="close-circle" size={20} color="#ff4444" />
              <Text style={styles.disconnectButtonText}>Disconnect</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[styles.connectButton, isConnecting && styles.buttonDisabled]}
              onPress={connectToServer}
              disabled={isConnecting}
            >
              {isConnecting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="link" size={20} color="#fff" />
                  <Text style={styles.connectButtonText}>Connect</Text>
                </>
              )}
            </TouchableOpacity>
          )}
        </View>

        {/* Test Controls */}
        {pcConnection.isConnected && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Test Connection</Text>
            
            <View style={styles.testInputContainer}>
              <TextInput
                style={styles.testInput}
                placeholder="Type text to send..."
                placeholderTextColor="#555"
                value={testText}
                onChangeText={setTestText}
              />
              <TouchableOpacity style={styles.sendButton} onPress={sendTestText}>
                <Ionicons name="send" size={20} color="#fff" />
              </TouchableOpacity>
            </View>

            <Text style={styles.quickActionsLabel}>Quick Actions</Text>
            <View style={styles.quickActions}>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => sendKeyCommand('ENTER')}
              >
                <Ionicons name="return-down-back" size={20} color="#fff" />
                <Text style={styles.actionButtonText}>Enter</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => sendKeyCommand('TAB')}
              >
                <Ionicons name="arrow-forward" size={20} color="#fff" />
                <Text style={styles.actionButtonText}>Tab</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => sendKeyCommand('BACKSPACE')}
              >
                <Ionicons name="backspace" size={20} color="#fff" />
                <Text style={styles.actionButtonText}>Delete</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Server Info */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Server Info</Text>
          <View style={styles.infoCard}>
            <Ionicons name="information-circle" size={24} color="#00d4ff" />
            <Text style={styles.infoText}>
              To control your PC, download and run the VoiceKey PC Server application on your computer. The server listens for commands from this app and types text or sends keystrokes to your PC.
            </Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  scrollView: {
    flex: 1,
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
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 12,
  },
  statusCard: {
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#222',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 10,
  },
  statusLabel: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  serverInfo: {
    fontSize: 14,
    color: '#888',
    marginTop: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
    paddingHorizontal: 12,
  },
  inputIcon: {
    marginRight: 8,
  },
  input: {
    flex: 1,
    height: 50,
    color: '#fff',
    fontSize: 16,
  },
  hint: {
    fontSize: 12,
    color: '#666',
    marginTop: 8,
    marginBottom: 16,
  },
  connectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#00d4ff',
    borderRadius: 12,
    paddingVertical: 14,
    gap: 8,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  connectButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  disconnectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 68, 68, 0.1)',
    borderRadius: 12,
    paddingVertical: 14,
    gap: 8,
    borderWidth: 1,
    borderColor: '#ff4444',
  },
  disconnectButtonText: {
    color: '#ff4444',
    fontSize: 16,
    fontWeight: '600',
  },
  testInputContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  testInput: {
    flex: 1,
    backgroundColor: '#111',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
    paddingHorizontal: 16,
    height: 50,
    color: '#fff',
    fontSize: 16,
  },
  sendButton: {
    width: 50,
    height: 50,
    backgroundColor: '#00d4ff',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quickActionsLabel: {
    fontSize: 14,
    color: '#888',
    marginBottom: 12,
  },
  quickActions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionButton: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333',
    gap: 4,
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 12,
  },
  infoCard: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.2)',
  },
  infoText: {
    flex: 1,
    color: '#aaa',
    fontSize: 14,
    lineHeight: 20,
    marginLeft: 12,
  },
});
