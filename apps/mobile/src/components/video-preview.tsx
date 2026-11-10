import { useEvent } from 'expo';
import { useVideoPlayer, VideoView } from 'expo-video';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { formatBytes, formatDuration } from '@/lib/format';
import type { VideoDraft } from '@/types/analysis';

interface VideoPreviewProps {
  draft: VideoDraft;
  isUploading: boolean;
  progress: number;
  onChange: () => void;
  onDiscard: () => void;
  onUpload: () => void;
  onCancelUpload: () => void;
}

export function VideoPreview({
  draft,
  isUploading,
  progress,
  onChange,
  onDiscard,
  onUpload,
  onCancelUpload,
}: VideoPreviewProps) {
  const player = useVideoPlayer(draft.uri);
  const { isPlaying } = useEvent(player, 'playingChange', {
    isPlaying: player.playing,
  });

  return (
    <View style={styles.card}>
      <Text style={styles.heading}>Preview your clip</Text>
      <VideoView
        player={player}
        nativeControls
        contentFit="contain"
        style={styles.video}
      />
      <Pressable
        accessibilityRole="button"
        onPress={() => (isPlaying ? player.pause() : player.play())}
        style={styles.playButton}
      >
        <Text style={styles.playButtonText}>{isPlaying ? 'Pause preview' : 'Play preview'}</Text>
      </Pressable>

      <Text numberOfLines={2} style={styles.filename}>{draft.filename}</Text>
      <Text style={styles.meta}>
        {formatBytes(draft.fileSizeBytes)} · {formatDuration(draft.durationSeconds)}
      </Text>

      {isUploading ? (
        <View style={styles.uploadPanel}>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${progress}%` }]} />
          </View>
          <Text style={styles.progressLabel}>Uploading… {progress}%</Text>
          <Pressable accessibilityRole="button" onPress={onCancelUpload} style={styles.cancelButton}>
            <Text style={styles.cancelText}>Cancel upload</Text>
          </Pressable>
        </View>
      ) : (
        <>
          <Pressable accessibilityRole="button" onPress={onUpload} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Upload video</Text>
          </Pressable>
          <View style={styles.secondaryRow}>
            <Pressable accessibilityRole="button" onPress={onChange} style={styles.secondaryButton}>
              <Text style={styles.secondaryText}>
                {draft.source === 'in_app_camera' ? 'Retake' : 'Replace'}
              </Text>
            </Pressable>
            <Pressable accessibilityRole="button" onPress={onDiscard} style={styles.secondaryButton}>
              <Text style={styles.discardText}>Discard</Text>
            </Pressable>
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 18,
    gap: 12,
  },
  heading: {
    color: '#17293C',
    fontSize: 20,
    fontWeight: '800',
  },
  video: {
    width: '100%',
    aspectRatio: 9 / 16,
    maxHeight: 430,
    backgroundColor: '#07131F',
    borderRadius: 14,
  },
  playButton: {
    alignSelf: 'flex-start',
    borderRadius: 9,
    backgroundColor: '#E7F2EC',
    paddingHorizontal: 13,
    paddingVertical: 9,
  },
  playButtonText: {
    color: '#216E4C',
    fontWeight: '700',
  },
  filename: {
    color: '#17293C',
    fontSize: 16,
    fontWeight: '700',
  },
  meta: {
    color: '#637489',
    fontSize: 14,
  },
  uploadPanel: {
    gap: 10,
  },
  progressTrack: {
    height: 10,
    overflow: 'hidden',
    borderRadius: 999,
    backgroundColor: '#E2E8F0',
  },
  progressFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: '#216E4C',
  },
  progressLabel: {
    color: '#35475A',
    fontWeight: '700',
  },
  primaryButton: {
    minHeight: 50,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    backgroundColor: '#216E4C',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
  },
  secondaryRow: {
    flexDirection: 'row',
    gap: 10,
  },
  secondaryButton: {
    flex: 1,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 11,
    padding: 12,
  },
  secondaryText: {
    color: '#35475A',
    fontWeight: '700',
  },
  discardText: {
    color: '#A52A2A',
    fontWeight: '700',
  },
  cancelButton: {
    alignSelf: 'flex-start',
    paddingVertical: 8,
  },
  cancelText: {
    color: '#A52A2A',
    fontWeight: '700',
  },
});
