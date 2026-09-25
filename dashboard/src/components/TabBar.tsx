interface TabBarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  hasSummaries: boolean;
}

const TABS = [
  { id: 'team', label: 'Overall Team View' },
  { id: 'overview', label: 'Detailed View' },
  { id: 'summaries', label: 'Summaries' },
  { id: 'table', label: 'Full Table' },
  { id: 'config', label: 'Configuration' },
];

export function TabBar({ activeTab, onTabChange, hasSummaries }: TabBarProps) {
  const tabs = hasSummaries ? TABS : TABS.filter(tab => tab.id !== 'summaries');

  return (
    <div className="tabs" data-testid="tab-bar">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`tab${activeTab === tab.id ? ' active' : ''}`}
          onClick={() => onTabChange(tab.id)}
          data-testid={`tab-${tab.id}`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
