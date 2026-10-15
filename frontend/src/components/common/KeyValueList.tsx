import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export interface KeyValueItem {
  label: string;
  value: React.ReactNode;
  rawCopyValue?: string;
  isMono?: boolean;
}

interface KeyValueListProps {
  items: KeyValueItem[];
  className?: string;
}

export const KeyValueList: React.FC<KeyValueListProps> = ({ items, className = '' }) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (key: string, text: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  return (
    <dl className={`divide-y divide-border text-[13px] ${className}`}>
      {items.map((item, idx) => {
        const copyText =
          item.rawCopyValue || (typeof item.value === 'string' ? item.value : null);

        const hasCopy = Boolean(copyText && (item.isMono || item.rawCopyValue));
        const isCopied = copiedKey === item.label;

        return (
          <div key={idx} className="py-2 flex items-start justify-between gap-3">
            <dt className="text-[12px] text-text-3 font-medium shrink-0 pt-0.5">
              {item.label}
            </dt>
            <dd className="text-right flex items-center justify-end gap-1.5 min-w-0">
              <span
                className={`truncate ${
                  item.isMono ? 'font-mono text-[12px] text-text' : 'text-text'
                }`}
              >
                {item.value}
              </span>
              {hasCopy && (
                <button
                  type="button"
                  onClick={() => handleCopy(item.label, copyText!)}
                  className="p-1 rounded-[4px] hover:bg-surface-2 text-text-3 hover:text-text transition-colors shrink-0 cursor-pointer"
                  title={isCopied ? 'Copied' : 'Copy to clipboard'}
                >
                  {isCopied ? (
                    <span className="flex items-center gap-1 text-[11px] text-ok font-mono font-medium">
                      <Check className="w-3.5 h-3.5" />
                      <span>Copied</span>
                    </span>
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
};
