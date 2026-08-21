import { useMemo, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import type { QuarterData } from '../types';

const ACTIVITY_TYPE_COLORS: Record<string, string> = {
  'Associate Wellness & Development': '#8b5cf6',
  'Future Sustainability': '#06b6d4',
  'Incidents & Support': '#ef4444',
  'Quality / Stability / Reliability': '#f59e0b',
  'Security & Compliance': '#10b981',
  'Product / Portfolio Work': '#3b82f6',
};

const FALLBACK_COLORS = [
  '#6366f1', '#d946ef', '#0ea5e9', '#84cc16', '#14b8a6', '#ec4899',
];

function getColor(name: string, index: number): string {
  return ACTIVITY_TYPE_COLORS[name] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

interface ActivityTypeChartProps {
  quarters: QuarterData[];
  names: string[];
  colors: string[];
  selectedEngineers: Set<string>;
  activityTypeNames: string[];
  quarterLabels: string[];
}

export function ActivityTypeChart({
  quarters, names, selectedEngineers, activityTypeNames, quarterLabels,
}: ActivityTypeChartProps) {
  const [selectedQuarter, setSelectedQuarter] = useState(quarters.length - 1);
  const [sprintOnly, setSprintOnly] = useState(false);

  const filteredIndices = useMemo(() =>
    names.map((n, i) => ({ n, i })).filter(({ n }) => selectedEngineers.has(n)).map(({ i }) => i),
    [names, selectedEngineers],
  );

  const filteredNames = useMemo(() => filteredIndices.map(i => names[i]), [filteredIndices, names]);

  const chartData = useMemo(() => {
    const q = quarters[selectedQuarter];
    const source = sprintOnly ? q.sprint_activity_types : q.activity_types;
    return {
      labels: filteredNames,
      datasets: activityTypeNames.map((type, ti) => ({
        label: type,
        data: filteredIndices.map(i => source[i]?.[type] ?? 0),
        backgroundColor: getColor(type, ti),
        borderRadius: 2,
      })),
    };
  }, [quarters, activityTypeNames, selectedQuarter, filteredIndices, filteredNames, sprintOnly]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: { usePointStyle: true, font: { size: 11 }, padding: 12 },
      },
    },
    scales: {
      x: { stacked: true },
      y: { stacked: true, beginAtZero: true, title: { display: true, text: 'Story Points' } },
    },
  }), []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: 8, flexShrink: 0, display: 'flex', alignItems: 'center', gap: 16 }}>
        <select
          value={selectedQuarter}
          onChange={e => setSelectedQuarter(Number(e.target.value))}
          style={{
            padding: '4px 8px',
            borderRadius: 4,
            border: '1px solid #555',
            background: '#1e1e2e',
            color: '#e0e0e0',
            fontSize: 13,
          }}
        >
          {quarterLabels.map((label, i) => (
            <option key={i} value={i}>{label}</option>
          ))}
        </select>
        <label style={{ fontSize: 13, cursor: 'pointer', userSelect: 'none' }}>
          <input
            type="checkbox"
            checked={sprintOnly}
            onChange={e => setSprintOnly(e.target.checked)}
            style={{ marginRight: 6 }}
          />
          Completed sprints only
        </label>
      </div>
      <div style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <Bar data={chartData} options={chartOptions} />
      </div>
    </div>
  );
}
