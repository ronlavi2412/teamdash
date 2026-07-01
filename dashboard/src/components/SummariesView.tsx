import { useState } from 'react';

interface SummariesViewProps {
  summaries: Record<string, Record<string, string>>;
  names: string[];
  quarterLabels: string[];
}

export function SummariesView({ summaries, names, quarterLabels }: SummariesViewProps) {
  const quartersWithSummaries = quarterLabels.filter(q => summaries[q] && Object.keys(summaries[q]).length > 0);
  const [selectedQuarter, setSelectedQuarter] = useState(quartersWithSummaries[quartersWithSummaries.length - 1] ?? '');
  const [selectedEngineer, setSelectedEngineer] = useState('');

  if (quartersWithSummaries.length === 0) {
    return <div className="chart-card"><p>No summaries available.</p></div>;
  }

  const quarterSummaries = summaries[selectedQuarter] ?? {};
  const engineersWithSummaries = names.filter(n => quarterSummaries[n]);
  const active = engineersWithSummaries.includes(selectedEngineer)
    ? selectedEngineer
    : engineersWithSummaries[0] ?? '';

  const text = quarterSummaries[active] ?? '';
  const paragraphs = text.split('\n\n').filter(p => p.trim());

  return (
    <div>
      <div className="quarter-tabs">
        {quartersWithSummaries.map(q => (
          <button
            key={q}
            className={`quarter-tab${selectedQuarter === q ? ' active' : ''}`}
            onClick={() => setSelectedQuarter(q)}
          >
            {q}
          </button>
        ))}
      </div>
      <div className="summary-tabs">
        {engineersWithSummaries.map(name => (
          <button
            key={name}
            className={`summary-tab${active === name ? ' active' : ''}`}
            onClick={() => setSelectedEngineer(name)}
          >
            {name}
          </button>
        ))}
      </div>
      <div className="chart-card summary-content">
        <h3>{active} &mdash; {selectedQuarter} Summary</h3>
        {paragraphs.map((p, i) => (
          <p key={i} className="summary-paragraph">{p.trim()}</p>
        ))}
      </div>
    </div>
  );
}
