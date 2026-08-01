import { api } from "@/lib/api/client";
import type { Attachment } from "@/lib/api/types";

export async function uploadFile(file: {
  uri: string;
  name: string;
  mimeType: string;
}): Promise<Attachment> {
  const form = new FormData();
  // React Native's fetch/FormData accepts { uri, name, type } directly for files
  // picked via expo-image-picker/expo-document-picker — not a real Blob/File.
  form.append("file", { uri: file.uri, name: file.name, type: file.mimeType } as unknown as Blob);

  const { data } = await api.post<Attachment>("/files/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getAttachment(attachmentId: string): Promise<Attachment> {
  const { data } = await api.get<Attachment>(`/files/${attachmentId}`);
  return data;
}
