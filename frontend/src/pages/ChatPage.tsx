/** RAG Chat page with citations, scope selector, and search mode toggle. */

import { useCallback, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import ChatInput from "../components/chat/ChatInput";
import MessageList from "../components/chat/MessageList";
import ScopeSelector from "../components/chat/ScopeSelector";
import PageHeader from "../components/ui/PageHeader";
import { useCategories } from "../hooks/useCategories";
import { useRagQuery } from "../hooks/useRagChat";
import type { ChatMessage, QueryScope, SearchMode } from "../types/rag";

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const documentId = id ?? "";
  const messageIdRef = useRef(0);

  const { data: categoriesData } = useCategories();
  const ragQuery = useRagQuery();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [scope, setScope] = useState<QueryScope>("single_document");
  const [scopeId, setScopeId] = useState<string | undefined>(documentId);
  const [searchMode, setSearchMode] = useState<SearchMode>("hybrid");

  const categories = categoriesData?.categories ?? [];

  const handleScopeChange = useCallback(
    (newScope: QueryScope) => {
      setScope(newScope);
      if (newScope === "single_document") {
        setScopeId(documentId);
      } else if (newScope === "all") {
        setScopeId(undefined);
      } else {
        setScopeId(undefined);
      }
    },
    [documentId],
  );

  const handleSubmit = useCallback(
    (query: string) => {
      const userMsgId = String(++messageIdRef.current);
      const userMessage: ChatMessage = {
        id: userMsgId,
        role: "user",
        content: query,
      };
      setMessages((prev) => [...prev, userMessage]);

      ragQuery.mutate(
        {
          query,
          scope,
          scopeId: scope === "all" ? undefined : scopeId,
          searchMode,
        },
        {
          onSuccess: (data) => {
            const aiMsgId = String(++messageIdRef.current);
            const aiMessage: ChatMessage = {
              id: aiMsgId,
              role: "assistant",
              content: data.answer,
              citations: data.citations,
            };
            setMessages((prev) => [...prev, aiMessage]);
          },
          onError: (error) => {
            const errMsgId = String(++messageIdRef.current);
            const errMessage: ChatMessage = {
              id: errMsgId,
              role: "assistant",
              content: `Error: ${error.message}`,
            };
            setMessages((prev) => [...prev, errMessage]);
          },
        },
      );
    },
    [scope, scopeId, searchMode, ragQuery],
  );

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Chat with Document" />

      <div className="flex flex-wrap items-center gap-4 px-6 py-3 border-b border-gray-200">
        <ScopeSelector
          scope={scope}
          scopeId={scopeId}
          onScopeChange={handleScopeChange}
          onScopeIdChange={setScopeId}
          documentId={documentId}
          categories={categories}
        />

        <div className="flex items-center gap-2" data-testid="search-mode-toggle">
          <label className="text-sm font-medium text-gray-700">Mode:</label>
          {(["semantic", "keyword", "hybrid"] as SearchMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setSearchMode(mode)}
              className={`px-3 py-1 text-xs rounded-full border capitalize ${
                searchMode === mode
                  ? "bg-blue-100 text-blue-800 border-blue-200"
                  : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}
              data-testid={`search-mode-${mode}`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} />
      </div>

      <ChatInput onSubmit={handleSubmit} disabled={ragQuery.isPending} />
    </div>
  );
}
