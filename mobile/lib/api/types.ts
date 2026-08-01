export type User = {
  id: string;
  email: string;
  display_name: string;
  avatar_uri: string | null;
  status: string | null;
  department_id: string | null;
  team_id: string | null;
  role_id: string | null;
  created_at: string | null;
};

export type Channel = {
  id: string;
  name: string;
  type: "public" | "private" | "dm" | "group";
  topic: string | null;
  created_by: string | null;
  created_at: string | null;
};

export type ChannelMember = {
  user_id: string;
  role: string | null;
  muted: boolean | null;
  joined_at: string | null;
};

export type Message = {
  id: string;
  channel_id: string | null;
  sender_id: string | null;
  content: string | null;
  reply_to_id: string | null;
  forwarded_from_id: string | null;
  is_pinned: boolean | null;
  is_edited: boolean | null;
  is_deleted: boolean | null;
  created_at: string | null;
  edited_at: string | null;
  attachment_ids: string[];
};

export type MessageListResponse = {
  items: Message[];
  next_cursor: string | null;
};

export type Attachment = {
  id: string;
  message_id: string | null;
  file_name: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  is_encrypted: boolean | null;
  is_compressed: boolean | null;
  checksum: string | null;
  created_at: string | null;
  status: "processing" | "ready";
  has_thumbnail: boolean;
};

export type Notification = {
  id: string;
  type: "mention" | "dm" | "reaction";
  payload: Record<string, unknown>;
  is_read: boolean | null;
  created_at: string | null;
};

export type NotificationListResponse = {
  items: Notification[];
  unread_count: number;
};

export type SearchType = "messages" | "users" | "channels" | "files";

export type SearchResponse = {
  type: SearchType;
  query: string;
  messages: Message[] | null;
  users: User[] | null;
  channels: Channel[] | null;
  files: Attachment[] | null;
};
