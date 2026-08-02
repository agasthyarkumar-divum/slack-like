import { api } from "@/lib/api/client";
import type { Message, MessageListResponse, ThreadRepliesResponse } from "@/lib/api/types";

export async function listMessages(
  channelId: string,
  cursor?: string | null
): Promise<MessageListResponse> {
  const { data } = await api.get<MessageListResponse>(`/channels/${channelId}/messages`, {
    params: cursor ? { cursor } : undefined,
  });
  return data;
}

export async function sendMessage(
  channelId: string,
  input: { content?: string | null; reply_to_id?: string | null; attachment_ids?: string[] }
): Promise<Message> {
  const { data } = await api.post<Message>(`/channels/${channelId}/messages`, input);
  return data;
}

export async function editMessage(messageId: string, content: string): Promise<Message> {
  const { data } = await api.patch<Message>(`/messages/${messageId}`, { content });
  return data;
}

export async function deleteMessage(messageId: string): Promise<Message> {
  const { data } = await api.delete<Message>(`/messages/${messageId}`);
  return data;
}

export async function toggleReaction(messageId: string, emoji: string): Promise<Message> {
  const { data } = await api.post<Message>(`/messages/${messageId}/reactions`, { emoji });
  return data;
}

export async function listReplies(messageId: string, cursor?: string | null): Promise<ThreadRepliesResponse> {
  const { data } = await api.get<ThreadRepliesResponse>(`/messages/${messageId}/replies`, {
    params: cursor ? { cursor } : undefined,
  });
  return data;
}

export async function pinMessage(messageId: string): Promise<Message> {
  const { data } = await api.post<Message>(`/messages/${messageId}/pin`);
  return data;
}

export async function unpinMessage(messageId: string): Promise<Message> {
  const { data } = await api.post<Message>(`/messages/${messageId}/unpin`);
  return data;
}
