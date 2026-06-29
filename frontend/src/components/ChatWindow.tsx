import React, { useState, useRef, useEffect } from 'react';
import { SessionInfo, Message } from '../services/api';
import { ThinkingIndicator } from './ThinkingIndicator';
import { HumanPromptCard } from './HumanPromptCard';
import { MarkdownMessage } from './MarkdownMessage';
import { Send, Mountain, AlertCircle, Sparkles, Terminal, Loader2, Plus, PanelLeftOpen } from 'lucide-react';

interface ChatWindowProps {
  activeSession: SessionInfo | null;
  isNewSessionDraft: boolean;
  messages: Message[];
  onSendMessage: (content: string) => void;
  isInterrupted: boolean;
  interruptQuestion: string | null;
  onSubmitInterrupt: (response: string) => void;
  loading: boolean;
  streamingText: string;
  toolStatus: string | null;
  isSidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
}

const MAX_MESSAGE_LENGTH = 3000;

export const ChatWindow: React.FC<ChatWindowProps> = ({
  activeSession,
  isNewSessionDraft,
  messages,
  onSendMessage,
  isInterrupted,
  interruptQuestion,
  onSubmitInterrupt,
  loading,
  streamingText,
  toolStatus,
  isSidebarCollapsed = false,
  onToggleSidebar,
}) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText, loading]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && inputValue.length <= MAX_MESSAGE_LENGTH && !loading && !isInterrupted) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  // Welcome Screen
  if (!activeSession && !isNewSessionDraft) {
    return (
      <div className="flex-1 h-full flex flex-col items-center justify-center p-8 bg-white text-center relative overflow-hidden select-none">
        <div className="z-10 max-w-lg flex flex-col items-center">
          <div className="w-12 h-12 rounded-2xl bg-neutral-900 flex items-center justify-center shadow-md mb-6">
            <Mountain className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-neutral-900 tracking-tight">智能滑坡监测决策系统</h2>
          <p className="text-neutral-500 mt-2 text-sm leading-relaxed max-w-md">
            欢迎来到 Landslide Monitoring Agent。本系统集成了实时气象数据查询、地质阈值计算以及有状态推理分析。
          </p>
          <div className="mt-8 grid grid-cols-2 gap-4 w-full">
            <div className="p-4 rounded-2xl border border-neutral-200 bg-neutral-50/50 text-left">
              <div className="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center mb-2">
                <Sparkles className="w-4 h-4 text-neutral-700" />
              </div>
              <h4 className="text-neutral-800 text-xs font-bold uppercase tracking-wider">智能推理分析</h4>
              <p className="text-neutral-500 text-xs mt-1">自动识别滑坡敏感点并提供预警判定方案。</p>
            </div>
            <div className="p-4 rounded-2xl border border-neutral-200 bg-neutral-50/50 text-left">
              <div className="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center mb-2">
                <Terminal className="w-4 h-4 text-neutral-700" />
              </div>
              <h4 className="text-neutral-800 text-xs font-bold uppercase tracking-wider">实时在线搜索</h4>
              <p className="text-neutral-500 text-xs mt-1">接入实时网络搜索库获取最新降雨量与环境警报。</p>
            </div>
          </div>
          <p className="text-xs text-neutral-400 mt-10">请在左侧边栏“选择历史会话”或“新建监测会话”以启动 Agent 工作流。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full flex flex-col bg-white text-neutral-800 relative">
      {/* Top Header - empty for visual spacing and aligned border lines */}
      <div className="h-16 px-6 bg-white border-b border-neutral-200 flex items-center justify-between shrink-0 z-10">
        {isSidebarCollapsed && onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            aria-label="展开侧边栏"
            className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors shrink-0"
            title="展开侧边栏"
          >
            <PanelLeftOpen className="w-4 h-4" />
          </button>
        )}
        <div /> {/* keep alignment */}
      </div>

      {/* Messages Feed */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-6 space-y-6"
      >
        {messages.length === 0 && !streamingText && (
          <div className="h-60 flex flex-col items-center justify-center text-neutral-400 text-xs gap-2 select-none">
            <Mountain className="w-6 h-6 opacity-30 animate-bounce" />
            {isNewSessionDraft
              ? '输入首条消息开始滑坡风险监测分析（发送后将自动创建会话）'
              : '会话已就绪，在下方输入问题（例如：“最近降雨是否会导致黄土滑坡风险？”）开启分析。'}
          </div>
        )}

        {messages.map((msg, index) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={index}
              className={`flex items-start gap-4 max-w-4xl mx-auto w-full ${isUser ? 'flex-row-reverse' : ''}`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border text-xs font-bold select-none ${
                  isUser
                    ? 'bg-neutral-100 border-neutral-200 text-neutral-600'
                    : 'bg-neutral-900 border-neutral-900 text-white'
                }`}
              >
                {isUser ? 'ME' : 'AI'}
              </div>

              {/* Bubble */}
              <div
                className={`rounded-2xl ${
                  isUser
                    ? 'bg-neutral-100 text-neutral-800 px-4 py-2.5 max-w-[70%]'
                    : 'text-neutral-800 px-1 py-1 max-w-full flex-1'
                }`}
              >
                <MarkdownMessage content={msg.content} />
              </div>
            </div>
          );
        })}

        {/* Streaming Chunk bubble */}
        {streamingText && (
          <div className="flex items-start gap-4 max-w-4xl mx-auto w-full">
            <div className="w-8 h-8 rounded-lg bg-neutral-900 border border-neutral-900 text-white flex items-center justify-center shrink-0 text-xs font-bold select-none">
              AI
            </div>
            <div className="max-w-full flex-1 text-neutral-800 px-1 py-1">
              <div className="mb-2.5 flex items-center gap-1.5 text-[11px] font-medium text-neutral-500 select-none">
                <Loader2 className="w-3 h-3 animate-spin text-neutral-600" />
                <span>{toolStatus || '正在生成回复...'}</span>
              </div>
              <MarkdownMessage content={streamingText} />
            </div>
          </div>
        )}

        {/* Loading status (Thinking) */}
        {loading && !streamingText && (
          <div className="max-w-4xl mx-auto w-full">
            <ThinkingIndicator statusText={toolStatus || undefined} />
          </div>
        )}

        {/* Human Interrupt Card */}
        {isInterrupted && interruptQuestion && (
          <div className="max-w-4xl mx-auto w-full">
            <HumanPromptCard
              question={interruptQuestion}
              onSubmit={onSubmitInterrupt}
              loading={loading}
            />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Panel */}
      <div className="p-4 bg-white shrink-0 z-10">
        <form onSubmit={handleSend} className="max-w-4xl mx-auto flex items-center gap-2 relative bg-white border border-neutral-200 rounded-2xl p-1.5 shadow-[0_0_15px_rgba(0,0,0,0.05),0_2px_5px_rgba(0,0,0,0.03)] focus-within:border-neutral-300 transition-colors">
          {isInterrupted && (
            <div className="absolute inset-0 bg-white/90 rounded-2xl z-20 backdrop-blur-[1px] flex items-center justify-center gap-2 border border-amber-500/20">
              <AlertCircle className="w-4 h-4 text-amber-500" />
              <span className="text-xs text-amber-600 font-medium">系统当前挂起，请在上方中断卡片中回复 Agent 继续监测</span>
            </div>
          )}

          {/* Plus button for future extensions */}
          <button
            type="button"
            className="w-8 h-8 rounded-full bg-neutral-100 hover:bg-neutral-200 flex items-center justify-center text-neutral-500 hover:text-neutral-700 transition-colors shrink-0"
            title="添加附件或扩展功能"
          >
            <Plus className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={loading || isInterrupted}
            maxLength={MAX_MESSAGE_LENGTH}
            placeholder={
              isInterrupted
                ? '等待上方人工干预指令...'
                : '询问滑坡监测数据、气象降雨风险或计算判定方案...'
            }
            className="flex-1 bg-transparent text-neutral-800 placeholder:text-neutral-400 text-sm outline-none px-2 py-1.5 disabled:opacity-50"
          />

          <span
            className={`absolute -top-5 right-12 text-[10px] ${
              inputValue.length >= 2800 ? 'text-red-500' : 'text-neutral-400'
            }`}
          >
            {inputValue.length}/{MAX_MESSAGE_LENGTH}
          </span>

          <button
            type="submit"
            disabled={!inputValue.trim() || loading || isInterrupted}
            aria-label="发送消息"
            className="p-3 rounded-xl bg-gradient-to-r from-indigo-500 to-blue-600 hover:brightness-110 text-white transition-all disabled:opacity-30 disabled:scale-100 active:scale-95 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/10"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
