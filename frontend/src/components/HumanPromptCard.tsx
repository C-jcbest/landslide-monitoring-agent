import React, { useState } from 'react';
import { AlertTriangle, Send } from 'lucide-react';

interface HumanPromptCardProps {
  question: string;
  onSubmit: (response: string) => void;
  loading: boolean;
}

const MAX_MESSAGE_LENGTH = 3000;

export const HumanPromptCard: React.FC<HumanPromptCardProps> = ({ question, onSubmit, loading }) => {
  const [value, setValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !loading) {
      onSubmit(value.trim());
      setValue('');
    }
  };

  return (
    <div className="mx-auto max-w-2xl my-6 bg-gradient-to-br from-amber-500/10 to-orange-600/10 border border-amber-500/25 rounded-2xl p-6 shadow-xl shadow-amber-500/5 animate-pulse-slow">
      <div className="flex items-start gap-4 mb-4">
        <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center shrink-0">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-amber-300 uppercase tracking-wider">监测人工干预请求</h3>
          <p className="text-slate-300 text-sm mt-1 leading-relaxed font-medium">{question}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative rounded-xl overflow-hidden glass-input border border-amber-500/20">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={loading}
            maxLength={MAX_MESSAGE_LENGTH}
            placeholder="输入您的确认说明或答复以继续监测..."
            className="w-full bg-transparent px-4 py-3 text-slate-100 text-sm outline-none resize-none h-20 placeholder:text-slate-500"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <div className="absolute bottom-2.5 right-3 flex items-center gap-2 text-[10px] text-slate-500">
            <span>Shift + Enter 换行</span>
            <span>/</span>
            <span>Enter 发送</span>
            <span>/</span>
            <span className={value.length >= 2800 ? 'text-red-400' : ''}>
              {value.length}/{MAX_MESSAGE_LENGTH}
            </span>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!value.trim() || loading}
            aria-label="提交人工干预回复"
            className="px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-slate-950 font-semibold text-xs tracking-wide uppercase transition-all flex items-center gap-2 active:scale-95 disabled:scale-100"
          >
            {loading ? '正在恢复 Agent...' : '确认并提交指令'}
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
    </div>
  );
};
