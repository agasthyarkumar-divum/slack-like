import { api } from "@/lib/api/client";
import type { SearchResponse, SearchType } from "@/lib/api/types";

export async function search(query: string, type: SearchType): Promise<SearchResponse> {
  const { data } = await api.get<SearchResponse>("/search", { params: { q: query, type } });
  return data;
}
