import React, { useState, useEffect } from 'react';
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
} from './services/api';

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
          return { ...s, name: "新监测会话" };
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
    setIsNewSessionDraft(false);
    setActiveSession(session);
    setMessages([]);
    setStreamingText('');
    setIsInterrupted(false);
    setInterruptQuestion(null);
    setLoading(true);

    try {
      const response = await fetch(`/api/v1/chatbot/messages`, {
        headers: { 'Authorization': `Bearer ${session.token.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
        setIsInterrupted(data.is_interrupted || false);
        setInterruptQuestion(data.interrupt_question || null);
      }
    } catch (err) {
      console.error('Failed to fetch messages', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = () => {
    setIsNewSessionDraft(true);
    setActiveSession(null);
    setMessages([]);
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
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));

      if (activeSession?.session_id === sessionId) {
        setActiveSession(null);
        setMessages([]);
        setIsInterrupted(false);
        setInterruptQuestion(null);
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

    try {
      await streamChat(
        updatedMessages,
        session.token.access_token,
        (chunk) => {
          setStreamingText((prev) => prev + chunk);
        },
        async () => {
          // Streaming finished, synchronize backend messages state
          await syncMessagesState(session);
        },
        (err) => {
          console.error(err);
          alert('接收流式回复出错，连接可能已断开，请重试。');
          setLoading(false);
        }
      );
    } catch (err) {
      console.error(err);
      setLoading(false);
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

    try {
      await streamChat(
        updatedMessages,
        activeSession.token.access_token,
        (chunk) => {
          setStreamingText((prev) => prev + chunk);
        },
        async () => {
          await syncMessagesState(activeSession);
        },
        (err) => {
          console.error(err);
          alert('发送干预回复出错，请重试。');
          setLoading(false);
        }
      );
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const syncMessagesState = async (session: SessionInfo) => {
    try {
      let firstUserMsg = "";
      const response = await fetch(`/api/v1/chatbot/messages`, {
        headers: { 'Authorization': `Bearer ${session.token.access_token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
        // Batch stream text clearing and loading stop to prevent double AI message rendering
        setStreamingText('');
        setLoading(false);
        setIsInterrupted(data.is_interrupted || false);
        setInterruptQuestion(data.interrupt_question || null);
        
        firstUserMsg = data.messages.find((m: any) => m.role === 'user')?.content || "";
      }

      // Fetch sessions list from backend to check if the naming task has completed
      if (!userToken) return;
      const data = await getSessions(userToken);
      
      const updatedSessions = data.map(s => {
        // Clear isGeneratingTitle flag on the updated session list
        if (s.session_id === session.session_id) {
          // If the backend has not set a name (remains empty due to error/timeout),
          // fallback to extracting the first user message content sliced to 15 characters.
          if (!s.name || s.name.trim() === "") {
            const fallbackName = firstUserMsg 
              ? (firstUserMsg.slice(0, 15) + (firstUserMsg.length > 15 ? '...' : ''))
              : '新监测会话';
            return { ...s, name: fallbackName, isGeneratingTitle: false };
          }
        }
        return { ...s, isGeneratingTitle: false };
      });

      // Maintain reverse chronological order (newest first)
      updatedSessions.reverse();
      setSessions(updatedSessions);
      const activeSec = updatedSessions.find(s => s.session_id === session.session_id);
      if (activeSec) {
        setActiveSession(activeSec);
      }
    } catch (e) {
      console.error('Error synchronizing chat history:', e);
    } finally {
      setLoading(false);
      setStreamingText('');
    }
  };

  const handleLogout = () => {
    removeStoredUserToken();
    removeStoredUsername();
    setUserToken(null);
    setSessions([]);
    setActiveSession(null);
    setMessages([]);
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
        onClearHistory={handleClearHistory}
      />
    </div>
  );
};
