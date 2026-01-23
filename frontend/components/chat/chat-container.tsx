'use client';
import { useChat } from '@/hooks/use-chat';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { ErrorMessage } from './error-message';
import { useChatStore } from '@/lib/store/chat-store';
import { useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api-client';
import type { ChatMessage } from '@/types';

export function ChatContainer() {
  const { sendMessage, status } = useChat();
  const connectionStatus = useChatStore((s) => s.connectionStatus);
  const sessionId = useChatStore((s) => s.sessionId);
  const messages = useChatStore((s) => s.messages);
  const setMessages = useChatStore((s) => s.setMessages);
  const hasLoadedHistory = useRef(false);

  // Load session history on mount when there's a sessionId but no messages
  useEffect(() => {
    const loadHistory = async () => {
      if (sessionId && !hasLoadedHistory.current && messages.length === 0) {
        hasLoadedHistory.current = true;
        try {
          const historyData = await apiClient.getSessionHistory(sessionId);

          // Convert history messages to ChatMessage format
          const chatMessages: ChatMessage[] = historyData.messages.map((msg: any) => ({
            id: msg.message_id || crypto.randomUUID(),
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            toolName: msg.tool_name,
            toolInput: msg.metadata?.input,
            toolUseId: msg.tool_use_id,
            isError: msg.is_error,
          }));

          if (chatMessages.length > 0) {
            setMessages(chatMessages);
          }
        } catch (error) {
          console.error('Failed to load session history:', error);
        }
      }
    };

    loadHistory();
  }, [sessionId, messages.length, setMessages]);

  if (connectionStatus === 'error') {
    return (
      <div className="flex-1 p-4">
        <ErrorMessage
          error="Connection error. Please check your internet connection and try again."
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <MessageList />
      <ChatInput onSend={sendMessage} disabled={connectionStatus !== 'connected'} />
    </div>
  );
}
