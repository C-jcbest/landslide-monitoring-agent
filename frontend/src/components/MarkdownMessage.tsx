import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownMessageProps {
  content: string;
}

export const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content }) => (
  <div className="prose message-markdown text-sm break-words leading-relaxed">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        table: ({ children, ...props }) => (
          <div className="markdown-table-wrap">
            <table {...props}>{children}</table>
          </div>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
);
