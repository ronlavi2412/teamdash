import { useState } from 'react';
import type { DashboardData } from '../types';
import { buildTeamSummary } from '../teamSummary';

interface SummariesViewProps {
  summaries: Record<string, Record<string, string>>;
  data: DashboardData;
}

export function SummariesView({ summaries, data }: SummariesViewProps) {
  const { names, quarterLabels } = data;
  const quartersWithSummaries = quarterLabels.filter(q => summaries[q] && Object.keys(summaries[q]).length > 0);
  const [selectedQuarter, setSelectedQuarter] = useState(quartersWithSummaries[quartersWithSummaries.length - 1] ?? '');
  const [selectedEngineer, setSelectedEngineer] = useState('');

  if (quartersWithSummaries.length === 0) {
    return <div className="chart-card"><p>No summaries available.</p></div>;
  }

  const quarterSummaries = summaries[selectedQuarter] ?? {};
  const engineersWithSummaries = names.filter(n => quarterSummaries[n]);
  const active = engineersWithSummaries.includes(selectedEngineer) ? selectedEngineer : '';

  const text = active ? quarterSummaries[active] : buildTeamSummary(data, selectedQuarter);
  const blocks = text.trim().split(/\r?\n\s*\r?\n/).filter(Boolean);

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
        <button
          className={`summary-tab${active === '' ? ' active' : ''}`}
          onClick={() => setSelectedEngineer('')}
          aria-pressed={active === ''}
        >
          Team Summary
        </button>
        {engineersWithSummaries.map(name => (
          <button
            key={name}
            className={`summary-tab${active === name ? ' active' : ''}`}
            onClick={() => setSelectedEngineer(name)}
            aria-pressed={active === name}
          >
            {name}
          </button>
        ))}
      </div>
      <div className="chart-card summary-content">
        <h3>{active || 'Team'} &mdash; {selectedQuarter} Summary</h3>
        {blocks.map((block, i) => {
          const heading = block.match(/^## ([^\n]+)$/);
          if (heading) {
            return <h4 key={i} className="summary-heading">{heading[1]}</h4>;
          }
          const lines = block.split(/\r?\n/);
          if (lines.every(line => line.startsWith('- '))) {
            return (
              <ul key={i} className="summary-list">
                {lines.map((line, j) => {
                  const item = line.slice(2);
                  const labelEnd = item.indexOf(': ');
                  return (
                    <li key={j}>
                      {labelEnd === -1 ? item : (
                        <><strong>{item.slice(0, labelEnd)}</strong>{item.slice(labelEnd)}</>
                      )}
                    </li>
                  );
                })}
              </ul>
            );
          }
          return <p key={i} className="summary-paragraph">{block}</p>;
        })}
      </div>
    </div>
  );
}
