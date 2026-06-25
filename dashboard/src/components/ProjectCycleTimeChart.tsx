import { useMemo, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import type { CycleTimePhases, CycleTimeQuarterData } from '../types';
import { calculatePercentile } from '../utils';

const PHASE_COLORS = {
  dev: '#3b82f6',
  build: '#f59e0b',
  qe: '#10b981',
};

interface ProjectCycleTimeChartProps {
  cycleTimeData: Record<string, CycleTimeQuarterData>;
  cycleTimeProjects: string[];
  quarterLabels: string[];
}

function mergePhases(a: CycleTimePhases, b: CycleTimePhases): CycleTimePhases {
  return {
    dev: [...a.dev, ...b.dev],
    build: [...a.build, ...b.build],
    qe: [...a.qe, ...b.qe],
    total: [...a.total, ...b.total],
  };
}

export function ProjectCycleTimeChart({
  cycleTimeData, cycleTimeProjects, quarterLabels,
}: ProjectCycleTimeChartProps) {
  const [selectedQuarter, setSelectedQuarter] = useState(quarterLabels.length - 1);
  const [selectedType, setSelectedType] = useState('All');

  const issueTypes = useMemo(() => {
    const types = new Set<string>();
    for (const qData of Object.values(cycleTimeData)) {
      for (const projTypes of Object.values(qData)) {
        for (const t of Object.keys(projTypes)) types.add(t);
      }
    }
    return [...types].sort();
  }, [cycleTimeData]);

  const chartData = useMemo(() => {
    const label = quarterLabels[selectedQuarter];
    const qData = cycleTimeData[label] || {};

    return {
      labels: cycleTimeProjects,
      datasets: (['dev', 'build', 'qe'] as const).map(phase => ({
        label: phase === 'dev' ? 'Dev' : phase === 'build' ? 'Build' : 'QE',
        data: cycleTimeProjects.map(proj => {
          const projTypes = qData[proj];
          if (!projTypes) return 0;

          let phases: CycleTimePhases;
          if (selectedType === 'All') {
            const empty: CycleTimePhases = { dev: [], build: [], qe: [], total: [] };
            phases = Object.values(projTypes).reduce(mergePhases, empty);
          } else {
            phases = projTypes[selectedType] || { dev: [], build: [], qe: [], total: [] };
          }
          return calculatePercentile(phases[phase], 50) ?? 0;
        }),
        backgroundColor: PHASE_COLORS[phase],
        borderRadius: 2,
      })),
    };
  }, [cycleTimeData, cycleTimeProjects, selectedQuarter, selectedType, quarterLabels]);

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
      x: { stacked: false },
      y: { beginAtZero: true, title: { display: true, text: 'Business Days (Median)' } },
    },
  }), []);

  const selectStyle = {
    padding: '4px 8px',
    borderRadius: 4,
    border: '1px solid #555',
    background: '#1e1e2e',
    color: '#e0e0e0',
    fontSize: 13,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: 8, flexShrink: 0, display: 'flex', gap: 8 }}>
        <select value={selectedQuarter} onChange={e => setSelectedQuarter(Number(e.target.value))} style={selectStyle}>
          {quarterLabels.map((label, i) => (
            <option key={i} value={i}>{label}</option>
          ))}
        </select>
        <select value={selectedType} onChange={e => setSelectedType(e.target.value)} style={selectStyle}>
          <option value="All">All Types</option>
          {issueTypes.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>
      <div style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <Bar data={chartData} options={chartOptions} />
      </div>
    </div>
  );
}
