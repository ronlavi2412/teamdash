import type { ScriptableLineSegmentContext } from 'chart.js';
import { useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import type { QuarterData } from '../types';
import { calculateAverage, getQuarterLabel } from '../utils';

interface DetailLineChartProps {
  quarters: QuarterData[];
  names: string[];
  colors: string[];
  selectedEngineers: Set<string>;
  getValues: (q: QuarterData) => (number | null)[];
  yAxisLabel?: string;
  yMax?: number;
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
}

export function DetailLineChart({
  quarters, names, colors, selectedEngineers, getValues,
  yAxisLabel, yMax, currentQuarterIndex, isCurrentQuarter,
}: DetailLineChartProps) {
  const labels = quarters.map((q, idx) => getQuarterLabel(q.label, idx, currentQuarterIndex, isCurrentQuarter));

  const datasets = useMemo(() => {
    const engineerDatasets = names.map((name, i) => ({
      label: name,
      data: quarters.map(q => getValues(q)[i]),
      borderColor: colors[i],
      backgroundColor: colors[i] + '20',
      tension: 0.3,
      fill: false,
      pointRadius: 4,
      hidden: !selectedEngineers.has(name),
      spanGaps: true,
      segment: {
        borderDash: (ctx: ScriptableLineSegmentContext) => {
          if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) {
            return [5, 5];
          }
          return [];
        },
      },
    }));

    const avgDataset = {
      label: 'Team Average',
      data: quarters.map(q => {
        const values = getValues(q);
        const visible = values.filter((_, i) => selectedEngineers.has(names[i]));
        return calculateAverage(visible);
      }),
      borderColor: '#10b981',
      borderWidth: 2,
      borderDash: [5, 5] as number[],
      tension: 0.3,
      fill: false,
      pointRadius: 0,
      spanGaps: true,
      order: -1,
    };

    return [...engineerDatasets, avgDataset];
  }, [quarters, names, colors, selectedEngineers, getValues, currentQuarterIndex, isCurrentQuarter]);

  return (
    <Line
      data={{ labels, datasets }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { usePointStyle: true } } },
        scales: {
          y: {
            beginAtZero: true,
            ...(yMax !== undefined ? { max: yMax } : {}),
            ...(yAxisLabel ? { title: { display: true, text: yAxisLabel } } : { ticks: { stepSize: 5 } }),
          },
        },
      }}
    />
  );
}
