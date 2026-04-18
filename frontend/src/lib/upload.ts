import { api, apiClient } from "./api";

export interface UploadedFile {
  s3Key: string;
  filename: string;
  size: number;
  mimeType: string;
}

export async function uploadFile(file: File): Promise<UploadedFile> {
  // 1. Get presigned URL
  const { url, fields, key } = await api.post(
    `/files/presign-upload?filename=${encodeURIComponent(file.name)}&content_type=${encodeURIComponent(file.type)}`
  );

  // 2. Upload directly to S3/MinIO
  const form = new FormData();
  Object.entries(fields as Record<string, string>).forEach(([k, v]) => form.append(k, v));
  form.append("file", file); // must be last

  const res = await fetch(url, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status} ${res.statusText}`);

  // 3. Validate on backend
  await api.post(`/files/validate?s3_key=${encodeURIComponent(key)}`);

  return { s3Key: key, filename: file.name, size: file.size, mimeType: file.type };
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}
