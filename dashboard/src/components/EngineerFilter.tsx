import { useState, useEffect, useRef } from 'react';

interface EngineerFilterProps {
  names: string[];
  colors: string[];
  selected: Set<string>;
  onToggle: (name: string) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
}

export function EngineerFilter({ names, colors, selected, onToggle, onSelectAll, onClearAll }: EngineerFilterProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const filterLabel = selected.size === names.length
    ? 'All Engineers'
    : selected.size === 0
      ? 'No Engineers'
      : 'Engineers';

  return (
    <div className="filter-bar">
      <div className={`filter-dropdown${open ? ' open' : ''}`} ref={ref} data-testid="engineer-filter">
        <button
          className="filter-button"
          onClick={() => setOpen(o => !o)}
          data-testid="engineer-filter-btn"
        >
          <span className="filter-icon">{'\u{1F464}'}</span>
          <span data-testid="filter-label">{filterLabel}</span>
          {selected.size > 0 && selected.size < names.length && (
            <span className="filter-count" data-testid="filter-count">{selected.size}</span>
          )}
          <span className="dropdown-arrow">{'▼'}</span>
        </button>
        <div className="filter-panel" data-testid="filter-panel">
          <div className="filter-actions">
            <button className="filter-action-btn" onClick={onSelectAll} data-testid="select-all-btn">Select All</button>
            <button className="filter-action-btn" onClick={onClearAll} data-testid="clear-all-btn">Clear All</button>
          </div>
          <div className="filter-search">
            <input
              type="text"
              placeholder="Search engineers..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              data-testid="engineer-search"
            />
          </div>
          <div className="filter-list">
            {names.map((name, index) => {
              const visible = !search || name.toLowerCase().includes(search.toLowerCase());
              return (
                <div
                  key={name}
                  className={`filter-checkbox${visible ? '' : ' hidden'}`}
                  data-testid={`filter-checkbox-${index}`}
                >
                  <input
                    type="checkbox"
                    id={`engineer-${index}`}
                    checked={selected.has(name)}
                    onChange={() => onToggle(name)}
                  />
                  <label htmlFor={`engineer-${index}`}>
                    {name}
                    <span className="engineer-color-dot" style={{ backgroundColor: colors[index] }} />
                  </label>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
