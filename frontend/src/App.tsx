import React, { useState, useEffect, useRef } from 'react';
import { AuthScreen } from './components/AuthScreen';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { Modal } from './components/Modal';
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
  const [modalType, setModalType] = useState<'settings' | 'reports' | 'subscription' | 'logout_confirm' | 'delete_confirm' | null>(null);
  const [sessionToDelete, setSessionToDelete] = useState<SessionInfo | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
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

  const handleDeleteSessionConfirm = (session: SessionInfo) => {
    setSessionToDelete(session);
    setModalType('delete_confirm');
  };

  const handleExecuteDelete = async () => {
    if (!sessionToDelete) return;
    const sessionId = sessionToDelete.session_id;
    setModalType(null);
    setSessionToDelete(null);

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

  const handleLogoutClick = () => {
    setModalType('logout_confirm');
  };

  const handleExecuteLogout = () => {
    setModalType(null);
    handleLogout();
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
    <div className="h-screen w-screen flex bg-white overflow-hidden">
      {!isSidebarCollapsed && (
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSession?.session_id || null}
          isNewSessionDraft={isNewSessionDraft}
          onSelectSession={handleSelectSession}
          onCreateSession={handleCreateSession}
          onRenameSession={handleRenameSession}
          onDeleteSession={(sessionId) => {
            const session = sessions.find(s => s.session_id === sessionId);
            if (session) handleDeleteSessionConfirm(session);
          }}
          onLogout={handleLogoutClick}
          isGeneratingMessage={loading}
          onOpenSettings={() => setModalType('settings')}
          onOpenReports={() => setModalType('reports')}
          onOpenSubscription={() => setModalType('subscription')}
          onToggleSidebar={() => setIsSidebarCollapsed(true)}
        />
      )}
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
        isSidebarCollapsed={isSidebarCollapsed}
        onToggleSidebar={() => setIsSidebarCollapsed(false)}
      />

      {/* Settings Modal */}
      <Modal
        isOpen={modalType === 'settings'}
        title="系统设置"
        onClose={() => setModalType(null)}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2.5 border-b border-neutral-100">
            <span className="font-medium text-neutral-800">界面主题</span>
            <span className="text-xs text-neutral-500 bg-neutral-100 px-2 py-1 rounded">简约浅色模式 (ChatGPT 风格)</span>
          </div>
          <div className="flex items-center justify-between py-2.5 border-b border-neutral-100">
            <span className="font-medium text-neutral-800">系统语言</span>
            <select className="text-xs border border-neutral-200 rounded p-1 bg-white outline-none">
              <option>简体中文</option>
              <option>English</option>
            </select>
          </div>
          <div className="flex items-center justify-between py-2.5 border-b border-neutral-100">
            <span className="font-medium text-neutral-800">自动重试机制</span>
            <span className="text-xs text-neutral-400">已启用 (指数退避)</span>
          </div>
          <div className="pt-2 text-[10px] text-neutral-400 leading-normal">
            Landslide Monitoring Agent v1.0.0. 集成实时气象分析、阈值决策与有状态图逻辑。
          </div>
        </div>
      </Modal>

      {/* Reports Modal */}
      <Modal
        isOpen={modalType === 'reports'}
        title="监测报表与警报历史"
        onClose={() => setModalType(null)}
      >
        <div className="space-y-3">
          <p className="text-xs text-neutral-500 mb-2">以下为最近 7 天内触发的地质灾害监测预警简报数据：</p>
          <div className="overflow-x-auto border border-neutral-200 rounded-xl">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-neutral-50 border-b border-neutral-200">
                  <th className="p-2.5 font-semibold text-neutral-700">预警点</th>
                  <th className="p-2.5 font-semibold text-neutral-700">累计降雨</th>
                  <th className="p-2.5 font-semibold text-neutral-700">危险等级</th>
                  <th className="p-2.5 font-semibold text-neutral-700">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-neutral-100 hover:bg-neutral-50/50">
                  <td className="p-2.5">陇东黄土塬-A区</td>
                  <td className="p-2.5">52.4 mm</td>
                  <td className="p-2.5"><span className="text-amber-600 font-medium">中度风险</span></td>
                  <td className="p-2.5"><span className="text-green-600">已确认</span></td>
                </tr>
                <tr className="border-b border-neutral-100 hover:bg-neutral-50/50">
                  <td className="p-2.5">秦岭北麓泥石流点</td>
                  <td className="p-2.5">12.8 mm</td>
                  <td className="p-2.5"><span className="text-neutral-500">安全</span></td>
                  <td className="p-2.5"><span className="text-neutral-400">正常监测</span></td>
                </tr>
                <tr className="hover:bg-neutral-50/50">
                  <td className="p-2.5">甘肃南部滑坡体-C3</td>
                  <td className="p-2.5">85.0 mm</td>
                  <td className="p-2.5"><span className="text-red-600 font-bold">高度风险</span></td>
                  <td className="p-2.5"><span className="text-amber-500">紧急处置</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </Modal>

      {/* Subscription Modal */}
      <Modal
        isOpen={modalType === 'subscription'}
        title="账户与订阅计划"
        onClose={() => setModalType(null)}
      >
        <div className="space-y-4">
          <div className="p-4 bg-neutral-50 rounded-2xl border border-neutral-200">
            <h4 className="font-bold text-neutral-800 text-sm">专业监测版 (Enterprise Plan)</h4>
            <p className="text-xs text-neutral-500 mt-1">永久授权 · 允许无限次滑坡监测计算与 API 接入</p>
            <div className="mt-2.5 text-xs inline-flex items-center gap-1 bg-green-50 text-green-700 px-2 py-0.5 rounded border border-green-200/50 font-medium">
              当前状态: 正常运行中
            </div>
          </div>
          <div className="space-y-2">
            <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">专属尊享权益</span>
            <ul className="text-xs text-neutral-600 space-y-1.5 list-disc pl-4 leading-relaxed">
              <li>毫秒级 LLM 流式推理与大模型多模态支持</li>
              <li>每分钟最高支持 200 次监测限流限额</li>
              <li>长期地质记忆库存储，实现个性化定制判定</li>
              <li>7x24 小时地质灾害预警自动网络搜索支持</li>
            </ul>
          </div>
        </div>
      </Modal>

      {/* Delete Session Confirmation Modal */}
      <Modal
        isOpen={modalType === 'delete_confirm'}
        title="确认删除监测会话"
        onClose={() => {
          setModalType(null);
          setSessionToDelete(null);
        }}
        onConfirm={handleExecuteDelete}
        confirmText="确认删除"
        cancelText="取消"
      >
        <p className="text-sm text-neutral-600">
          您确认要删除会话 <strong className="text-neutral-800">“{sessionToDelete?.name || '新会话'}”</strong> 吗？删除后其全部聊天历史与监测记录将无法恢复。
        </p>
      </Modal>

      {/* Logout Confirmation Modal */}
      <Modal
        isOpen={modalType === 'logout_confirm'}
        title="确认退出登录"
        onClose={() => setModalType(null)}
        onConfirm={handleExecuteLogout}
        confirmText="确认退出"
        cancelText="取消"
      >
        <p className="text-sm text-neutral-600">
          您确定要退出当前地质监测账户，并回到登录认证界面吗？
        </p>
      </Modal>
    </div>
  );
};
