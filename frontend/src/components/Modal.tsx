import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  title: string;
  onClose: () => void;
  onConfirm?: () => void;
  confirmText?: string;
  cancelText?: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  title,
  onClose,
  onConfirm,
  confirmText = '确认',
  cancelText = '取消',
  children,
}) => {
  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[2px] transition-opacity">
      {/* Modal Container */}
      <div
        role="dialog"
        aria-modal="true"
        className="bg-white rounded-2xl w-full max-w-lg overflow-hidden border border-neutral-200 shadow-2xl flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-100 flex items-center justify-between bg-neutral-50/50">
          <h3 className="text-base font-semibold text-neutral-800 tracking-tight">{title}</h3>
          <button
            onClick={onClose}
            aria-label="关闭弹窗"
            className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto text-sm text-neutral-600 leading-relaxed flex-1">
          {children}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-100 flex items-center justify-end gap-3 bg-neutral-50/50">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-neutral-600 hover:bg-neutral-100 border border-neutral-200 text-xs font-medium transition-colors"
          >
            {cancelText}
          </button>
          {onConfirm && (
            <button
              onClick={onConfirm}
              className="px-4 py-2 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium transition-colors shadow-sm"
            >
              {confirmText}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
