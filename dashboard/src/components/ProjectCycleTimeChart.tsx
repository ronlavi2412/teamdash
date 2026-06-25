import { Line } from 'react-chartjs-2';
import type { CycleTimeQuarterData } from '../types';
import { calculatePercentile, getQuarterLabel } from '../utils';

const PROJECT_COLORS = [
  '#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16',
];

interface ProjectCycleTimeChartProps {
  cycleTimeData: Record<string, CycleTimeQuarterData>;
  cycleTimeProjects: string[];
  quarterLabels: string[];
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
}

export function ProjectCycleTimeChart({
  cycleTimeData, cycleTimeProjects, quarterLabels,
  currentQuarterIndex, isCurrentQuarter,
}: ProjectCycleTimeChartProps) {
  const labels = quarterLabels.map((q, idx) =>
    getQuarterLabel(q, idx, currentQuarterIndex, isCurrentQuarter),
  );

  const datasets = cycleTimeProjects.map((proj, i) => {
    const color = PROJECT_COLORS[i % PROJECT_COLORS.length];
    const data = quarterLabels.map(label => {
      const qData = cycleTimeData[label];
      if (!qData || !qData[proj]) return null;
      const allTotals: number[] = [];
      for (const phases of Object.values(qData[proj])) {
        allTotals.push(...phases.total);
      }
      return calculatePercentile(allTotals, 50);
    });

    return {
      label: proj,
      data,
      borderColor: color,
      backgroundColor: color + '20',
      tension: 0.3,
      fill: false,
      pointRadius: 5,
      pointBackgroundColor: color,
      spanGaps: true,
      segment: {
        borderDash: (ctx: any) => {
          if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) return [5, 5];
          return [];
        },
      },
    };
  });

  return (
    <Line
      data={{ labels, datasets }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: 'bottom' as const },
          tooltip: {
            callbacks: {
              label: (context: any) =>
                `${context.dataset.label}: ${context.parsed.y} days`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Business Days (Median)' },
          },
        },
      }}
    />
  );
}
