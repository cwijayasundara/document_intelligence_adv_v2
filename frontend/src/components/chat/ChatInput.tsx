/** Chat input field with submit button. */

import { useCallback, useState } from "react";

interface ChatInputProps {
  onSubmit: (query: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSubmit, disabled = false }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = input.trim();
      if (trimmed) {
        onSubmit(trimmed);
        setInput("");
      }
    },
    [input, onSubmit],
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 p-4 border-t border-gray-200"
      data-testid="chat-input-form"
    >
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask a question about your documents..."
        disabled={disabled}
        className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
        data-testid="chat-input"
      />
      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid="chat-submit"
      >
        Send
      </button>
    </form>
  );
}
