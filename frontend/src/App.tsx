import React, { useState, useEffect, useRef } from 'react';
import { AuthScreen } from './components/AuthScreen';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import {
  SessionInfo,
  Message,
  getStoredUserToken,
  removeStoredUserToken,
  removeStoredUsername,
  getSessions,
  createSession,
  renameSession,
  deleteSession,
  clearChatHistory,
  streamChat,
  StreamEvent,
} from './services/api';

interface ChatResponseData {
  messages?: Message[];
  is_interrupted?: boolean;
  interrupt_question?: string | null;
}

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === 'AbortError';

const buildToolStatus = (event: StreamEvent): string | null | undefined => {
  if (event.event === 'tool_start') {
    const toolName = event.tool_name || '工具';
    const query =
      typeof event.tool_input === 'object' && event.tool_input !== null && 'query' in event.tool_input
        ? String((event.tool_input as { query?: unknown }).query || '')
        : '';
    return query ? `正在使用 ${toolName} 查询：${query}` : `正在使用 ${toolName} 处理监测数据...`;
  }

  if (event.event === 'tool_end') {
    return null;
  }

  return undefined;
};

export const App: React.FC = () => {
  const [userToken, setUserToken] = useState<string | null>(getStoredUserToken());
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSession, setActiveSession] = useState<SessionInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isInterrupted, setIsInterrupted] = useState(false);
  const [interruptQuestion, setInterruptQuestion] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [isNewSessionDraft, setIsNewSessionDraft] = useState(false);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const activeSessionRef = useRef<SessionInfo | null>(activeSession);
  const fetchAbortControllerRef = useRef<AbortController | null>(null);
  const streamAbortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    activeSessionRef.current = activeSession;
  }, [activeSession]);

  // Load user sessions upon successful login
  useEffect(() => {
    if (userToken) {
      loadSessions();
    }
  }, [userToken]);

  const loadSessions = async (currentActiveId?: string | null) => {
    try {
      if (!userToken) return;
      const data = await getSessions(userToken);

      const processed = data.map(s => {
        if (!s.name || s.name.trim() === "") {
          return { ...s, name: "新会话" };
        }
        return s;
      });

      // Sort in reverse chronological order (newest first)
      processed.reverse();
      setSessions(processed);

      const activeId = currentActiveId || activeSession?.session_id;
      if (activeId) {
        const updatedActive = processed.find(s => s.session_id === activeId);
        if (updatedActive) {
          setActiveSession(updatedActive);
        }
      } else if (processed.length > 0) {
        // Auto-select the first session if nothing is active
        handleSelectSession(processed[0]);
      } else {
        // No sessions exist, enter draft mode by default
        setIsNewSessionDraft(true);
      }
    } catch (err) {
      console.error('Failed to load sessions', err);
    }
  };

  const handleSelectSession = async (session: SessionInfo) => {
    fetchAbortControllerRef.current?.abort();
    streamAbortControllerRef.current?.abort();
    const controller = new AbortController();
    fetchAbortControllerRef.current = controller;

    setIsNewSessionDraft(false);
    setActiveSession(session);
    activeSessionRef.current = session;
    setMessages([]);
    setStreamingText('');
    setToolStatus(null);
    setIsInterrupted(false);
    setInterruptQuestion(null);
    setLoading(true);

    try {
      const response = await fetch(`/api/v1/chatbot/messages`, {
        headers: { 'Authorization': `Bearer ${session.token.access_token}` },
        signal: controller.signal,
      });
      if (response.ok) {
        const data = (await response.json()) as ChatResponseData;
        if (activeSessionRef.current?.session_id !== session.session_id) return;
        setMessages(data.messages || []);
        setIsInterrupted(data.is_interrupted || false);
        setInterruptQuestion(data.interrupt_question || null);
      }
    } catch (err) {
      if (isAbortError(err)) return;
      console.error('Failed to fetch messages', err);
    } finally {
      if (fetchAbortControllerRef.current === controller) {
        fetchAbortControllerRef.current = null;
      }
      if (activeSessionRef.current?.session_id === session.session_id) {
        setLoading(false);
      }
    }
  };

  const handleCreateSession = () => {
    fetchAbortControllerRef.current?.abort();
    streamAbortControllerRef.current?.abort();
    setIsNewSessionDraft(true);
    setActiveSession(null);
    activeSessionRef.current = null;
    setMessages([]);
    setStreamingText('');
    setToolStatus(null);
    setLoading(false);
    setIsInterrupted(false);
    setInterruptQuestion(null);
  };

  const handleRenameSession = async (sessionId: string, newName: string) => {
    const targetSession = sessions.find((s) => s.session_id === sessionId);
    if (!targetSession) return;

    try {
      const updated = await renameSession(targetSession.token.access_token, sessionId, newName);
      setSessions((prev) => prev.map((s) => (s.session_id === sessionId ? updated : s)));
      if (activeSession?.session_id === sessionId) {
        setActiveSession(updated);
      }
    } catch (err) {
      alert('重命名失败，请重试。');
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    const targetSession = sessions.find((s) => s.session_id === sessionId);
    if (!targetSession) return;

    try {
      await deleteSession(targetSession.token.access_token, sessionId);
      const targetIndex = sessions.findIndex((s) => s.session_id === sessionId);
      const remainingSessions = sessions.filter((s) => s.session_id !== sessionId);
      setSessions(remainingSessions);

      if (activeSession?.session_id === sessionId) {
        const nextIndex = Math.min(Math.max(targetIndex, 0), remainingSessions.length - 1);
        const nextSession = remainingSessions[nextIndex];

        if (nextSession) {
          await handleSelectSession(nextSession);
        } else {
          handleCreateSession();
        }
      }
    } catch (err) {
      alert('删除会话失败，请重试。');
    }
  };

  const handleClearHistory = async () => {
    if (!activeSession) return;
    try {
      await clearChatHistory(activeSession.token.access_token);
      setMessages([]);
      setIsInterrupted(false);
      setInterruptQuestion(null);
    } catch (err) {
      alert('清空历史记录失败，请重试。');
    }
  };

  const handleSendMessage = async (content: string) => {
    let session = activeSession;
    let updatedSessions = [...sessions];

    if (isNewSessionDraft) {
      if (!userToken) return;
      try {
        setLoading(true);
        // 1. Create the session on the backend
        const newSession = await createSession(userToken);

        // 2. Set generating title flag and empty name
        newSession.isGeneratingTitle = true;
        newSession.name = "";

        // 3. Add to sessions list and select it
        session = newSession;
        updatedSessions = [newSession, ...sessions];
        setSessions(updatedSessions);
        setActiveSession(newSession);
        activeSessionRef.current = newSession;
        setIsNewSessionDraft(false);
      } catch (err) {
        alert('初始化监测会话失败，请重试。');
        setLoading(false);
        return;
      }
    }

    if (!session) return;

    const userMessage: Message = { role: 'user', content };
    const updatedMessages = [...messages, userMessage];

    // Optimistically update message feed
    setMessages(updatedMessages);
    setLoading(true);
    setStreamingText('');
    setToolStatus(null);

    streamAbortControllerRef.current?.abort();
    const streamController = new AbortController();
    streamAbortControllerRef.current = streamController;
    const requestSession = session;

    try {
      await streamChat(
        [userMessage],
        requestSession.token.access_token,
        (chunk) => {
          if (activeSessionRef.current?.session_id !== requestSession.session_id) return;
          setStreamingText((prev) => prev + chunk);
        },
        async () => {
          if (activeSessionRef.current?.session_id !== requestSession.session_id) return;
          // Streaming finished, synchronize backend messages state
          await syncMessagesState(requestSession);
        },
        (err) => {
          if (isAbortError(err)) return;
          if (activeSessionRef.current?.session_id !== requestSession.session_id) return;
          console.error(err);
          alert('接收流式回复出错，连接可能已断开，请重试。');
          setLoading(false);
          setToolStatus(null);
        },
        {
          signal: streamController.signal,
          onEvent: (event) => {
            if (activeSessionRef.current?.session_id !== requestSession.session_id) return;
            const status = buildToolStatus(event);
            if (status !== undefined) {
              setToolStatus(status);
            }
          },
        }
      );
    } catch (err) {
      console.error(err);
      setLoading(false);
    } finally {
      if (streamAbortControllerRef.current === streamController) {
        streamAbortControllerRef.current = null;
      }
    }
  };

  const handleSubmitInterrupt = async (response: string) => {
    if (!activeSession) return;

    const userResponse: Message = { role: 'user', content: response };
    const updatedMessages = [...messages, userResponse];

    setMessages(updatedMessages);
    setIsInterrupted(false);
    setInterruptQuestion(null);
    setLoading(true);
    setStreamingText('');
    setToolStatus(null);

    streamAbortControllerRef.current?.abort();
    const streamController = new AbortController();
    streamAbortControllerRef.current = streamController;
    const requestSession = activeSession;

    try {
      await streamChat(
        [userResponse],
        requestSession.token.access_token,
        (chunk) => {
          if (activeSessionRef.current?.session_id !== requestSession.session_id) return;
          setStreamingText((prev) => prev + chunk);
        },
        async () => {
          if (activeSessionRef.current?.session_id !== requestSession.session_id) return;
          await syncMessagesState(requestSession);
        },
        (err) => {
          if (isAbortError(err)) return;
          if (activeSessionRef.current?.session_id !== requestSession.session_id) return;
          console.error(err);
          alert('发送干预回复出错，请重试。');
          setLoading(false);
          setToolStatus(null);
        },
        {
          signal: streamController.signal,
          onEvent: (event) => {
            if (activeSessionRef.current?.session_id !== requestSession.session_id) return;
            const status = buildToolStatus(event);
            if (status !== undefined) {
              setToolStatus(status);
            }
          },
        }
      );
    } catch (err) {
      console.error(err);
      setLoading(false);
    } finally {
      if (streamAbortControllerRef.current === streamController) {
        streamAbortControllerRef.current = null;
      }
    }
  };

  const syncMessagesState = async (session: SessionInfo) => {
    try {
      if (activeSessionRef.current?.session_id !== session.session_id) return;
      const response = await fetch(`/api/v1/chatbot/messages`, {
        headers: { 'Authorization': `Bearer ${session.token.access_token}` },
      });
      if (response.ok) {
        const data = (await response.json()) as ChatResponseData;
        if (activeSessionRef.current?.session_id !== session.session_id) return;
        setMessages(data.messages || []);
        // Batch stream text clearing and loading stop to prevent double AI message rendering
        setStreamingText('');
        setLoading(false);
        setToolStatus(null);
        setIsInterrupted(data.is_interrupted || false);
        setInterruptQuestion(data.interrupt_question || null);
      }

      // Fetch sessions list from backend to check if the naming task has completed
      if (!userToken) return;
      const data = await getSessions(userToken);
      if (activeSessionRef.current?.session_id !== session.session_id) return;

      const updatedSessions = data.map(s => {
        if (!s.name || s.name.trim() === "") {
          return { ...s, name: "新会话", isGeneratingTitle: false };
        }
        return { ...s, isGeneratingTitle: false };
      });

      // Maintain reverse chronological order (newest first)
      updatedSessions.reverse();
      setSessions(updatedSessions);
      const activeSec = updatedSessions.find(s => s.session_id === session.session_id);
      if (activeSec) {
        setActiveSession(activeSec);
        activeSessionRef.current = activeSec;
      }
    } catch (e) {
      console.error('Error synchronizing chat history:', e);
    } finally {
      if (activeSessionRef.current?.session_id === session.session_id) {
        setLoading(false);
        setStreamingText('');
        setToolStatus(null);
      }
    }
  };

  const handleLogout = () => {
    fetchAbortControllerRef.current?.abort();
    streamAbortControllerRef.current?.abort();
    removeStoredUserToken();
    removeStoredUsername();
    setUserToken(null);
    setSessions([]);
    setActiveSession(null);
    activeSessionRef.current = null;
    setMessages([]);
    setStreamingText('');
    setToolStatus(null);
    setLoading(false);
    setIsInterrupted(false);
    setInterruptQuestion(null);
  };

  if (!userToken) {
    return <AuthScreen onAuthSuccess={() => setUserToken(getStoredUserToken())} />;
  }

  return (
    <div className="h-screen w-screen flex bg-[#030712] overflow-hidden">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSession?.session_id || null}
        isNewSessionDraft={isNewSessionDraft}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        onLogout={handleLogout}
        isGeneratingMessage={loading}
      />
      <ChatWindow
        activeSession={activeSession}
        isNewSessionDraft={isNewSessionDraft}
        messages={messages}
        onSendMessage={handleSendMessage}
        isInterrupted={isInterrupted}
        interruptQuestion={interruptQuestion}
        onSubmitInterrupt={handleSubmitInterrupt}
        loading={loading}
        streamingText={streamingText}
        toolStatus={toolStatus}
        onClearHistory={handleClearHistory}
      />
    </div>
  );
};
