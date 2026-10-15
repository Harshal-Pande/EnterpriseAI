import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export type ToastType = 'info' | 'ok' | 'warn' | 'danger';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  timestamp?: string;
}

interface ToastProps {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}

export const Toast: React.FC<ToastProps> = ({ toast, onDismiss }) => {
  useEffect(() => {
    // Errors persist until explicitly closed, other toasts auto-dismiss after 5s
    if (toast.type !== 'danger') {
      const timer = setTimeout(() => {
        onDismiss(toast.id);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [toast, onDismiss]);

  const leftBarColor = {
    info: 'border-l-info',
    ok: 'border-l-ok',
    warn: 'border-l-warn',
    danger: 'border-l-danger',
  }[toast.type];

  return (
    <div
      role="status"
      aria-live="polite"
      className={`rounded-[4px] border border-border border-l-4 ${leftBarColor} bg-surface p-3 text-[12px] text-text shadow-lg flex items-start justify-between gap-3 min-w-[280px] max-w-sm`}
    >
      <div className="min-w-0">
        {toast.title && (
          <div className="font-semibold text-text text-[13px] mb-0.5">
            {toast.title}
          </div>
        )}
        <div className="text-text-2 leading-tight">{toast.message}</div>
      </div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="text-text-3 hover:text-text p-0.5 rounded-[3px] transition-colors shrink-0 cursor-pointer"
        title="Dismiss"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
