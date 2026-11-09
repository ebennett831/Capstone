import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

type ConnectionStatus = 'idle' | 'checking' | 'connected' | 'error';

export default function HomeScreen() {
  const [status, setStatus] = useState<ConnectionStatus>('idle');
  const [message, setMessage] = useState('Tap the button to test your backend.');

  async function checkBackend() {
    setStatus('checking');
    setMessage('Contacting FastAPI...');

    try {
      const apiUrl = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/$/, '');
      if (!apiUrl) {
        throw new Error('Missing EXPO_PUBLIC_API_URL in apps/mobile/.env.local');
      }

      const response = await fetch(`${apiUrl}/health`);
      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }

      const data: { status?: string; service?: string } = await response.json();
      if (data.status !== 'ok') {
        throw new Error('Backend responded, but did not report status "ok".');
      }

      setStatus('connected');
      setMessage(`Connected to ${data.service ?? 'FastAPI'}!`);
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Unknown connection error');
    }
  }

  const statusLabel = {
    idle: 'Not checked',
    checking: 'Checking connection',
    connected: 'Backend online',
    error: 'Connection failed',
  }[status];

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.card}>
        <Text style={styles.eyebrow}>CAPSTONE PROJECT</Text>
        <Text style={styles.title}>AI Lacrosse Coach</Text>
        <Text style={styles.subtitle}>
          Your training assistant, powered by computer vision.
        </Text>

        <View style={styles.separator} />

        <Text style={styles.sectionTitle}>Milestone 1: App ↔ API</Text>
        <Text style={styles.description}>
          Your phone will send a request to the FastAPI server running on your computer.
        </Text>

        <Pressable
          accessibilityRole="button"
          onPress={checkBackend}
          disabled={status === 'checking'}
          style={({ pressed }) => [
            styles.button,
            pressed && styles.buttonPressed,
            status === 'checking' && styles.buttonDisabled,
          ]}
        >
          {status === 'checking' ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.buttonText}>Test Backend Connection</Text>
          )}
        </Pressable>

        <View
          style={[
            styles.statusCard,
            status === 'connected' && styles.successCard,
            status === 'error' && styles.errorCard,
          ]}
        >
          <Text style={styles.statusLabel}>{statusLabel}</Text>
          <Text style={styles.statusMessage}>{message}</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    backgroundColor: '#F3F6FA',
    padding: 24,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 24,
  },
  eyebrow: {
    color: '#216E4C',
    fontSize: 12,
    letterSpacing: 1.5,
    fontWeight: '700',
    marginBottom: 10,
  },
  title: {
    color: '#17293C',
    fontSize: 30,
    fontWeight: '800',
    marginBottom: 10,
  },
  subtitle: {
    color: '#637489',
    fontSize: 16,
    lineHeight: 23,
  },
  separator: {
    backgroundColor: '#E2E8F0',
    height: 1,
    marginVertical: 26,
  },
  sectionTitle: {
    color: '#17293C',
    fontWeight: '700',
    fontSize: 18,
    marginBottom: 8,
  },
  description: {
    color: '#637489',
    fontSize: 14,
    lineHeight: 21,
    marginBottom: 22,
  },
  button: {
    backgroundColor: '#216E4C',
    borderRadius: 12,
    padding: 16,
    minHeight: 52,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonPressed: {
    opacity: 0.85,
  },
  buttonDisabled: {
    opacity: 0.65,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  statusCard: {
    backgroundColor: '#F1F5F9',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
  },
  successCard: {
    backgroundColor: '#E4F4EA',
  },
  errorCard: {
    backgroundColor: '#FCE8E6',
  },
  statusLabel: {
    color: '#17293C',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 4,
  },
  statusMessage: {
    color: '#35475A',
    fontSize: 14,
    lineHeight: 20,
  },
});
