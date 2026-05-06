import type { ReactNode } from 'react';

interface ChartCardProps {
  title: string;
  tooltip?: string;
  full?: boolean;
  children: ReactNode;
  testId?: string;
}

export function ChartCard({ title, tooltip, full, children, testId }: ChartCardProps) {
  return (
    <div className={`chart-card${full ? ' full' : ''}`} data-testid={testId}>
      <h3>
        {title}
        {tooltip && (
          <span className="chart-info" data-tooltip={tooltip}>i</span>
        )}
      </h3>
      <div className="chart-wrap">
        {children}
      </div>
    </div>
  );
}
