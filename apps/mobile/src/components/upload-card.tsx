import { Pressable, StyleSheet, Text, View } from 'react-native';

import { formatBytes, formatLocalDate, formatSource } from '@/lib/format';
import type { AnalysisMetadata } from '@/types/analysis';

interface UploadCardProps {
  analysis: AnalysisMetadata;
  isDeleting: boolean;
  onDelete: () => void;
}

export function UploadCard({ analysis, isDeleting, onDelete }: UploadCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text numberOfLines={2} style={styles.filename}>{analysis.original_filename}</Text>
        <View style={styles.statusPill}>
          <Text style={styles.statusText}>{analysis.status}</Text>
        </View>
      </View>
      <Text style={styles.detail}>Source: {formatSource(analysis.source)}</Text>
      <Text style={styles.detail}>Size: {formatBytes(analysis.file_size_bytes)}</Text>
      <Text style={styles.detail}>
        Recorded: {analysis.recorded_at ? formatLocalDate(analysis.recorded_at) : 'Recording date unavailable'}
      </Text>
      <Text style={styles.detail}>Uploaded: {formatLocalDate(analysis.uploaded_at)}</Text>
      <Pressable
        accessibilityRole="button"
        disabled={isDeleting}
        onPress={onDelete}
        style={({ pressed }) => [styles.deleteButton, pressed && styles.pressed]}
      >
        <Text style={styles.deleteText}>{isDeleting ? 'Deleting…' : 'Delete upload'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 7,
    borderRadius: 16,
    backgroundColor: '#FFFFFF',
    padding: 17,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  filename: {
    flex: 1,
    color: '#17293C',
    fontSize: 17,
    fontWeight: '800',
  },
  statusPill: {
    borderRadius: 999,
    backgroundColor: '#E4F4EA',
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  statusText: {
    color: '#216E4C',
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  detail: {
    color: '#526579',
    fontSize: 14,
    lineHeight: 20,
  },
  deleteButton: {
    alignSelf: 'flex-start',
    marginTop: 5,
    borderRadius: 9,
    backgroundColor: '#FCE8E6',
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  deleteText: {
    color: '#A52A2A',
    fontWeight: '700',
  },
  pressed: {
    opacity: 0.7,
  },
});
