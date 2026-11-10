import { File, UploadType, type UploadTask } from 'expo-file-system';

import { UPLOAD_TIMEOUT_MS } from '@/lib/config';
import { calculateUploadProgress } from '@/lib/upload-progress';
import type { AnalysisMetadata, VideoDraft } from '@/types/analysis';

export interface HealthResponse {
  status: string;
  service: string;
}

export interface AnalysisUpload {
  promise: Promise<AnalysisMetadata>;
  cancel: () => void;
}

function getApiBaseUrl(): string {
  const value = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/$/, '');
  if (!value) {
    throw new Error('Missing EXPO_PUBLIC_API_URL in apps/mobile/.env.local');
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function extractErrorMessage(body: string, status: number): string {
  try {
    const parsed: unknown = JSON.parse(body);
    if (isRecord(parsed)) {
      if (typeof parsed.detail === 'string') {
        return parsed.detail;
      }
      if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
        const first = parsed.detail[0];
        if (isRecord(first) && typeof first.msg === 'string') {
          return first.msg;
        }
      }
    }
  } catch {
    // Fall back to an HTTP status message when the server did not return JSON.
  }
  return `Backend returned HTTP ${status}`;
}

function isAnalysisMetadata(value: unknown): value is AnalysisMetadata {
  if (!isRecord(value)) {
    return false;
  }
  const sourceIsValid = value.source === 'in_app_camera' || value.source === 'photo_library';
  const recordedAtIsValid = value.recorded_at === null || typeof value.recorded_at === 'string';
  return (
    typeof value.analysis_id === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.analysis_id) &&
    typeof value.original_filename === 'string' &&
    sourceIsValid &&
    recordedAtIsValid &&
    typeof value.uploaded_at === 'string' &&
    typeof value.file_size_bytes === 'number' &&
    typeof value.content_type === 'string' &&
    value.status === 'uploaded'
  );
}

function parseAnalysis(body: string): AnalysisMetadata {
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    throw new Error('The backend returned an unreadable upload response.');
  }
  if (!isAnalysisMetadata(parsed)) {
    throw new Error('The backend did not return a valid analysis ID.');
  }
  return parsed;
}

function mimeTypeForFilename(filename: string): string {
  return filename.toLowerCase().endsWith('.mov') ? 'video/quicktime' : 'video/mp4';
}

async function fetchWithTimeout(
  input: string,
  init: RequestInit = {},
  timeoutMs = 15_000,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('The backend request timed out.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/health`);
  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }
  const data: unknown = await response.json();
  if (
    !isRecord(data) ||
    typeof data.status !== 'string' ||
    typeof data.service !== 'string'
  ) {
    throw new Error('The backend health response was invalid.');
  }
  return { status: data.status, service: data.service };
}

export function createAnalysisUpload(
  draft: VideoDraft,
  onProgress: (percent: number) => void,
): AnalysisUpload {
  const file = new File(draft.uri);
  if (!file.exists) {
    throw new Error('The selected video is no longer available on this device.');
  }
  const inferredMimeType = mimeTypeForFilename(file.name);
  const draftMimeType = draft.mimeType.toLowerCase();
  const uploadMimeType =
    (inferredMimeType === 'video/quicktime' && draftMimeType === 'video/quicktime') ||
    (inferredMimeType === 'video/mp4' &&
      (draftMimeType === 'video/mp4' || draftMimeType === 'application/mp4'))
      ? draftMimeType
      : inferredMimeType;

  const controller = new AbortController();
  const parameters: Record<string, string> = {
    source: draft.source,
    original_filename: draft.filename,
  };
  if (draft.recordedAt) {
    parameters.recorded_at = draft.recordedAt;
  }

  let task: UploadTask | undefined;
  const promise = (async () => {
    const timeout = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);
    try {
      task = file.createUploadTask(`${getApiBaseUrl()}/api/v1/analyses`, {
        httpMethod: 'POST',
        uploadType: UploadType.MULTIPART,
        fieldName: 'video',
        mimeType: uploadMimeType,
        parameters,
        signal: controller.signal,
        sessionType: 'foreground',
        onProgress: ({ bytesSent, totalBytes }) => {
          onProgress(calculateUploadProgress(bytesSent, totalBytes));
        },
      });
      const result = await task.uploadAsync();
      if (result.status < 200 || result.status >= 300) {
        throw new Error(extractErrorMessage(result.body, result.status));
      }
      const analysis = parseAnalysis(result.body);
      onProgress(100);
      return analysis;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Upload cancelled or timed out. The video was kept for retry.');
      }
      throw error;
    } finally {
      clearTimeout(timeout);
      task?.release();
    }
  })();

  return {
    promise,
    cancel: () => {
      task?.cancel();
      controller.abort();
    },
  };
}

export async function listAnalyses(): Promise<AnalysisMetadata[]> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/v1/analyses`);
  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }
  const data: unknown = await response.json();
  if (
    !isRecord(data) ||
    !Array.isArray(data.items) ||
    !data.items.every(isAnalysisMetadata)
  ) {
    throw new Error('The backend returned an invalid uploads list.');
  }
  return data.items;
}

export async function deleteAnalysis(analysisId: string): Promise<void> {
  const response = await fetchWithTimeout(
    `${getApiBaseUrl()}/api/v1/analyses/${encodeURIComponent(analysisId)}`,
    { method: 'DELETE' },
  );
  if (!response.ok) {
    const body = await response.text();
    throw new Error(extractErrorMessage(body, response.status));
  }
}
