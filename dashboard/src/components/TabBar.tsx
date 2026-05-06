interface TabBarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const TABS = [
  { id: 'team', label: 'Overall Team View' },
  { id: 'overview', label: 'Detailed View' },
  { id: 'table', label: 'Full Table' },
  { id: 'config', label: 'Configuration' },
];

export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  return (
    <div className="tabs" data-testid="tab-bar">
      {TABS.map(tab => (
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
