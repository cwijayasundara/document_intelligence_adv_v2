/** Renders the chat message history with user and AI messages. */

import type { ChatMessage } from "../../types/rag";
import CitationCard from "./CitationCard";

interface MessageListProps {
  messages: ChatMessage[];
}

export default function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <p>Ask a question about your documents to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4" data-testid="message-list">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          data-testid={`message-${msg.id}`}
        >
          <div
            className={`max-w-2xl rounded-lg px-4 py-3 ${
              msg.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-900"
            }`}
          >
            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

            {msg.citations && msg.citations.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-xs font-medium text-gray-500">Citations:</p>
                {msg.citations.map((citation, idx) => (
                  <CitationCard
                    key={`${msg.id}-citation-${idx}`}
                    citation={citation}
                    index={idx}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
