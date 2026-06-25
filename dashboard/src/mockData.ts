import type { DashboardData } from './types';

export const mockData: DashboardData = {
  title: "Test Team &mdash; 2024-Q4 to 2025-Q1",
  subtitle: "2 quarters (2024-10-01 to 2025-03-31)",
  generated: "2025-05-05 14:30",
  names: ["Alice", "Bob"],
  colors: ["#f59e0b", "#3b82f6"],
  quarterLabels: ["Q4'24", "Q1'25"],
  quarters: [
    {
      label: "Q4'24",
      gh_prs: [8, 2],
      gl_mrs: [4, 1],
      reviews: [6, 3],
      merge_time: [2.5, 3.1],
      sp: [35, 10],
      xl_count: [0, 0],
      review_sp: [18, 10],
      size_dist: [
        { XS: 2, S: 4, M: 3, L: 2, XL: 0 },
        { XS: 1, S: 1, M: 1, L: 0, XL: 0 },
      ],
      verified_bugs: [6, 2],
      activity_types: [
        { "Incidents & Support": 10, "Product / Portfolio Work": 18, "Quality / Stability / Reliability": 5, "Security & Compliance": 0, "Future Sustainability": 3, "Associate Wellness & Development": 0 },
        { "Incidents & Support": 2, "Product / Portfolio Work": 5, "Quality / Stability / Reliability": 0, "Security & Compliance": 3, "Future Sustainability": 0, "Associate Wellness & Development": 0 },
      ],
    },
    {
      label: "Q1'25",
      gh_prs: [10, 3],
      gl_mrs: [5, 2],
      reviews: [8, 4],
      merge_time: [1.8, 2.4],
      sp: [34, 16],
      xl_count: [1, 0],
      review_sp: [21, 13],
      size_dist: [
        { XS: 3, S: 3, M: 4, L: 2, XL: 1 },
        { XS: 1, S: 2, M: 1, L: 1, XL: 0 },
      ],
      verified_bugs: [10, 4],
      activity_types: [
        { "Incidents & Support": 14, "Product / Portfolio Work": 22, "Quality / Stability / Reliability": 8, "Security & Compliance": 3, "Future Sustainability": 0, "Associate Wellness & Development": 5 },
        { "Incidents & Support": 0, "Product / Portfolio Work": 10, "Quality / Stability / Reliability": 2, "Security & Compliance": 0, "Future Sustainability": 5, "Associate Wellness & Development": 0 },
      ],
    },
  ],
  currentQuarterIndex: -1,
  isCurrentQuarter: false,
  hasScoring: true,
  hasJira: true,
  hasCycleTime: true,
  hasActivityTypes: true,
  activityTypeNames: [
    "Associate Wellness & Development",
    "Future Sustainability",
    "Incidents & Support",
    "Product / Portfolio Work",
    "Quality / Stability / Reliability",
    "Security & Compliance",
  ],
  cycleTimeData: {
    "Q4'24": {
      "CNV": { dev: [3.0, 5.0, 8.0], build: [1.0, 2.0, 1.5], qe: [2.0, 4.0, 3.0], total: [6.0, 11.0, 12.5] },
      "MTV": { dev: [4.0, 6.0], build: [1.0, 2.5], qe: [3.0, 5.0], total: [8.0, 13.5] },
    },
    "Q1'25": {
      "CNV": { dev: [2.0, 4.0, 6.0, 3.0], build: [1.0, 1.5, 2.0, 1.0], qe: [2.0, 3.0, 4.0, 2.5], total: [5.0, 8.5, 12.0, 6.5] },
      "MTV": { dev: [5.0, 7.0], build: [2.0, 3.0], qe: [4.0, 6.0], total: [11.0, 16.0] },
    },
  },
  cycleTimeProjects: ["CNV", "MTV"],
  config: {
    github_orgs: ["test-org"],
    gitlab_url: "https://gitlab.example.com",
    jira_cloud_id: "redhat.atlassian.net",
    jira_project_keys: ["CNV", "MTV", "MTA", "OCPBUGS", "CONSOLE"],
    engineers: [
      { name: "Alice", github: "alice", gitlab: "alice_gl" },
      { name: "Bob", github: "bob", gitlab: "bob_gl" },
    ],
    scoring: {
      size_points: { XS: 2, S: 5, M: 8, L: 13, XL: 21 },
      diff_thresholds: [50, 200, 500, 1200],
      file_thresholds: [3, 8, 15, 30],
      merge_time_thresholds: [0.5, 2.0, 5.0, 10.0],
    },
  },
  tableRows: [
    {
      name: "Alice",
      quarters: [
        { total: 12, github_prs: 8, gitlab_mrs: 4, reviews: 6, merge_time: 2.5, story_points: 35, review_story_points: 18, verified_bugs: 6, activity_type_counts: { "Incidents & Support": 10, "Product / Portfolio Work": 18, "Quality / Stability / Reliability": 5 } },
        { total: 15, github_prs: 10, gitlab_mrs: 5, reviews: 8, merge_time: 1.8, story_points: 34, review_story_points: 21, verified_bugs: 10, activity_type_counts: { "Incidents & Support": 14, "Product / Portfolio Work": 22, "Quality / Stability / Reliability": 8 } },
      ],
      growth: "+25%",
    },
    {
      name: "Bob",
      quarters: [
        { total: 3, github_prs: 2, gitlab_mrs: 1, reviews: 3, merge_time: 3.1, story_points: 10, review_story_points: 10, verified_bugs: 2, activity_type_counts: { "Incidents & Support": 2, "Security & Compliance": 3 } },
        { total: 5, github_prs: 3, gitlab_mrs: 2, reviews: 4, merge_time: 2.4, story_points: 16, review_story_points: 13, verified_bugs: 4, activity_type_counts: { "Product / Portfolio Work": 10, "Quality / Stability / Reliability": 2 } },
      ],
      growth: "+67%",
    },
  ],
};
