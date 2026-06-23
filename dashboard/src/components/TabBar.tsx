interface TabBarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  hasSummaries?: boolean;
}

const BASE_TABS = [
  { id: 'team', label: 'Overall Team View' },
  { id: 'overview', label: 'Detailed View' },
  { id: 'table', label: 'Full Table' },
  { id: 'config', label: 'Configuration' },
];

export function TabBar({ activeTab, onTabChange, hasSummaries }: TabBarProps) {
  const tabs = hasSummaries
    ? [...BASE_TABS, { id: 'summaries', label: 'Summaries' }]
    : BASE_TABS;

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
