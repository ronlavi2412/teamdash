import type { CycleTimeQuarterData, DashboardData, QuarterData } from './types';
import { calculateMedian, calculatePercentile } from './utils';

const sum = (values: number[]) => values.reduce((total, value) => total + value, 0);
const formatNumber = (value: number) => value.toLocaleString('en-US', { maximumFractionDigits: 1 });

function change(before: number, after: number, duration = false): string {
  if (before === after) return 'unchanged';
  if (before === 0) return 'no percentage comparison from a zero baseline';
  const percent = formatNumber(Math.abs((after - before) / before * 100));
  const direction = duration
    ? (after < before ? 'faster' : 'longer')
    : (after > before ? 'increase' : 'decrease');
  return `${percent}% ${direction}`;
}

function comparison(before: number | null, after: number | null, unit = '', duration = false): string {
  const beforeText = before === null ? 'not available' : `${formatNumber(before)}${unit}`;
  const afterText = after === null ? 'not available' : `${formatNumber(after)}${unit}`;
  const values = `${beforeText} → ${afterText}`;
  return before === null || after === null
    ? `${values} (insufficient data for comparison)`
    : `${values} (${change(before, after, duration)})`;
}

function cycleTimes(data: CycleTimeQuarterData, project?: string, issueType?: string): number[] {
  const totals: number[] = [];
  const projects = project ? (data[project] ? [data[project]] : []) : Object.values(data);
  for (const types of projects) {
    for (const [type, phases] of Object.entries(types)) {
      if (!issueType || type === issueType) totals.push(...phases.total);
    }
  }
  return totals;
}

function activityTotals(quarter: QuarterData): Record<string, number> {
  const totals: Record<string, number> = {};
  for (const activities of quarter.activity_types) {
    for (const [category, points] of Object.entries(activities)) {
      totals[category] = (totals[category] ?? 0) + points;
    }
  }
  return totals;
}

export function buildTeamSummary(data: DashboardData, selectedQuarter: string): string {
  const index = data.quarterLabels.indexOf(selectedQuarter);
  if (index < 1 || !data.quarters[index] || !data.quarters[index - 1]) {
    return '## Team comparison\n\nTwo consecutive quarters are needed for a team comparison. No earlier quarter is available for the selected period.';
  }
  const previousLabel = data.quarterLabels[index - 1];
  const previous = data.quarters[index - 1];
  const current = data.quarters[index];
  const previousCycles = data.cycleTimeData[previousLabel] ?? {};
  const currentCycles = data.cycleTimeData[selectedQuarter] ?? {};
  const previousActivity = activityTotals(previous);
  const currentActivity = activityTotals(current);
  const previousSP = sum(Object.values(previousActivity));
  const currentSP = sum(Object.values(currentActivity));
  const previousOutput = sum(previous.gh_prs) + sum(previous.gl_mrs);
  const currentOutput = sum(current.gh_prs) + sum(current.gl_mrs);
  const previousBugTimes = cycleTimes(previousCycles, undefined, 'Bug');
  const currentBugTimes = cycleTimes(currentCycles, undefined, 'Bug');
  const previousBugMedian = calculatePercentile(previousBugTimes, 50);
  const currentBugMedian = calculatePercentile(currentBugTimes, 50);

  const cycleLine = (label: string, project?: string, issueType?: string) => {
    const before = cycleTimes(previousCycles, project, issueType);
    const after = cycleTimes(currentCycles, project, issueType);
    return `- ${label}: ${comparison(calculatePercentile(before, 50), calculatePercentile(after, 50), ' business days', true)}. Completed issues with cycle-time data: ${before.length} → ${after.length}.`;
  };
  const cycleLines = ['Story', 'Bug', 'Vulnerability'].map(type => cycleLine(`${type} median, all projects`, undefined, type));
  const projects = [...new Set([...Object.keys(previousCycles), ...Object.keys(currentCycles)])].sort();
  cycleLines.push(...projects.map(project => cycleLine(`${project} median, all tracked types`, project)));
  cycleLines.push(`- Merge time, median of engineer medians: ${comparison(calculateMedian(previous.merge_time), calculateMedian(current.merge_time), ' calendar days', true)}. Matches the team chart; not the median of all individual PRs.`);

  const velocity = [`- PRs/MRs: ${comparison(previousOutput, currentOutput)} merged changes.`];
  if (data.hasScoring) {
    velocity.push(`- Authored complexity points: ${comparison(sum(previous.cp), sum(current.cp))}. These are estimated PR/MR size, not Jira story points.`);
  }
  if (data.hasActivityTypes) {
    velocity.push(`- Jira activity SP, engineer rollup: ${comparison(previousSP, currentSP, ' SP')}. Includes the recorded activity categories; shared issues can contribute to multiple engineers.`);
  }
  velocity.push(`- Reviews: ${comparison(sum(previous.reviews), sum(current.reviews))}.`);
  if (data.hasScoring) velocity.push(`- Review complexity points: ${comparison(sum(previous.review_cp), sum(current.review_cp))}.`);

  const resolution = [
    `- Bug resolution cycle, all projects: ${comparison(previousBugMedian, currentBugMedian, ' business days', true)} from first In Progress to resolution. Same Bug metric as Cycle Time, not a separate improvement.`,
  ];
  if (data.hasJira) {
    resolution.push(`- Verified-bug story points, configured Jira projects: ${comparison(previous.verified_bugs, current.verified_bugs, ' SP')}. This is project-wide story-point throughput, not the number of bugs resolved by the team. A verified-bug count is not stored.`);
  } else {
    resolution.push('- Verified-bug throughput: no Jira verified-bug story-point data is available.');
  }
  resolution.push('A shorter median means the measured completed bugs resolved faster. It does not describe unresolved backlog or prove why the time changed; the issue mix and sample counts differ between quarters.');

  const overview = `The team merged ${formatNumber(currentOutput)} PRs/MRs versus ${formatNumber(previousOutput)} in ${previousLabel} (${change(previousOutput, currentOutput)}), and recorded ${formatNumber(sum(current.reviews))} reviews versus ${formatNumber(sum(previous.reviews))} (${change(sum(previous.reviews), sum(current.reviews))}). Bug cycle time was ${comparison(previousBugMedian, currentBugMedian, ' business days', true)}. Read the project-level results and merge time below alongside these gains: a team-wide median can improve while individual projects get slower.`;
  const parts = [
    `## ${previousLabel} to ${selectedQuarter}: quarter at a glance`, overview,
    '## Cycle Time', `Values below are ${previousLabel} → ${selectedQuarter}. Cycle time is the median for completed issues, in business days; sample counts make changes in coverage visible.`, cycleLines.join('\n'),
    '## Velocity', velocity.join('\n'),
    '## Resolution Time', resolution.join('\n\n'),
  ];
  if (data.hasActivityTypes) {
    const categories = [...new Set([...Object.keys(previousActivity), ...Object.keys(currentActivity)])].sort();
    const lines = categories.map(category => {
      const before = previousActivity[category] ?? 0;
      const after = currentActivity[category] ?? 0;
      const shares = previousSP > 0 && currentSP > 0
        ? ` Share of Jira activity SP: ${formatNumber(before / previousSP * 100)}% → ${formatNumber(after / currentSP * 100)}%.`
        : '';
      return `- ${category}: ${comparison(before, after, ' SP')}.${shares}`;
    });
    parts.push('## How the work mix changed', lines.join('\n'), 'These are recorded work categories, not a capacity or effort allocation. Increased product or security SP can coexist with higher delivery volume; the totals do not establish that this caused faster resolution.');
  }
  parts.push('## Reading this comparison', 'Both quarters use the current stored dataset, not a previously saved report. Refetches and changes in Jira coverage can revise historical figures. Merge-time changes use the rounded dashboard medians in calendar days, not hours. Jira activity SP, verified-bug SP, and PR complexity points have different scopes and should not be added together. Percentages are omitted for missing data or zero baselines.');
  return parts.join('\n\n');
}
