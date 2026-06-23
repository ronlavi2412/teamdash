import { useState } from 'react';

interface SummariesViewProps {
  summaries: Record<string, string>;
  names: string[];
}

export function SummariesView({ summaries, names }: SummariesViewProps) {
  const engineersWithSummaries = names.filter(n => summaries[n]);
  const [selected, setSelected] = useState(engineersWithSummaries[0] ?? '');

  if (engineersWithSummaries.length === 0) {
    return <div className="chart-card"><p>No summaries available.</p></div>;
  }

  const text = summaries[selected] ?? '';
  const paragraphs = text.split('\n\n').filter(p => p.trim());

  return (
    <div>
      <div className="summary-tabs">
        {engineersWithSummaries.map(name => (
          <button
            key={name}
            className={`summary-tab${selected === name ? ' active' : ''}`}
            onClick={() => setSelected(name)}
          >
            {name}
          </button>
        ))}
      </div>
      <div className="chart-card summary-content">
        <h3>{selected} — Quarterly Summary</h3>
        {paragraphs.map((p, i) => (
          <p key={i} className="summary-paragraph">{p.trim()}</p>
        ))}
      </div>
    </div>
  );
}
