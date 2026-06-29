import React, { useState } from 'react';
import { login, register, setStoredUserToken, setStoredUsername } from '../services/api';
import { Mountain, Lock, Mail, User, AlertCircle, Loader2 } from 'lucide-react';

interface AuthScreenProps {
  onAuthSuccess: () => void;
}

export const AuthScreen: React.FC<AuthScreenProps> = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isLogin) {
        const response = await login(email, password);
        setStoredUserToken(response.access_token);
        // Extract mock display name from email for aesthetic personalization
        const displayName = email.split('@')[0];
        setStoredUsername(displayName);
      } else {
        const response = await register(email, password, username || undefined);
        setStoredUserToken(response.token.access_token);
        setStoredUsername(response.username || response.email.split('@')[0]);
      }
      onAuthSuccess();
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f9f9f9] px-4 select-none">
      {/* Main Card */}
      <div className="w-full max-w-md bg-white border border-neutral-200 rounded-2xl p-8 shadow-xl transition-all duration-300">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-neutral-900 flex items-center justify-center shadow-sm mb-3">
            <Mountain className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900">Landslide Monitoring</h1>
          <p className="text-sm text-neutral-500 mt-1">
            {isLogin ? '登录以访问智能体工作流' : '创建新账户以开始监测'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-red-700 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {!isLogin && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-neutral-500">用户名</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-400">
                  <User className="w-4 h-4" />
                </span>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-neutral-200 bg-white text-neutral-800 text-sm outline-none transition-all focus:border-neutral-400 shadow-sm"
                  placeholder="输入用户名（可选）"
                />
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-neutral-500">电子邮箱</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-400">
                <Mail className="w-4 h-4" />
              </span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-neutral-200 bg-white text-neutral-800 text-sm outline-none transition-all focus:border-neutral-400 shadow-sm"
                placeholder="name@example.com"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-neutral-500">密码</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-400">
                <Lock className="w-4 h-4" />
              </span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-neutral-200 bg-white text-neutral-800 text-sm outline-none transition-all focus:border-neutral-400 shadow-sm"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 mt-2 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium text-sm transition-all active:scale-[0.98] disabled:opacity-50 disabled:scale-100 flex items-center justify-center gap-2 shadow-sm"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin animate-pulse" />
                正在提交...
              </>
            ) : isLogin ? (
              '立即登录'
            ) : (
              '注册账户'
            )}
          </button>
        </form>

        <div className="mt-8 text-center text-sm">
          <span className="text-neutral-500">
            {isLogin ? '还没有账户？' : '已经有账户了？'}
          </span>{' '}
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            className="font-medium text-neutral-800 hover:text-black transition-colors underline underline-offset-4"
          >
            {isLogin ? '立即注册' : '返回登录'}
          </button>
        </div>
      </div>
    </div>
  );
};
