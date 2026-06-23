import React, { useState } from 'react';
import { SessionInfo, getStoredUsername } from '../services/api';
import { Mountain, Plus, MessageSquare, Trash2, Edit3, Check, X, LogOut, User } from 'lucide-react';

interface SidebarProps {
  sessions: SessionInfo[];
  activeSessionId: string | null;
  isNewSessionDraft: boolean;
  onSelectSession: (session: SessionInfo) => void;
  onCreateSession: () => void;
  onRenameSession: (sessionId: string, newName: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  isNewSessionDraft,
  onSelectSession,
  onCreateSession,
  onRenameSession,
  onDeleteSession,
  onLogout,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const username = getStoredUsername();

  const handleStartRename = (e: React.MouseEvent, session: SessionInfo) => {
    e.stopPropagation();
    setEditingId(session.session_id);
    setEditValue(session.name);
  };

  const handleSaveRename = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (editValue.trim()) {
      onRenameSession(sessionId, editValue.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <div className="w-80 h-full flex flex-col glass border-r border-slate-800/60 text-slate-200">
      {/* Header */}
      <div className="p-6 border-b border-slate-800/60 flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-blue-600 flex items-center justify-center shadow-md shadow-indigo-500/10">
          <Mountain className="w-4 h-4 text-white" />
        </div>
        <div className="font-bold text-lg tracking-tight text-white">LMA Monitor</div>
        <span className="text-xs bg-indigo-500/15 text-indigo-400 font-medium px-2 py-0.5 rounded-full border border-indigo-500/20">
          Agent v1.0
        </span>
      </div>

      {/* New Chat Button */}
      <div className="p-4 shrink-0">
        <button
          onClick={onCreateSession}
          className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-500/10 to-blue-600/10 hover:from-indigo-500/20 hover:to-blue-600/20 border border-indigo-500/30 hover:border-indigo-500/50 text-indigo-300 hover:text-white font-medium text-sm transition-all duration-200 active:scale-[0.98] flex items-center justify-center gap-2 group"
        >
          <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-200" />
          新建监测会话
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {sessions.length === 0 && !isNewSessionDraft ? (
          <div className="h-40 flex flex-col items-center justify-center text-slate-500 text-xs px-4 text-center">
            <MessageSquare className="w-8 h-8 mb-2 opacity-30" />
            暂无历史监测会话<br />点击上方新建开始监测
          </div>
        ) : (
          sessions.map((session) => {
            if (session.isGeneratingTitle) {
              return (
                <div
                  key={session.session_id}
                  className="flex items-center gap-3 px-3.5 py-3 rounded-xl border border-slate-850 bg-slate-900/20 animate-pulse mb-1"
                >
                  <MessageSquare className="w-4 h-4 shrink-0 text-indigo-500/60" />
                  <div className="h-3 bg-slate-800/60 rounded w-24"></div>
                </div>
              );
            }
            const isActive = session.session_id === activeSessionId;
            const isEditing = session.session_id === editingId;

            return (
              <div
                key={session.session_id}
                onClick={() => !isEditing && onSelectSession(session)}
                className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-sm transition-all duration-150 cursor-pointer ${
                  isActive
                    ? 'bg-indigo-500/15 border border-indigo-500/20 text-white font-medium'
                    : 'border border-transparent hover:bg-slate-800/40 hover:border-slate-800/50 text-slate-400 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <MessageSquare className={`w-4 h-4 shrink-0 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                  {isEditing ? (
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveRename(e as any, session.session_id);
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                      className="bg-slate-900 border border-slate-700 text-white rounded px-2 py-0.5 text-xs outline-none w-full"
                      autoFocus
                    />
                  ) : (
                    <span className="truncate text-slate-200">{session.name || '新监测会话'}</span>
                  )}
                </div>

                {/* Hover Action Buttons */}
                {!isEditing && (
                  <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => handleStartRename(e, session)}
                      className="p-1 rounded hover:bg-slate-700/50 text-slate-500 hover:text-slate-200 transition-colors"
                      title="重命名"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm('确认删除此监测会话吗？')) onDeleteSession(session.session_id);
                      }}
                      className="p-1 rounded hover:bg-red-950/40 text-slate-500 hover:text-red-400 transition-colors"
                      title="删除会harm"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}

                {isEditing && (
                  <div className="flex items-center gap-1 shrink-0 ml-1">
                    <button
                      onClick={(e) => handleSaveRename(e, session.session_id)}
                      className="p-1 rounded bg-green-500/10 hover:bg-green-500/20 text-green-400"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={handleCancelRename}
                      className="p-1 rounded bg-red-500/10 hover:bg-red-500/20 text-red-400"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* User Info & Logout (Bottom) */}
      <div className="p-4 border-t border-slate-800/60 bg-slate-950/20 shrink-0">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center shrink-0">
              <User className="w-4 h-4 text-slate-400" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-medium text-slate-200 truncate">{username || '监测员'}</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">监测中心用户</div>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="p-2 rounded-lg bg-slate-800/50 hover:bg-red-950/20 text-slate-400 hover:text-red-400 transition-all border border-slate-800 hover:border-red-950/30"
            title="退出登录"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
