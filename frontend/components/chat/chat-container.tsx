'use client';
import { useChat } from '@/hooks/use-chat';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { ErrorMessage } from './error-message';
import { QuestionModal } from './question-modal';
import { PlanApprovalModal } from './plan-approval-modal';
import { useChatStore } from '@/lib/store/chat-store';
import { useEffect, useRef, useCallback } from 'react';
import { apiClient } from '@/lib/api-client';
import { Loader2 } from 'lucide-react';
import { convertHistoryToChatMessages } from '@/lib/history-utils';

export function ChatContainer() {
  const { sendMessage, sendAnswer, sendPlanApproval, status } = useChat();
  const connectionStatus = useChatStore((s) => s.connectionStatus);
  const sessionId = useChatStore((s) => s.sessionId);
  const messages = useChatStore((s) => s.messages);
  const setMessages = useChatStore((s) => s.setMessages);
  const hasLoadedHistory = useRef(false);

  // Handler for question modal answer submission
  const handleQuestionAnswer = useCallback((questionId: string, answers: Record<string, string | string[]>) => {
    sendAnswer(questionId, answers);
  }, [sendAnswer]);

  // Handler for plan approval modal submission
  const handlePlanApproval = useCallback((planId: string, approved: boolean, feedback?: string) => {
    sendPlanApproval(planId, approved, feedback);
  }, [sendPlanApproval]);

  // Load session history on mount when there's a sessionId but no messages
  useEffect(() => {
    const loadHistory = async () => {
      if (sessionId && !hasLoadedHistory.current && messages.length === 0) {
        hasLoadedHistory.current = true;
        try {
          const historyData = await apiClient.getSessionHistory(sessionId);
          const chatMessages = convertHistoryToChatMessages(historyData.messages);

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

  // Show loading state when connecting or disconnected
  if (connectionStatus === 'connecting' || connectionStatus === 'disconnected') {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">
          {connectionStatus === 'connecting' ? 'Connecting to server...' : 'Waiting for connection...'}
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      <div className="shrink-0">
        <ChatInput onSend={sendMessage} disabled={connectionStatus !== 'connected'} />
      </div>
      <QuestionModal onSubmit={handleQuestionAnswer} />
      <PlanApprovalModal onSubmit={handlePlanApproval} />
    </div>
  );
}
