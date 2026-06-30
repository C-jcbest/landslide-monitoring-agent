import React, { useState } from 'react';
import { AlertTriangle, Send, Loader2, Sparkles } from 'lucide-react';

interface HumanPromptCardProps {
  question: string;
  onSubmit: (response: string) => void;
  loading: boolean;
}

const MAX_MESSAGE_LENGTH = 3000;

const QUICK_RESPONSES = [
  '确认无误，请继续执行。',
  '已核实当前数据，请恢复监测。',
  '忽略此次异常，跳过以继续。',
];

export const HumanPromptCard: React.FC<HumanPromptCardProps> = ({ question, onSubmit, loading }) => {
  const [value, setValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !loading) {
      onSubmit(value.trim());
      setValue('');
    }
  };

  const handleQuickResponse = (resp: string) => {
    if (!loading) {
      setValue(resp);
    }
  };

  return (
    <div className="relative mx-auto max-w-2xl my-6 bg-gradient-to-br from-amber-50/70 via-white to-amber-50/20 border border-amber-200/60 rounded-2xl pl-7 pr-6 py-6 shadow-[0_10px_30px_-10px_rgba(245,158,11,0.08)] transition-all overflow-hidden">
      {/* Accent gradient line at the left edge */}
      <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-amber-500 to-orange-500" />

      <div className="flex items-start gap-4 mb-4">
        <div className="w-9 h-9 rounded-xl bg-amber-100 border border-amber-200 flex items-center justify-center shrink-0">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-bold text-amber-800 uppercase tracking-wider">监测人工干预请求</h3>
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
          </div>
          <p className="text-slate-700 text-sm mt-1.5 leading-relaxed font-semibold">{question}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Quick action buttons to auto-fill response */}
        <div>
          <div className="flex items-center gap-1 text-[11px] font-medium text-slate-400 mb-2 select-none">
            <Sparkles className="w-3 h-3 text-amber-500/80" />
            <span>智能推荐快捷回复：</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {QUICK_RESPONSES.map((resp, index) => (
              <button
                key={index}
                type="button"
                onClick={() => handleQuickResponse(resp)}
                disabled={loading}
                className="px-3 py-1.5 rounded-lg border border-slate-200/80 hover:border-amber-300 bg-white hover:bg-amber-50/40 disabled:opacity-40 text-xs text-slate-600 hover:text-amber-800 transition-all cursor-pointer shadow-[0_1px_2px_rgba(0,0,0,0.02)] select-none active:scale-95 disabled:scale-100 disabled:pointer-events-none"
              >
                {resp}
              </button>
            ))}
          </div>
        </div>

        {/* Textarea container */}
        <div className="relative rounded-xl border border-slate-200 bg-white focus-within:border-amber-500 focus-within:ring-4 focus-within:ring-amber-500/10 transition-all duration-200 overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={loading}
            maxLength={MAX_MESSAGE_LENGTH}
            placeholder="输入您的确认说明或答复以继续监测..."
            className="w-full bg-transparent px-4 py-3 text-slate-800 text-sm outline-none resize-none h-24 placeholder:text-slate-400"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <div className="absolute bottom-2.5 right-3 flex items-center gap-2 text-[10px] text-slate-400 select-none">
            <span>Shift + Enter 换行</span>
            <span>/</span>
            <span>Enter 发送</span>
            <span>/</span>
            <span className={value.length >= 2800 ? 'text-red-500 font-medium' : ''}>
              {value.length}/{MAX_MESSAGE_LENGTH}
            </span>
          </div>
        </div>

        {/* Submit button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!value.trim() || loading}
            aria-label="提交人工干预回复"
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 disabled:from-slate-200 disabled:to-slate-200 disabled:text-slate-400 text-white font-medium text-xs tracking-wide shadow-sm hover:shadow-md transition-all flex items-center gap-2 active:scale-95 disabled:scale-100 disabled:shadow-none cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>正在恢复 Agent...</span>
              </>
            ) : (
              <>
                <span>确认并提交指令</span>
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
