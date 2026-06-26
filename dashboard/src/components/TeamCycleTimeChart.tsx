import type { ScriptableLineSegmentContext } from 'chart.js';
import { Line } from 'react-chartjs-2';
import type { CycleTimeQuarterData } from '../types';
import { calculatePercentile, getQuarterLabel } from '../utils';

const ISSUE_TYPE_COLORS: Record<string, string> = {
  Story: '#10b981',
  Bug: '#f59e0b',
  Vulnerability: '#eab308',
};

interface TeamCycleTimeChartProps {
  cycleTimeData: Record<string, CycleTimeQuarterData>;
  quarterLabels: string[];
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
}

function collectTotalsByType(
  cycleTimeData: Record<string, CycleTimeQuarterData>,
  quarterLabels: string[],
): { issueTypes: string[]; byType: Record<string, (number | null)[]> } {
  const typeSet = new Set<string>();
  for (const qData of Object.values(cycleTimeData)) {
    for (const projTypes of Object.values(qData)) {
      for (const typeName of Object.keys(projTypes)) {
        typeSet.add(typeName);
      }
    }
  }
  const issueTypes = [...typeSet].sort();

  const byType: Record<string, (number | null)[]> = {};
  for (const t of issueTypes) {
    byType[t] = quarterLabels.map(label => {
      const qData = cycleTimeData[label];
      if (!qData) return null;
      const allTotals: number[] = [];
      for (const projTypes of Object.values(qData)) {
        const phases = projTypes[t];
        if (phases) allTotals.push(...phases.total);
      }
      return calculatePercentile(allTotals, 50);
    });
  }
  return { issueTypes, byType };
}

export function TeamCycleTimeChart({ cycleTimeData, quarterLabels, currentQuarterIndex, isCurrentQuarter }: TeamCycleTimeChartProps) {
  const labels = quarterLabels.map((q, idx) => getQuarterLabel(q, idx, currentQuarterIndex, isCurrentQuarter));
  const { issueTypes, byType } = collectTotalsByType(cycleTimeData, quarterLabels);

  return (
    <Line
      data={{
        labels,
        datasets: issueTypes.map(t => ({
          label: t,
          data: byType[t],
          borderColor: ISSUE_TYPE_COLORS[t] ?? '#6366f1',
          backgroundColor: (ISSUE_TYPE_COLORS[t] ?? '#6366f1') + '20',
          tension: 0.3,
          fill: false,
          pointRadius: 5,
          pointBackgroundColor: ISSUE_TYPE_COLORS[t] ?? '#6366f1',
          spanGaps: true,
          segment: {
            borderDash: (ctx: ScriptableLineSegmentContext) => {
              if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) return [5, 5];
              return [];
            },
          },
        })),
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: 'top' },
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: 'Business Days' } },
        },
      }}
    />
  );
}
