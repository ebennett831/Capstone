import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { UploadCard } from '@/components/upload-card';
import { deleteAnalysis, listAnalyses } from '@/lib/api';
import type { AnalysisMetadata } from '@/types/analysis';

export default function UploadsScreen() {
  const [items, setItems] = useState<AnalysisMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadUploads = useCallback(async (refreshing = false) => {
    if (refreshing) setIsRefreshing(true);
    else setIsLoading(true);
    setErrorMessage(null);
    try {
      setItems(await listAnalyses());
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Could not load uploads.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { void loadUploads(); }, [loadUploads]));

  async function performDelete(analysis: AnalysisMetadata) {
    setDeletingId(analysis.analysis_id);
    setErrorMessage(null);
    try {
      await deleteAnalysis(analysis.analysis_id);
      await loadUploads(true);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Could not delete the upload.');
    } finally {
      setDeletingId(null);
    }
  }

  function confirmDelete(analysis: AnalysisMetadata) {
    Alert.alert('Delete this upload?', `${analysis.original_filename} and its metadata will be removed from the local backend.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => void performDelete(analysis) },
    ]);
  }

  return (
    <ScrollView contentContainerStyle={styles.container} refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={() => void loadUploads(true)} />}>
      <View style={styles.headerRow}>
        <View style={styles.headerCopy}><Text style={styles.eyebrow}>LOCAL BACKEND</Text><Text style={styles.title}>My Uploads</Text></View>
        <Pressable accessibilityRole="button" onPress={() => void loadUploads(true)} style={styles.refreshButton}><Text style={styles.refreshText}>Refresh</Text></Pressable>
      </View>
      <Text style={styles.subtitle}>Metadata for videos stored by your development server. Playback remains local to the pre-upload preview in this milestone.</Text>
      {errorMessage && <View style={styles.errorCard}><Text style={styles.errorText}>{errorMessage}</Text><Pressable accessibilityRole="button" onPress={() => void loadUploads()} style={styles.retryButton}><Text style={styles.retryText}>Try again</Text></Pressable></View>}
      {isLoading && !isRefreshing ? (
        <View style={styles.centerState}><ActivityIndicator color="#216E4C" size="large" /><Text style={styles.stateText}>Loading uploads…</Text></View>
      ) : items.length === 0 && !errorMessage ? (
        <View style={styles.centerState}><Text style={styles.emptyTitle}>No uploads yet</Text><Text style={styles.stateText}>Your successfully uploaded clips will appear here.</Text></View>
      ) : (
        <View style={styles.list}>{items.map((analysis) => <UploadCard key={analysis.analysis_id} analysis={analysis} isDeleting={deletingId === analysis.analysis_id} onDelete={() => confirmDelete(analysis)} />)}</View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: '#F3F6FA', paddingHorizontal: 20, paddingTop: 56, paddingBottom: 120 }, headerRow: { flexDirection: 'row', alignItems: 'center', gap: 12 }, headerCopy: { flex: 1 }, eyebrow: { marginBottom: 5, color: '#216E4C', fontSize: 12, fontWeight: '800', letterSpacing: 1.4 }, title: { color: '#17293C', fontSize: 30, fontWeight: '900' }, subtitle: { marginTop: 9, marginBottom: 18, color: '#637489', fontSize: 14, lineHeight: 21 }, refreshButton: { borderRadius: 10, backgroundColor: '#E7F2EC', paddingHorizontal: 13, paddingVertical: 10 }, refreshText: { color: '#216E4C', fontWeight: '800' }, list: { gap: 12 }, centerState: { alignItems: 'center', gap: 10, borderRadius: 18, backgroundColor: '#FFFFFF', padding: 32 }, emptyTitle: { color: '#17293C', fontSize: 19, fontWeight: '800' }, stateText: { color: '#637489', textAlign: 'center', lineHeight: 20 }, errorCard: { gap: 8, marginBottom: 14, borderRadius: 14, backgroundColor: '#FCE8E6', padding: 15 }, errorText: { color: '#8B2424', lineHeight: 20 }, retryButton: { alignSelf: 'flex-start', paddingVertical: 4 }, retryText: { color: '#8B2424', fontWeight: '800', textDecorationLine: 'underline' },
});
