export interface QuarterData {
  label: string;
  gh_prs: number[];
  gl_mrs: number[];
  reviews: number[];
  merge_time: (number | null)[];
  cp: number[];
  xl_count: number[];
  review_cp: number[];
  size_dist: SizeDistribution[];
  verified_bugs: number[];
  activity_types: Record<string, number>[];
}

export interface SizeDistribution {
  XS: number;
  S: number;
  M: number;
  L: number;
  XL: number;
}

export interface ConfigData {
  github_orgs: string[];
  gitlab_url: string | null;
  jira_cloud_id: string | null;
  jira_project_keys: string[];
  engineers: EngineerConfigData[];
  scoring: ScoringConfigData | null;
}

export interface EngineerConfigData {
  name: string;
  github: string | null;
  gitlab: string | null;
}

export interface ScoringConfigData {
  size_points: Record<string, number>;
  diff_thresholds: number[];
  file_thresholds: number[];
  merge_time_thresholds: number[];
}

export interface TableRowData {
  name: string;
  quarters: QuarterMetrics[];
  growth: string;
}

export interface QuarterMetrics {
  total: number;
  github_prs: number;
  gitlab_mrs: number;
  reviews: number;
  merge_time: number | null;
  complexity_points: number;
  review_complexity_points: number;
  verified_bugs: number;
  activity_type_counts: Record<string, number>;
}

export interface CycleTimePhases {
  dev: number[];
  build: number[];
  qe: number[];
  total: number[];
}

export type CycleTimeProjectData = Record<string, CycleTimePhases>;
export type CycleTimeQuarterData = Record<string, CycleTimeProjectData>;

export interface DashboardData {
  title: string;
  subtitle: string;
  generated: string;
  names: string[];
  colors: string[];
  quarters: QuarterData[];
  quarterLabels: string[];
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
  hasScoring: boolean;
  hasJira: boolean;
  hasCycleTime: boolean;
  hasActivityTypes: boolean;
  activityTypeNames: string[];
  cycleTimeData: Record<string, CycleTimeQuarterData>;
  cycleTimeProjects: string[];
  config: ConfigData;
  tableRows: TableRowData[];
  summaries?: Record<string, Record<string, string>>;
}
