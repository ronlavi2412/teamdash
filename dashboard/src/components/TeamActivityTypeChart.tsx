import { useMemo, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import type { QuarterData } from '../types';
import { getQuarterLabel } from '../utils';

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

interface TeamActivityTypeChartProps {
  quarters: QuarterData[];
  activityTypeNames: string[];
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
}

export function TeamActivityTypeChart({
  quarters, activityTypeNames, currentQuarterIndex, isCurrentQuarter,
}: TeamActivityTypeChartProps) {
  const [sprintOnly, setSprintOnly] = useState(false);

  const chartData = useMemo(() => ({
    labels: quarters.map((q, idx) =>
      getQuarterLabel(q.label, idx, currentQuarterIndex, isCurrentQuarter)
    ),
    datasets: activityTypeNames.map((type, i) => ({
      label: type,
      data: quarters.map(q => {
        const source = sprintOnly ? q.sprint_activity_types : q.activity_types;
        return source.reduce((sum, eng) => sum + (eng[type] ?? 0), 0);
      }),
      backgroundColor: getColor(type, i),
      borderRadius: 2,
    })),
  }), [quarters, activityTypeNames, currentQuarterIndex, isCurrentQuarter, sprintOnly]);

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
      <div style={{ marginBottom: 8, flexShrink: 0 }}>
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
