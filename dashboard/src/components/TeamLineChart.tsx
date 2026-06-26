import type { ScriptableLineSegmentContext } from 'chart.js';
import { Line } from 'react-chartjs-2';
import type { QuarterData } from '../types';
import { calculateMedian, getQuarterLabel } from '../utils';

interface TeamLineChartProps {
  quarters: QuarterData[];
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
}

export function TeamLineChart({ quarters, currentQuarterIndex, isCurrentQuarter }: TeamLineChartProps) {
  const labels = quarters.map((q, idx) => getQuarterLabel(q.label, idx, currentQuarterIndex, isCurrentQuarter));

  return (
    <Line
      data={{
        labels,
        datasets: [{
          label: 'Median Merge Time (days)',
          data: quarters.map(q => calculateMedian(q.merge_time)),
          borderColor: '#ef4444',
          backgroundColor: '#ef444420',
          tension: 0.3,
          fill: true,
          pointRadius: 5,
          pointBackgroundColor: '#ef4444',
          spanGaps: true,
          segment: {
            borderDash: (ctx: ScriptableLineSegmentContext) => {
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
          y: { beginAtZero: true, max: 20, title: { display: true, text: 'Days' } },
        },
      }}
    />
  );
}
