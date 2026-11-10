export type AnalysisSource = 'in_app_camera' | 'photo_library';

export type AnalysisStatus = 'uploaded';

export interface AnalysisMetadata {
  analysis_id: string;
  original_filename: string;
  source: AnalysisSource;
  recorded_at: string | null;
  uploaded_at: string;
  file_size_bytes: number;
  content_type: string;
  status: AnalysisStatus;
}

export interface AnalysisListResponse {
  items: AnalysisMetadata[];
}

export interface VideoDraft {
  uri: string;
  filename: string;
  fileSizeBytes?: number;
  durationSeconds?: number;
  mimeType: string;
  source: AnalysisSource;
  recordedAt: string | null;
  isOwnedTemporary: boolean;
}
