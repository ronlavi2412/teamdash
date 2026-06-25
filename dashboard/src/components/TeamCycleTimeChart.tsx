import { Line } from 'react-chartjs-2';
import type { CycleTimeQuarterData } from '../types';
import { calculatePercentile, getQuarterLabel } from '../utils';

interface TeamCycleTimeChartProps {
  cycleTimeData: Record<string, CycleTimeQuarterData>;
  quarterLabels: string[];
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
}

export function TeamCycleTimeChart({ cycleTimeData, quarterLabels, currentQuarterIndex, isCurrentQuarter }: TeamCycleTimeChartProps) {
  const labels = quarterLabels.map((q, idx) => getQuarterLabel(q, idx, currentQuarterIndex, isCurrentQuarter));

  const allTotals = quarterLabels.map(label => {
    const qData = cycleTimeData[label];
    if (!qData) return [];
    return Object.values(qData).flatMap(proj => proj.total);
  });

  return (
    <Line
      data={{
        labels,
        datasets: [{
          label: 'Median Cycle Time (days)',
          data: allTotals.map(v => calculatePercentile(v, 50)),
          borderColor: '#3b82f6',
          backgroundColor: '#3b82f620',
          tension: 0.3,
          fill: true,
          pointRadius: 5,
          pointBackgroundColor: '#3b82f6',
          spanGaps: true,
          segment: {
            borderDash: (ctx: any) => {
              if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) {
                return [5, 5];
              }
              return [];
            },
          },
        }],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: 'Business Days' } },
        },
      }}
    />
  );
}
