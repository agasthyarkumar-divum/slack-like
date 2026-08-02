import { api } from "@/lib/api/client";
import type { Channel, ChannelMember } from "@/lib/api/types";

export async function listMyChannels(): Promise<Channel[]> {
  const { data } = await api.get<Channel[]>("/channels");
  return data;
}

export async function getChannel(channelId: string): Promise<Channel> {
  const { data } = await api.get<Channel>(`/channels/${channelId}`);
  return data;
}

export async function createChannel(input: {
  name: string;
  type: Channel["type"];
  topic?: string;
  member_ids?: string[];
}): Promise<Channel> {
  const { data } = await api.post<Channel>("/channels", input);
  return data;
}

export async function listMembers(channelId: string): Promise<ChannelMember[]> {
  const { data } = await api.get<ChannelMember[]>(`/channels/${channelId}/members`);
  return data;
}

export async function startDM(otherUserId: string): Promise<Channel> {
  const { data } = await api.post<Channel>(`/channels/dm/${otherUserId}`);
  return data;
}
