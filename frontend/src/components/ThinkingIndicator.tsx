import React from 'react';
import { Loader2 } from 'lucide-react';

interface ThinkingIndicatorProps {
  statusText?: string;
}

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({
  statusText = 'Agent 正在分析监测数据并加载回复...',
}) => {
  return (
    <div className="flex items-start gap-4 p-5 bg-slate-950/20 rounded-xl border border-slate-900">
      <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center shrink-0 border border-indigo-500/20">
        <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
      </div>
      <div className="flex-1 py-1">
        <div className="text-sm text-slate-400 font-medium animate-pulse">{statusText}</div>
        <div className="text-xs text-slate-500 mt-1">这可能需要几秒钟，正在协调 DuckDuckGo 搜索与滑坡分析工具...</div>
      </div>
    </div>
  );
};
