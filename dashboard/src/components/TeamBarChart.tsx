import { Bar } from 'react-chartjs-2';
import type { QuarterData } from '../types';
import { createStripePattern, getQuarterLabel } from '../utils';

interface TeamBarChartProps {
  quarters: QuarterData[];
  getData: (q: QuarterData) => number;
  color: string;
  borderColor: string;
  label: string;
  yAxisLabel?: string;
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
}

export function TeamBarChart({
  quarters, getData, color, borderColor, label,
  yAxisLabel, currentQuarterIndex, isCurrentQuarter,
}: TeamBarChartProps) {
  const labels = quarters.map((q, idx) => getQuarterLabel(q.label, idx, currentQuarterIndex, isCurrentQuarter));
  const data = quarters.map(getData);

  return (
    <Bar
      data={{
        labels,
        datasets: [{
          label,
          data,
          backgroundColor: quarters.map((_, idx) =>
            idx === currentQuarterIndex && isCurrentQuarter
              ? createStripePattern(color)
              : color
          ),
          borderColor,
          borderWidth: 1,
          borderRadius: 4,
        }],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            ...(yAxisLabel ? { title: { display: true, text: yAxisLabel } } : { ticks: { stepSize: 10 } }),
          },
        },
      }}
    />
  );
}
