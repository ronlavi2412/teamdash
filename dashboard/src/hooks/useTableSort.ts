import { useState, useCallback, useMemo } from 'react';

export function useTableSort<T>(rows: T[], getCellValue: (row: T, colIdx: number) => string | number) {
  const [sortCol, setSortCol] = useState<number | null>(null);
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = useCallback((colIdx: number) => {
    setSortCol(prev => {
      if (prev === colIdx) {
        setSortAsc(a => !a);
        return colIdx;
      }
      setSortAsc(false);
      return colIdx;
    });
  }, []);

  const sortedRows = useMemo(() => {
    if (sortCol === null) return rows;
    const sorted = [...rows].sort((a, b) => {
      const va = getCellValue(a, sortCol);
      const vb = getCellValue(b, sortCol);
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortAsc ? va - vb : vb - va;
      }
      const sa = String(va);
      const sb = String(vb);
      return sortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
    return sorted;
  }, [rows, sortCol, sortAsc, getCellValue]);

  return { sortedRows, sortCol, sortAsc, handleSort };
}
