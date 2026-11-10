export type UploadByteCount = number | bigint;

export function calculateUploadProgress(
  bytesSent: UploadByteCount,
  totalBytes: UploadByteCount,
): number {
  const normalizedBytesSent = Number(bytesSent);
  const normalizedTotalBytes = Number(totalBytes);

  if (
    !Number.isFinite(normalizedBytesSent) ||
    !Number.isFinite(normalizedTotalBytes) ||
    normalizedTotalBytes <= 0
  ) {
    return 0;
  }

  const percentage = Math.round((normalizedBytesSent / normalizedTotalBytes) * 100);
  if (!Number.isFinite(percentage)) {
    return 0;
  }

  return Math.max(0, Math.min(100, percentage));
}
