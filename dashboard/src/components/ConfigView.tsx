import type { ConfigData } from '../types';

interface ConfigViewProps {
  config: ConfigData;
  hasScoring: boolean;
}

export function ConfigView({ config, hasScoring }: ConfigViewProps) {
  return (
    <div data-testid="tab-config">
      <div className="chart-row">
        <div className="chart-card">
          <h3>Data Sources</h3>
          <table className="data-table">
            <thead><tr><th>Source</th><th>Value</th></tr></thead>
            <tbody>
              {config.github_orgs.length > 0 && (
                <tr><td><strong>GitHub Organizations</strong></td><td>{config.github_orgs.join(', ')}</td></tr>
              )}
              {config.gitlab_url && (
                <tr><td><strong>GitLab Instance</strong></td><td>{config.gitlab_url}</td></tr>
              )}
              {config.github_orgs.length === 0 && !config.gitlab_url && (
                <tr><td colSpan={2}>No data sources configured</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="chart-card">
          <h3>Team Members</h3>
          <table className="data-table">
            <thead><tr><th>Name</th><th>GitHub</th><th>GitLab</th></tr></thead>
            <tbody>
              {config.engineers.map(eng => (
                <tr key={eng.name}>
                  <td>{eng.name}</td>
                  <td>{eng.github || '-'}</td>
                  <td>{eng.gitlab || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {hasScoring && config.scoring && (
        <div className="chart-card full">
          <h3>Scoring Configuration</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div>
              <h4 style={{ marginBottom: 8, fontSize: '0.9rem', color: 'var(--text-muted)' }}>Complexity Points per Size</h4>
              <table className="data-table">
                <thead><tr><th>Size</th><th>Points</th></tr></thead>
                <tbody>
                  {['XS', 'S', 'M', 'L', 'XL'].map(size => (
                    <tr key={size}>
                      <td>{size}</td>
                      <td>{config.scoring!.size_points[size] ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <h4 style={{ marginBottom: 8, fontSize: '0.9rem', color: 'var(--text-muted)' }}>Classification Thresholds</h4>
              <table className="data-table">
                <thead><tr><th>Signal</th><th>Thresholds (XS/S/M/L boundary)</th></tr></thead>
                <tbody>
                  <tr><td>Lines changed</td><td>{config.scoring!.diff_thresholds.join(', ')}</td></tr>
                  <tr><td>Files changed</td><td>{config.scoring!.file_thresholds.join(', ')}</td></tr>
                  <tr><td>Merge time (days)</td><td>{config.scoring!.merge_time_thresholds.join(', ')}</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
