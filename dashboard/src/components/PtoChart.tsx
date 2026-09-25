import { useMemo, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import type { QuarterData } from '../types';

interface PtoChartProps {
  quarters: QuarterData[];
  names: string[];
  colors: string[];
  selectedEngineers: Set<string>;
  quarterLabels: string[];
}

export function PtoChart({
  quarters, names, colors, selectedEngineers, quarterLabels,
}: PtoChartProps) {
  const [selectedQuarter, setSelectedQuarter] = useState(quarters.length - 1);

  const filteredIndices = useMemo(() =>
    names.map((n, i) => ({ n, i })).filter(({ n }) => selectedEngineers.has(n)).map(({ i }) => i),
    [names, selectedEngineers],
  );

  const filteredNames = useMemo(() => filteredIndices.map(i => names[i]), [filteredIndices, names]);
  const filteredColors = useMemo(() => filteredIndices.map(i => colors[i]), [filteredIndices, colors]);

  const chartData = useMemo(() => {
    const q = quarters[selectedQuarter];
    return {
      labels: filteredNames,
      datasets: [{
        label: 'PTO Days',
        data: filteredIndices.map(i => q.pto_days[i] ?? 0),
        backgroundColor: filteredColors,
        borderRadius: 4,
      }],
    };
  }, [quarters, selectedQuarter, filteredIndices, filteredNames, filteredColors]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'PTO Days' } },
    },
  }), []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: 8, flexShrink: 0 }}>
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
      </div>
      <div style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <Bar data={chartData} options={chartOptions} />
      </div>
    </div>
  );
}
