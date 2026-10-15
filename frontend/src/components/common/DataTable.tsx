import React, { useState, useEffect } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  isNumeric?: boolean;
  width?: string;
  sortable?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T, index: number) => string;
  onRowClick?: (item: T, index: number) => void;
  selectedId?: string | null;
  isLoading?: boolean;
  emptyMessage?: string;
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  selectedId,
  isLoading = false,
  emptyMessage = 'No records found.',
  className = '',
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  // Sync selectedId with index
  useEffect(() => {
    if (selectedId != null) {
      const idx = data.findIndex((item, i) => keyExtractor(item, i) === selectedId);
      setSelectedIndex(idx);
    }
  }, [selectedId, data, keyExtractor]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sortedData = React.useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a: any, b: any) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal === bVal) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const res = aVal < bVal ? -1 : 1;
      return sortDir === 'asc' ? res : -res;
    });
  }, [data, sortKey, sortDir]);

  // Keyboard navigation: arrow-up/down moves selection, Enter triggers click
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!data.length || !onRowClick) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const next = Math.min(selectedIndex + 1, data.length - 1);
      setSelectedIndex(next);
      onRowClick(sortedData[next], next);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const prev = Math.max(selectedIndex - 1, 0);
      setSelectedIndex(prev);
      onRowClick(sortedData[prev], prev);
    } else if (e.key === 'Enter' && selectedIndex >= 0 && selectedIndex < data.length) {
      e.preventDefault();
      onRowClick(sortedData[selectedIndex], selectedIndex);
    }
  };

  return (
    <div
      className={`w-full overflow-x-auto focus:outline-none ${className}`}
      tabIndex={onRowClick ? 0 : undefined}
      onKeyDown={handleKeyDown}
      role={onRowClick ? 'grid' : 'region'}
      aria-label="Data Table"
    >
      <table className="w-full text-left border-collapse text-[13px]">
        <thead>
          <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider sticky top-0 z-10 select-none">
            {columns.map((col) => {
              const alignClass =
                col.align === 'right' || col.isNumeric
                  ? 'text-right'
                  : col.align === 'center'
                  ? 'text-center'
                  : 'text-left';

              const isSorted = sortKey === col.key;

              return (
                <th
                  key={col.key}
                  style={{ width: col.width }}
                  className={`px-3 py-1.5 font-medium whitespace-nowrap ${alignClass} ${
                    col.sortable ? 'cursor-pointer hover:text-text' : ''
                  }`}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  aria-sort={isSorted ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortable && isSorted && (
                      <span className="text-[10px] text-accent">
                        {sortDir === 'asc' ? '▲' : '▼'}
                      </span>
                    )}
                  </span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {isLoading ? (
            Array.from({ length: 5 }).map((_, rIdx) => (
              <tr key={rIdx} className="h-[40px]">
                {columns.map((_, cIdx) => (
                  <td key={cIdx} className="px-3 py-2">
                    <div className="h-4 bg-surface-2 rounded-[3px] w-3/4" />
                  </td>
                ))}
              </tr>
            ))
          ) : sortedData.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="h-[80px] text-center text-text-3 text-[13px]"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedData.map((item, idx) => {
              const id = keyExtractor(item, idx);
              const isSelected = selectedId === id || selectedIndex === idx;

              return (
                <tr
                  key={id}
                  onClick={() => {
                    setSelectedIndex(idx);
                    onRowClick?.(item, idx);
                  }}
                  className={`h-[40px] transition-colors relative ${
                    onRowClick ? 'cursor-pointer' : ''
                  } ${
                    isSelected
                      ? 'bg-surface-2 font-medium'
                      : 'hover:bg-surface-2/60 bg-surface'
                  }`}
                >
                  {columns.map((col, cIdx) => {
                    const alignClass =
                      col.align === 'right' || col.isNumeric
                        ? 'text-right'
                        : col.align === 'center'
                        ? 'text-center'
                        : 'text-left';

                    const numericClass = col.isNumeric ? 'font-mono tabular-nums' : '';

                    return (
                      <td
                        key={col.key}
                        className={`px-3 py-2 text-text relative whitespace-nowrap ${alignClass} ${numericClass}`}
                      >
                        {/* 3px accent left border on selected row */}
                        {cIdx === 0 && isSelected && (
                          <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-accent" />
                        )}
                        {col.render ? col.render(item, idx) : (item as any)[col.key]}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
