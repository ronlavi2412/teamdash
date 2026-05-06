import { useState, useCallback } from 'react';

export function useEngineerFilter(names: string[]) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set(names));

  const toggle = useCallback((name: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelected(new Set(names));
  }, [names]);

  const clearAll = useCallback(() => {
    setSelected(new Set());
  }, []);

  return { selected, toggle, selectAll, clearAll };
}
