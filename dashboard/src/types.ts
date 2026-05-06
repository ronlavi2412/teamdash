export interface QuarterData {
  label: string;
  gh_prs: number[];
  gl_mrs: number[];
  reviews: number[];
  merge_time: (number | null)[];
  sp: number[];
  xl_count: number[];
  review_sp: number[];
  size_dist: SizeDistribution[];
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
  story_points: number;
  review_story_points: number;
}

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
  config: ConfigData;
  tableRows: TableRowData[];
}
