import { CameraView, useCameraPermissions, useMicrophonePermissions } from 'expo-camera';
import { File } from 'expo-file-system';
import * as ImagePicker from 'expo-image-picker';
import { Link } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { VideoPreview } from '@/components/video-preview';
import { createAnalysisUpload, type AnalysisUpload } from '@/lib/api';
import { MAX_RECORDING_DURATION_SECONDS, MAX_UPLOAD_BYTES } from '@/lib/config';
import { formatBytes, formatDuration } from '@/lib/format';
import type { AnalysisMetadata, VideoDraft } from '@/types/analysis';

interface RecordingStats {
  durationSeconds: number;
  fileSizeBytes?: number;
}

function fileNameFromUri(uri: string, fallback: string): string {
  const rawName = uri.split('?')[0].split('/').pop();
  if (!rawName) return fallback;
  try {
    return decodeURIComponent(rawName);
  } catch {
    return rawName;
  }
}

function videoMimeType(filename: string, provided?: string): string {
  if (provided) return provided;
  return filename.toLowerCase().endsWith('.mov') ? 'video/quicktime' : 'video/mp4';
}

function deleteOwnedDraft(draft: VideoDraft): boolean {
  if (!draft.isOwnedTemporary) return true;
  try {
    const file = new File(draft.uri);
    if (file.exists) file.delete();
    return true;
  } catch {
    return false;
  }
}

export default function UploadScreen() {
  const cameraRef = useRef<CameraView | null>(null);
  const recordingInFlight = useRef(false);
  const recordingStartedAt = useRef<string | null>(null);
  const recordingStats = useRef<RecordingStats>({ durationSeconds: 0 });
  const activeUpload = useRef<AnalysisUpload | null>(null);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [microphonePermission, requestMicrophonePermission] = useMicrophonePermissions();
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [stats, setStats] = useState<RecordingStats>({ durationSeconds: 0 });
  const [draft, setDraft] = useState<VideoDraft | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploaded, setUploaded] = useState<AnalysisMetadata | null>(null);

  useEffect(() => () => activeUpload.current?.cancel(), []);

  async function chooseFromPhotos() {
    setErrorMessage(null);
    setUploaded(null);
    try {
      const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'], allowsEditing: false });
      if (result.canceled) return;
      const asset = result.assets[0];
      if (!asset) throw new Error('No video was returned by the picker.');
      if (asset.fileSize !== undefined && asset.fileSize > MAX_UPLOAD_BYTES) {
        Alert.alert('Video is too large', 'Choose a video smaller than 100 MB.');
        return;
      }
      const uriFilename = fileNameFromUri(asset.uri, 'selected-video.mp4');
      setDraft({
        uri: asset.uri,
        filename: asset.fileName ?? uriFilename,
        fileSizeBytes: asset.fileSize,
        durationSeconds: asset.duration == null ? undefined : asset.duration / 1000,
        mimeType: videoMimeType(uriFilename, asset.mimeType),
        source: 'photo_library',
        recordedAt: null,
        isOwnedTemporary: false,
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Could not open the video picker.');
    }
  }

  async function openCamera() {
    setErrorMessage(null);
    setUploaded(null);
    const cameraResult = cameraPermission?.granted ? cameraPermission : await requestCameraPermission();
    const microphoneResult = microphonePermission?.granted ? microphonePermission : await requestMicrophonePermission();
    if (!cameraResult.granted || !microphoneResult.granted) {
      setErrorMessage('Camera and microphone permission are required to record a clip.');
      return;
    }
    setCameraReady(false);
    setCameraOpen(true);
  }

  async function startRecording() {
    if (!cameraReady || recordingInFlight.current || !cameraRef.current) return;
    recordingInFlight.current = true;
    recordingStartedAt.current = new Date().toISOString();
    recordingStats.current = { durationSeconds: 0 };
    setStats({ durationSeconds: 0 });
    setIsRecording(true);
    setErrorMessage(null);
    try {
      const result = await cameraRef.current.recordAsync({ maxDuration: MAX_RECORDING_DURATION_SECONDS, progressUpdateInterval: 0.25 });
      if (!result) throw new Error('The camera did not return a recording.');
      const file = new File(result.uri);
      const uriFilename = fileNameFromUri(result.uri, `recording-${Date.now()}.mp4`);
      const finalStats = recordingStats.current;
      setDraft({
        uri: result.uri,
        filename: uriFilename,
        fileSizeBytes: file.size ?? finalStats.fileSizeBytes,
        durationSeconds: finalStats.durationSeconds,
        mimeType: videoMimeType(uriFilename),
        source: 'in_app_camera',
        recordedAt: recordingStartedAt.current,
        isOwnedTemporary: true,
      });
      setCameraOpen(false);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Recording failed.');
    } finally {
      recordingInFlight.current = false;
      setIsRecording(false);
    }
  }

  function stopRecording() {
    if (recordingInFlight.current) cameraRef.current?.stopRecording();
  }

  function updateRecordingStats(next: RecordingStats) {
    recordingStats.current = next;
    setStats(next);
  }

  function discardDraft() {
    if (!draft || isUploading) return;
    if (!deleteOwnedDraft(draft)) {
      setErrorMessage('The temporary recording could not be deleted; the operating system may clear it later.');
    }
    setDraft(null);
    setUploaded(null);
  }

  async function changeDraft() {
    if (!draft || isUploading) return;
    const source = draft.source;
    discardDraft();
    if (source === 'in_app_camera') await openCamera();
    else await chooseFromPhotos();
  }

  async function uploadDraft() {
    if (!draft || isUploading) return;
    setErrorMessage(null);
    setUploaded(null);
    setUploadProgress(0);
    setIsUploading(true);
    try {
      const upload = createAnalysisUpload(draft, setUploadProgress);
      activeUpload.current = upload;
      const analysis = await upload.promise;
      const cleaned = deleteOwnedDraft(draft);
      setDraft(null);
      setUploaded(analysis);
      if (!cleaned) setErrorMessage('Upload succeeded, but the temporary recording could not be deleted.');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Upload failed. The video was kept for retry.');
    } finally {
      activeUpload.current = null;
      setIsUploading(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <View>
        <Text style={styles.eyebrow}>RECORD / UPLOAD</Text>
        <Text style={styles.title}>Add a training clip</Text>
        <Text style={styles.subtitle}>Nothing uploads until you preview the clip and tap Upload.</Text>
      </View>
      {errorMessage && <View style={styles.errorCard}><Text style={styles.errorText}>{errorMessage}</Text></View>}
      {uploaded && (
        <View style={styles.successCard}>
          <Text style={styles.successTitle}>Upload complete</Text>
          <Text style={styles.successText}>Analysis ID: {uploaded.analysis_id}</Text>
          <Link href="/uploads" asChild><Pressable style={styles.successLink}><Text style={styles.successLinkText}>View My Uploads</Text></Pressable></Link>
        </View>
      )}
      {cameraOpen && !draft ? (
        <View style={styles.cameraCard}>
          <CameraView
            ref={cameraRef}
            style={styles.camera}
            facing="back"
            mode="video"
            onCameraReady={() => setCameraReady(true)}
            onMountError={({ message }) => setErrorMessage(message)}
            onRecordingProgress={({ duration, fileSize }) => updateRecordingStats({ durationSeconds: duration, fileSizeBytes: fileSize })}
          />
          <View style={styles.recordingStatus}>
            <View style={[styles.recordDot, isRecording && styles.recordDotActive]} />
            <Text style={styles.recordingText}>{isRecording ? `Recording ${formatDuration(stats.durationSeconds)} / 0:${MAX_RECORDING_DURATION_SECONDS}` : cameraReady ? 'Camera ready' : 'Starting camera…'}</Text>
            {stats.fileSizeBytes !== undefined && isRecording && <Text style={styles.recordingSize}>{formatBytes(stats.fileSizeBytes)}</Text>}
          </View>
          {isRecording ? (
            <Pressable accessibilityRole="button" onPress={stopRecording} style={styles.stopButton}><Text style={styles.buttonText}>Stop recording</Text></Pressable>
          ) : (
            <Pressable accessibilityRole="button" disabled={!cameraReady} onPress={startRecording} style={[styles.recordButton, !cameraReady && styles.disabled]}><Text style={styles.buttonText}>Start recording</Text></Pressable>
          )}
          {!isRecording && <Pressable accessibilityRole="button" onPress={() => setCameraOpen(false)} style={styles.cancelCameraButton}><Text style={styles.cancelCameraText}>Close camera</Text></Pressable>}
        </View>
      ) : draft ? (
        <VideoPreview key={draft.uri} draft={draft} isUploading={isUploading} progress={uploadProgress} onChange={changeDraft} onDiscard={discardDraft} onUpload={uploadDraft} onCancelUpload={() => activeUpload.current?.cancel()} />
      ) : (
        <View style={styles.choices}>
          <Pressable accessibilityRole="button" onPress={openCamera} style={styles.primaryChoice}>
            <Text style={styles.choiceKicker}>CAMERA</Text><Text style={styles.primaryChoiceTitle}>Record a new clip</Text><Text style={styles.primaryChoiceText}>Record up to {MAX_RECORDING_DURATION_SECONDS} seconds in temporary app storage.</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={chooseFromPhotos} style={styles.secondaryChoice}>
            <Text style={[styles.choiceKicker, styles.secondaryKicker]}>PHOTOS</Text><Text style={styles.secondaryChoiceTitle}>Choose an existing video</Text><Text style={styles.secondaryChoiceText}>The original Photos asset is never changed or deleted.</Text>
          </Pressable>
        </View>
      )}
      <Text style={styles.draftNote}>A recording draft stays available while this screen remains open. Temporary cache files can also be cleared by the operating system.</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, gap: 16, backgroundColor: '#F3F6FA', paddingHorizontal: 20, paddingTop: 56, paddingBottom: 120 },
  eyebrow: { marginBottom: 7, color: '#216E4C', fontSize: 12, fontWeight: '800', letterSpacing: 1.4 },
  title: { marginBottom: 7, color: '#17293C', fontSize: 30, fontWeight: '900' },
  subtitle: { color: '#637489', fontSize: 15, lineHeight: 22 },
  errorCard: { borderRadius: 12, backgroundColor: '#FCE8E6', padding: 14 }, errorText: { color: '#8B2424', lineHeight: 20 },
  successCard: { gap: 7, borderRadius: 16, backgroundColor: '#E4F4EA', padding: 16 }, successTitle: { color: '#185A3D', fontSize: 17, fontWeight: '800' }, successText: { color: '#2F5D49', fontSize: 12 }, successLink: { alignSelf: 'flex-start', paddingVertical: 5 }, successLinkText: { color: '#185A3D', fontWeight: '800', textDecorationLine: 'underline' },
  choices: { gap: 12 }, primaryChoice: { borderRadius: 20, backgroundColor: '#216E4C', padding: 22 }, secondaryChoice: { borderWidth: 1, borderColor: '#D7E0E8', borderRadius: 20, backgroundColor: '#FFFFFF', padding: 22 },
  choiceKicker: { marginBottom: 7, color: '#9ED8B9', fontSize: 11, fontWeight: '800', letterSpacing: 1.2 }, secondaryKicker: { color: '#216E4C' }, primaryChoiceTitle: { marginBottom: 7, color: '#FFFFFF', fontSize: 20, fontWeight: '800' }, primaryChoiceText: { color: '#D9EEE3', lineHeight: 20 }, secondaryChoiceTitle: { marginBottom: 7, color: '#17293C', fontSize: 20, fontWeight: '800' }, secondaryChoiceText: { color: '#637489', lineHeight: 20 },
  cameraCard: { gap: 12, borderRadius: 20, backgroundColor: '#FFFFFF', padding: 14 }, camera: { width: '100%', aspectRatio: 9 / 16, maxHeight: 480, overflow: 'hidden', borderRadius: 16 },
  recordingStatus: { minHeight: 24, flexDirection: 'row', alignItems: 'center', gap: 8 }, recordDot: { width: 10, height: 10, borderRadius: 999, backgroundColor: '#94A3B8' }, recordDotActive: { backgroundColor: '#D12C2C' }, recordingText: { flex: 1, color: '#35475A', fontWeight: '700' }, recordingSize: { color: '#637489', fontSize: 12 },
  recordButton: { minHeight: 50, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: '#216E4C' }, stopButton: { minHeight: 50, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: '#B12828' }, buttonText: { color: '#FFFFFF', fontSize: 15, fontWeight: '800' }, cancelCameraButton: { alignItems: 'center', padding: 9 }, cancelCameraText: { color: '#526579', fontWeight: '700' }, disabled: { opacity: 0.5 }, draftNote: { color: '#7A8A9B', fontSize: 12, lineHeight: 18 },
});
