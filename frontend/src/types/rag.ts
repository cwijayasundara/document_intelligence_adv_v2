/** Types for RAG chat and query operations. */

export type SearchMode = "semantic" | "keyword" | "hybrid";
export type QueryScope = "single_document" | "all" | "by_category";

export interface Citation {
  chunkText: string;
  documentName: string;
  documentId: string;
  chunkIndex: number;
  relevanceScore: number;
  section: string;
}

export interface RagQueryRequest {
  query: string;
  scope: QueryScope;
  scopeId?: string;
  searchMode: SearchMode;
  topK?: number;
  sessionId?: string;
}

export interface RagQueryResponse {
  answer: string;
  citations: Citation[];
  searchMode: SearchMode;
  chunksRetrieved: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}
