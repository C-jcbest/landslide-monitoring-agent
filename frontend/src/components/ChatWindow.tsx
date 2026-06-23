import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { SessionInfo, Message } from '../services/api';
import { ThinkingIndicator } from './ThinkingIndicator';
import { HumanPromptCard } from './HumanPromptCard';
import { Send, Trash2, Mountain, AlertCircle, Sparkles, Terminal } from 'lucide-react';

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
  onClearHistory: () => void;
}

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
  onClearHistory,
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
    if (inputValue.trim() && !loading && !isInterrupted) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  if (!activeSession && !isNewSessionDraft) {
    return (
      <div className="flex-1 h-full flex flex-col items-center justify-center p-8 bg-[#090d16] text-center relative overflow-hidden">
        {/* Glow Effects */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none"></div>

        <div className="z-10 max-w-lg flex flex-col items-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 mb-6 animate-pulse-slow">
            <Mountain className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">智能滑坡监测决策系统</h2>
          <p className="text-slate-400 mt-3 text-sm leading-relaxed">
            欢迎来到 Landslide Monitoring Agent。本系统集成了实时气象数据查询、地质阈值计算以及有状态推理分析。
          </p>
          <div className="mt-8 grid grid-cols-2 gap-4 w-full">
            <div className="p-4 rounded-xl glass-card text-left">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center mb-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
              </div>
              <h4 className="text-slate-200 text-xs font-bold uppercase tracking-wider">智能推理分析</h4>
              <p className="text-slate-400 text-xs mt-1">自动识别滑坡敏感点并提供预警判定方案。</p>
            </div>
            <div className="p-4 rounded-xl glass-card text-left">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center mb-2">
                <Terminal className="w-4 h-4 text-blue-400" />
              </div>
              <h4 className="text-slate-200 text-xs font-bold uppercase tracking-wider">实时在线搜索</h4>
              <p className="text-slate-400 text-xs mt-1">接入实时网络搜索库获取最新降雨量 and 环境警报。</p>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-10">请在左侧边栏“选择历史会话”或“新建监测会话”以启动 Agent 工作流。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full flex flex-col bg-[#090d16] text-slate-100 relative">
      {/* Top Header */}
      <div className="h-16 px-6 glass border-b border-slate-800/60 flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse"></div>
          {activeSession ? (
            <div>
              <h3 className="text-sm font-semibold text-white">{activeSession.name || '新监测会话'}</h3>
              <span className="text-[10px] text-slate-400 tracking-wide">监测会话 ID: {activeSession.session_id.slice(0, 8)}...</span>
            </div>
          ) : (
            <div>
              <h3 className="text-sm font-semibold text-white">新建监测会话</h3>
              <span className="text-[10px] text-slate-400 tracking-wide">草稿会话（发送首条消息后保存）</span>
            </div>
          )}
        </div>

        {activeSession && (
          <button
            onClick={() => {
              if (confirm('确认清空当前监测会话的对话历史吗？')) onClearHistory();
            }}
            className="py-1.5 px-3 rounded-lg bg-slate-800/40 hover:bg-red-950/20 text-slate-400 hover:text-red-400 border border-slate-800 hover:border-red-950/30 text-xs font-medium transition-all flex items-center gap-1.5"
            title="清空历史"
          >
            <Trash2 className="w-3.5 h-3.5" />
            清空监测历史
          </button>
        )}
      </div>

      {/* Messages Feed */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-6 space-y-6"
      >
        {messages.length === 0 && !streamingText && (
          <div className="h-60 flex flex-col items-center justify-center text-slate-500 text-xs gap-2">
            <Mountain className="w-8 h-8 opacity-20 animate-bounce" />
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
              className={`flex items-start gap-4 ${isUser ? 'flex-row-reverse' : ''}`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border text-xs font-bold ${
                  isUser
                    ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
                    : 'bg-blue-600/10 border-blue-600/20 text-blue-400'
                }`}
              >
                {isUser ? 'ME' : 'AI'}
              </div>

              {/* Bubble */}
              <div
                className={`max-w-[75%] rounded-2xl px-5 py-3.5 shadow-md ${
                  isUser
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'glass-card text-slate-100 rounded-tl-none border border-slate-800/50'
                }`}
              >
                <div className="prose text-sm break-words overflow-hidden leading-relaxed">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            </div>
          );
        })}

        {/* Streaming Chunk bubble */}
        {streamingText && (
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-lg bg-blue-600/10 border border-blue-600/20 text-blue-400 flex items-center justify-center shrink-0 text-xs font-bold">
              AI
            </div>
            <div className="max-w-[75%] rounded-2xl rounded-tl-none px-5 py-3.5 glass-card border border-slate-800/50 shadow-md">
              <div className="prose text-sm break-words overflow-hidden leading-relaxed">
                <ReactMarkdown>{streamingText}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {/* Loading status (Thinking) */}
        {loading && !streamingText && <ThinkingIndicator />}

        {/* Human Interrupt Card */}
        {isInterrupted && interruptQuestion && (
          <HumanPromptCard
            question={interruptQuestion}
            onSubmit={onSubmitInterrupt}
            loading={loading}
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Panel */}
      <div className="p-4 glass border-t border-slate-800/60 shrink-0 z-10">
        <form onSubmit={handleSend} className="max-w-4xl mx-auto flex items-center gap-3 relative">
          {isInterrupted && (
            <div className="absolute inset-0 bg-[#090d16]/80 rounded-xl z-20 backdrop-blur-[1px] flex items-center justify-center gap-2 border border-amber-500/20">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <span className="text-xs text-amber-300 font-medium">系统当前挂起，请在上方中断卡片中回复 Agent 继续监测</span>
            </div>
          )}

          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={loading || isInterrupted}
            placeholder={
              isInterrupted
                ? '等待上方人工干预指令...'
                : '询问滑坡监测数据、气象降雨风险或计算判定方案...'
            }
            className="flex-1 px-4 py-3 rounded-xl glass-input text-slate-100 placeholder:text-slate-500 text-sm outline-none transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || loading || isInterrupted}
            className="p-3 rounded-xl bg-gradient-to-r from-indigo-500 to-blue-600 hover:brightness-110 text-white transition-all disabled:opacity-30 disabled:scale-100 active:scale-95 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/10"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
