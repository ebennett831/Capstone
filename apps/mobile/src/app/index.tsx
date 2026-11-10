import { Link } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { checkHealth } from '@/lib/api';

type ConnectionStatus = 'idle' | 'checking' | 'connected' | 'error';

export default function HomeScreen() {
  const [status, setStatus] = useState<ConnectionStatus>('idle');
  const [message, setMessage] = useState('Tap the button to test your backend.');

  async function checkBackend() {
    setStatus('checking');
    setMessage('Contacting FastAPI…');

    try {
      const data = await checkHealth();
      if (data.status !== 'ok') {
        throw new Error('Backend responded, but did not report status "ok".');
      }
      setStatus('connected');
      setMessage(`Connected to ${data.service}!`);
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
      <View style={styles.hero}>
        <Text style={styles.eyebrow}>AI LACROSSE COACH</Text>
        <Text style={styles.title}>Train with clips that stay under your control.</Text>
        <Text style={styles.subtitle}>
          Record a short rep or choose one from Photos, review it, then upload it to your local coaching backend.
        </Text>
      </View>

      <View style={styles.actionGrid}>
        <Link href="/upload" asChild>
          <Pressable style={({ pressed }) => [styles.actionCard, pressed && styles.pressed]}>
            <Text style={styles.actionKicker}>NEW CLIP</Text>
            <Text style={styles.actionTitle}>Record or upload</Text>
            <Text style={styles.actionDescription}>Preview a video before anything leaves your phone.</Text>
          </Pressable>
        </Link>
        <Link href="/uploads" asChild>
          <Pressable style={({ pressed }) => [styles.actionCard, pressed && styles.pressed]}>
            <Text style={styles.actionKicker}>LOCAL HISTORY</Text>
            <Text style={styles.actionTitle}>My Uploads</Text>
            <Text style={styles.actionDescription}>Review metadata or delete a stored clip.</Text>
          </Pressable>
        </Link>
      </View>

      <View style={styles.devCard}>
        <Text style={styles.devLabel}>DEVELOPMENT</Text>
        <Text style={styles.devTitle}>Backend connection</Text>
        <Pressable
          accessibilityRole="button"
          onPress={checkBackend}
          disabled={status === 'checking'}
          style={({ pressed }) => [
            styles.button,
            pressed && styles.pressed,
            status === 'checking' && styles.disabled,
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
            status === 'connected' && styles.successStatusCard,
            status === 'error' && styles.errorStatusCard,
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
  container: { flexGrow: 1, backgroundColor: '#F3F6FA', paddingHorizontal: 20, paddingTop: 56, paddingBottom: 120, gap: 18 },
  hero: { borderRadius: 24, backgroundColor: '#163A2B', padding: 24 },
  eyebrow: { marginBottom: 12, color: '#A9E2C4', fontSize: 12, fontWeight: '800', letterSpacing: 1.5 },
  title: { marginBottom: 12, color: '#FFFFFF', fontSize: 30, fontWeight: '900', lineHeight: 36 },
  subtitle: { color: '#D4E7DD', fontSize: 16, lineHeight: 23 },
  actionGrid: { gap: 12 },
  actionCard: { borderRadius: 18, backgroundColor: '#FFFFFF', padding: 20 },
  actionKicker: { marginBottom: 6, color: '#216E4C', fontSize: 11, fontWeight: '800', letterSpacing: 1.2 },
  actionTitle: { marginBottom: 5, color: '#17293C', fontSize: 20, fontWeight: '800' },
  actionDescription: { color: '#637489', fontSize: 14, lineHeight: 20 },
  devCard: { borderRadius: 18, backgroundColor: '#FFFFFF', padding: 20 },
  devLabel: { marginBottom: 5, color: '#7A8A9B', fontSize: 11, fontWeight: '800', letterSpacing: 1.2 },
  devTitle: { marginBottom: 14, color: '#17293C', fontSize: 18, fontWeight: '800' },
  button: { minHeight: 50, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: '#216E4C', padding: 14 },
  buttonText: { color: '#FFFFFF', fontSize: 15, fontWeight: '700' },
  disabled: { opacity: 0.6 },
  pressed: { opacity: 0.75 },
  statusCard: { marginTop: 12, borderRadius: 12, backgroundColor: '#F1F5F9', padding: 14 },
  successStatusCard: { backgroundColor: '#E4F4EA' },
  errorStatusCard: { backgroundColor: '#FCE8E6' },
  statusLabel: { marginBottom: 3, color: '#17293C', fontSize: 14, fontWeight: '700' },
  statusMessage: { color: '#35475A', fontSize: 14, lineHeight: 20 },
});
