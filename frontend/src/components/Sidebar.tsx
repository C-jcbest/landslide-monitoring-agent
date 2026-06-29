import React, { useState, useEffect, useRef } from 'react';
import { SessionInfo, getStoredUsername } from '../services/api';
import { Mountain, Plus, MessageSquare, Trash2, Edit3, Check, X, LogOut, User, Settings, FileText, CreditCard, PanelLeftClose, Key } from 'lucide-react';

interface SidebarProps {
  sessions: SessionInfo[];
  activeSessionId: string | null;
  isNewSessionDraft: boolean;
  onSelectSession: (session: SessionInfo) => void;
  onCreateSession: () => void;
  onRenameSession: (sessionId: string, newName: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onLogout: () => void;
  isGeneratingMessage?: boolean;
  onOpenSettings: () => void;
  onOpenReports: () => void;
  onOpenSubscription: () => void;
  onOpenBeidouCredentials: () => void;
  onToggleSidebar: () => void;
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
  isGeneratingMessage = false,
  onOpenSettings,
  onOpenReports,
  onOpenSubscription,
  onOpenBeidouCredentials,
  onToggleSidebar,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const username = getStoredUsername();

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

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

  const handleSessionKeyDown = (e: React.KeyboardEvent, session: SessionInfo, isEditing: boolean) => {
    if (isEditing) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelectSession(session);
    }
  };

  const handleDeleteClick = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    onDeleteSession(sessionId);
  };

  return (
    <div className="w-64 h-full flex flex-col bg-[#f9f9f9] border-r border-neutral-200 text-neutral-700 select-none shrink-0">
      {/* Header */}
      <div className="h-16 px-4 border-b border-neutral-200 flex items-center justify-between shrink-0 bg-white">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-neutral-900 flex items-center justify-center shadow-sm shrink-0">
            <Mountain className="w-4 h-4 text-white" />
          </div>
          <div className="font-bold text-sm tracking-tight text-neutral-900 truncate">LMA Monitor</div>
        </div>
        <button
          onClick={onToggleSidebar}
          aria-label="折叠侧边栏"
          className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors shrink-0"
          title="折叠侧边栏"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-4 shrink-0">
        <button
          onClick={onCreateSession}
          aria-label="新建监测会话"
          className="w-full py-2.5 px-4 rounded-xl bg-white hover:bg-neutral-50 border border-neutral-200 text-neutral-700 font-medium text-sm transition-all duration-200 active:scale-[0.98] flex items-center justify-center gap-2 group shadow-sm"
        >
          <Plus className="w-4 h-4 text-neutral-500 group-hover:rotate-90 transition-transform duration-200" />
          新建监测会话
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1" role="listbox" aria-label="历史监测会话">
        {sessions.length === 0 && !isNewSessionDraft ? (
          <div className="h-40 flex flex-col items-center justify-center text-neutral-400 text-xs px-4 text-center">
            <MessageSquare className="w-8 h-8 mb-2 opacity-30 text-neutral-500" />
            暂无历史监测会话<br />点击上方新建开始监测
          </div>
        ) : (
          sessions.map((session) => {
            if (session.isGeneratingTitle) {
              return (
                <div
                  key={session.session_id}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-neutral-200 bg-neutral-100 animate-pulse h-11 mb-1"
                >
                  <MessageSquare className="w-4 h-4 shrink-0 text-neutral-400" />
                  <div className="h-3 bg-neutral-200 rounded w-24"></div>
                </div>
              );
            }
            const isActive = session.session_id === activeSessionId;
            const isEditing = session.session_id === editingId;
            const actionsDisabled = isGeneratingMessage;

            return (
              <div
                key={session.session_id}
                onClick={() => !isEditing && onSelectSession(session)}
                onKeyDown={(e) => handleSessionKeyDown(e, session, isEditing)}
                role="option"
                aria-selected={isActive}
                tabIndex={isEditing ? -1 : 0}
                className={`group flex items-center justify-between px-3 py-2 rounded-xl text-sm transition-colors duration-150 cursor-pointer h-11 border ${
                  isActive
                    ? 'bg-neutral-200/60 border-neutral-200 text-neutral-900 font-medium'
                    : 'border-transparent hover:bg-neutral-100/70 text-neutral-600 hover:text-neutral-900'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1 h-full">
                  <MessageSquare className={`w-4 h-4 shrink-0 ${isActive ? 'text-neutral-800' : 'text-neutral-400'}`} />
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
                      className="bg-white border border-neutral-300 text-neutral-900 rounded px-2 py-0.5 text-xs outline-none w-full shadow-sm"
                      autoFocus
                    />
                  ) : (
                    <span className="truncate text-neutral-800 font-normal">{session.name || '新会话'}</span>
                  )}
                </div>

                {/* Hover Action Buttons */}
                {!isEditing && !actionsDisabled && (
                  <div className="flex items-center gap-1.5 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto transition-opacity shrink-0 ml-2">
                    <button
                      onClick={(e) => handleStartRename(e, session)}
                      aria-label={`重命名会话 ${session.name || '新会话'}`}
                      className="p-1 rounded hover:bg-neutral-200 text-neutral-500 hover:text-neutral-800 transition-colors"
                      title="重命名"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => handleDeleteClick(e, session.session_id)}
                      aria-label={`删除会话 ${session.name || '新会话'}`}
                      className="p-1 rounded hover:bg-red-50 text-neutral-500 hover:text-red-600 transition-colors"
                      title="删除会话"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}

                {isEditing && (
                  <div className="flex items-center gap-1 shrink-0 ml-1">
                    <button
                      onClick={(e) => handleSaveRename(e, session.session_id)}
                      aria-label="保存会话名称"
                      className="p-1 rounded bg-neutral-200 hover:bg-neutral-350 text-neutral-800"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={handleCancelRename}
                      aria-label="取消重命名"
                      className="p-1 rounded bg-neutral-200 hover:bg-neutral-350 text-neutral-800"
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

      {/* User Info & Dropdown Trigger (Bottom) */}
      <div className="p-4 border-t border-neutral-200 bg-white shrink-0 relative" ref={dropdownRef}>
        {/* Dropdown Menu */}
        {showDropdown && (
          <div className="absolute bottom-[calc(100%-8px)] left-4 right-4 bg-white border border-neutral-200 rounded-2xl shadow-xl py-2 z-30 flex flex-col animate-in slide-in-from-bottom-2 duration-150">
            <button
              onClick={() => {
                setShowDropdown(false);
                onOpenSettings();
              }}
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors text-left w-full"
            >
              <Settings className="w-4 h-4 text-neutral-400" />
              <span>设置</span>
            </button>
            <button
              onClick={() => {
                setShowDropdown(false);
                onOpenBeidouCredentials();
              }}
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors text-left w-full"
            >
              <Key className="w-4 h-4 text-neutral-400" />
              <span>北斗凭证</span>
            </button>
            <button
              onClick={() => {
                setShowDropdown(false);
                onOpenReports();
              }}
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors text-left w-full"
            >
              <FileText className="w-4 h-4 text-neutral-400" />
              <span>报表记录</span>
            </button>
            <button
              onClick={() => {
                setShowDropdown(false);
                onOpenSubscription();
              }}
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors text-left w-full"
            >
              <CreditCard className="w-4 h-4 text-neutral-400" />
              <span>订阅历史</span>
            </button>
            <div className="h-px bg-neutral-100 my-1"></div>
            <button
              onClick={() => {
                setShowDropdown(false);
                onLogout();
              }}
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors text-left w-full"
            >
              <LogOut className="w-4 h-4 text-red-500" />
              <span>退出登录</span>
            </button>
          </div>
        )}

        {/* User Card Trigger */}
        <div
          onClick={() => setShowDropdown(!showDropdown)}
          className="flex items-center gap-2.5 min-w-0 p-2 rounded-xl hover:bg-neutral-100 transition-colors cursor-pointer"
        >
          <div className="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0 border border-neutral-200">
            <User className="w-4 h-4 text-neutral-600" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-neutral-800 truncate">{username || '监测员'}</div>
            <div className="text-[10px] text-neutral-400 uppercase tracking-wider">监测中心用户</div>
          </div>
        </div>
      </div>
    </div>
  );
};
