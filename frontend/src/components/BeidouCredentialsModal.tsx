import React, { useState, useEffect } from 'react';
import { Modal } from './Modal';
import {
  getBeidouCredentialStatus,
  bindBeidouCredential,
  unbindBeidouCredential,
  BeidouCredentialStatusResponse,
} from '../services/api';
import { Key, User, Lock, CheckCircle2, AlertTriangle, Loader2, Calendar, RefreshCw, Trash2, ShieldAlert } from 'lucide-react';

interface BeidouCredentialsModalProps {
  isOpen: boolean;
  onClose: () => void;
  userToken: string;
}

export const BeidouCredentialsModal: React.FC<BeidouCredentialsModalProps> = ({
  isOpen,
  onClose,
  userToken,
}) => {
  const [status, setStatus] = useState<'loading' | 'unbound' | 'bound' | 'edit'>('loading');
  const [beidouStatus, setBeidouStatus] = useState<BeidouCredentialStatusResponse | null>(null);

  // Form fields
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Interaction states
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState(false);
  const [showUnbindConfirm, setShowUnbindConfirm] = useState(false);

  // Format datetime helper
  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '--';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return isoString;
    }
  };

  const loadStatus = async () => {
    setStatus('loading');
    setError(null);
    try {
      const data = await getBeidouCredentialStatus(userToken);
      setBeidouStatus(data);
      if (data.bound) {
        setStatus('bound');
        setUsername(data.username || '');
      } else {
        setStatus('unbound');
        setUsername('');
      }
      setPassword('');
    } catch (err: any) {
      setError(err.message || '加载北斗凭据状态失败');
      setStatus('unbound');
    }
  };

  // Load status when modal opens
  useEffect(() => {
    if (isOpen) {
      loadStatus();
      setShowUnbindConfirm(false);
    }
  }, [isOpen]);

  const handleBindOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('请输入北斗平台用户名');
      return;
    }
    if (!password) {
      setError('请输入北斗平台密码');
      return;
    }
    if (password.length < 12 || password.length > 64) {
      setError('密码长度必须在 12 到 64 个字符之间');
      return;
    }

    setLoadingAction(true);
    setError(null);

    try {
      const data = await bindBeidouCredential(userToken, {
        username: username.trim(),
        password: password,
      });
      setBeidouStatus(data);
      setStatus('bound');
      setPassword('');
    } catch (err: any) {
      setError(err.message || '北斗凭据绑定失败，请检查账号密码');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleUnbind = async () => {
    setLoadingAction(true);
    setError(null);
    try {
      await unbindBeidouCredential(userToken);
      setShowUnbindConfirm(false);
      setBeidouStatus({
        bound: false,
        username: null,
        last_verified_at: null,
        session_expires_at: null,
      });
      setStatus('unbound');
      setUsername('');
      setPassword('');
    } catch (err: any) {
      setError(err.message || '解绑北斗凭据失败');
    } finally {
      setLoadingAction(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      title="北斗监测平台凭证管理"
      onClose={onClose}
      cancelText="关闭"
    >
      <div className="space-y-4">
        {/* Helper description */}
        <p className="text-xs text-neutral-500 leading-relaxed">
          绑定您的北斗灾害监测平台凭证后，LMA 智能体才能够实时获取对应站点的 GNSS 卫星位移数据并进行滑坡风险评估。
        </p>

        {/* Global Error Banner */}
        {error && (
          <div className="flex gap-2.5 p-3 rounded-xl bg-red-50 border border-red-200/60 text-red-700 text-xs animate-in fade-in duration-200">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
            <div className="flex-1 font-medium">{error}</div>
          </div>
        )}

        {/* LOADING STATE */}
        {status === 'loading' && (
          <div className="h-44 flex flex-col items-center justify-center gap-3 text-neutral-400">
            <Loader2 className="w-8 h-8 animate-spin text-neutral-500" />
            <span className="text-xs font-medium">正在获取北斗凭证状态...</span>
          </div>
        )}

        {/* BOUND STATE */}
        {status === 'bound' && beidouStatus && (
          <div className="space-y-4 animate-in fade-in duration-300">
            {/* Status Card */}
            <div className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800 text-white shadow-md relative overflow-hidden group">
              {/* Decorative Background Icon */}
              <Key className="absolute right-[-10px] bottom-[-10px] w-28 h-28 text-white/5 pointer-events-none transform -rotate-12 transition-transform duration-500 group-hover:scale-105" />

              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span className="font-semibold text-sm tracking-tight">北斗业务凭证已绑定</span>
                </div>
                <span className="text-[10px] uppercase font-bold tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                  正常运行
                </span>
              </div>

              {/* Status Details */}
              <div className="mt-4 space-y-2.5 text-xs border-t border-white/10 pt-3.5">
                <div className="flex items-center justify-between text-neutral-400">
                  <div className="flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-neutral-500" />
                    <span>绑定的账号</span>
                  </div>
                  <span className="font-mono text-white font-medium">{beidouStatus.username}</span>
                </div>
                <div className="flex items-center justify-between text-neutral-400">
                  <div className="flex items-center gap-1.5">
                    <RefreshCw className="w-3.5 h-3.5 text-neutral-500" />
                    <span>最近校验时间</span>
                  </div>
                  <span className="text-white font-medium">{formatDateTime(beidouStatus.last_verified_at)}</span>
                </div>
                <div className="flex items-center justify-between text-neutral-400">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-neutral-500" />
                    <span>估算会话有效期至</span>
                  </div>
                  <span className="text-white font-medium">{formatDateTime(beidouStatus.session_expires_at)}</span>
                </div>
              </div>
            </div>

            {/* Unbind Inline Confirmation Warning */}
            {showUnbindConfirm && (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-800 space-y-3 animate-in slide-in-from-top-2 duration-200">
                <div className="flex items-start gap-2">
                  <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div className="font-medium leading-relaxed">
                    确定要解绑北斗凭据吗？解绑后，本系统的地质监测分析、自动研判工具及历史会话将因缺少北斗平台授权而无法获取上游 GNSS 数据。
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2 pt-1 border-t border-amber-200/50">
                  <button
                    onClick={() => setShowUnbindConfirm(false)}
                    disabled={loadingAction}
                    className="px-3 py-1.5 rounded-lg border border-amber-300 text-amber-700 hover:bg-amber-100 transition-colors font-medium"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleUnbind}
                    disabled={loadingAction}
                    className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white transition-colors font-semibold flex items-center gap-1"
                  >
                    {loadingAction && <Loader2 className="w-3 h-3 animate-spin" />}
                    确认解绑
                  </button>
                </div>
              </div>
            )}

            {/* Actions Footer */}
            {!showUnbindConfirm && (
              <div className="flex items-center justify-between gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUnbindConfirm(true)}
                  className="px-3.5 py-2 rounded-xl text-red-600 hover:bg-red-50 border border-neutral-200 text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.98]"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  解除凭证绑定
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStatus('edit');
                    setPassword('');
                  }}
                  className="px-4 py-2 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.98] shadow-sm"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  更新账号密码
                </button>
              </div>
            )}
          </div>
        )}

        {/* UNBOUND STATE & EDIT/UPDATE FORM */}
        {(status === 'unbound' || status === 'edit') && (
          <form onSubmit={handleBindOrUpdate} className="space-y-4 animate-in fade-in duration-300">
            {status === 'edit' && (
              <div className="p-3 bg-neutral-50 border border-neutral-200/60 rounded-xl text-neutral-500 text-xs">
                正在为用户 <strong className="text-neutral-800 font-medium">{beidouStatus?.username}</strong> 修改绑定的密码。新密码通过北斗平台可用性验证后才会生效。
              </div>
            )}

            {/* Username Field */}
            <div className="space-y-1.5">
              <label htmlFor="beidou-username" className="text-xs font-semibold text-neutral-700 block">
                北斗平台用户名
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-neutral-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  id="beidou-username"
                  type="text"
                  placeholder="请输入北斗平台账号"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loadingAction || status === 'edit'}
                  className="w-full pl-10 pr-4 py-2 text-xs border border-neutral-200 rounded-xl focus:border-neutral-900 focus:outline-none transition-all disabled:bg-neutral-50 disabled:text-neutral-400"
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <label htmlFor="beidou-password" className="text-xs font-semibold text-neutral-700 block">
                平台密码
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-neutral-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="beidou-password"
                  type="password"
                  placeholder="请输入密码（12-64个字符）"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loadingAction}
                  className="w-full pl-10 pr-4 py-2 text-xs border border-neutral-200 rounded-xl focus:border-neutral-900 focus:outline-none transition-all disabled:bg-neutral-50 disabled:text-neutral-450"
                  minLength={12}
                  maxLength={64}
                  required
                />
              </div>
              <p className="text-[10px] text-neutral-400">
                依据北斗平台规范，密码长度需介于 12 至 64 个字符。
              </p>
            </div>

            {/* Form Footer Buttons */}
            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-neutral-100">
              {status === 'edit' && (
                <button
                  type="button"
                  onClick={() => {
                    setStatus('bound');
                    setUsername(beidouStatus?.username || '');
                    setError(null);
                  }}
                  disabled={loadingAction}
                  className="px-4 py-2 rounded-xl border border-neutral-200 text-neutral-600 hover:bg-neutral-50 text-xs font-semibold transition-all active:scale-[0.98]"
                >
                  取消
                </button>
              )}
              <button
                type="submit"
                disabled={loadingAction}
                className="px-4 py-2 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.98] shadow-sm disabled:bg-neutral-350"
              >
                {loadingAction ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    正在校验并绑定...
                  </>
                ) : (
                  <>
                    <Key className="w-3.5 h-3.5" />
                    {status === 'edit' ? '确认更新' : '立即绑定'}
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
};
