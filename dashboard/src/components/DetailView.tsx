import type { CycleTimeQuarterData, QuarterData } from '../types';
import { useEngineerFilter } from '../hooks/useEngineerFilter';
import { ActivityTypeChart } from './ActivityTypeChart';
import { ChartCard } from './ChartCard';
import { DetailLineChart } from './DetailLineChart';
import { EngineerFilter } from './EngineerFilter';
import { ProjectCycleTimeChart } from './ProjectCycleTimeChart';

interface DetailViewProps {
  quarters: QuarterData[];
  names: string[];
  colors: string[];
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
  hasScoring: boolean;
  hasJira: boolean;
  hasCycleTime: boolean;
  cycleTimeData: Record<string, CycleTimeQuarterData>;
  cycleTimeProjects: string[];
  hasActivityTypes: boolean;
  activityTypeNames: string[];
  quarterLabels: string[];
}

export function DetailView({ quarters, names, colors, currentQuarterIndex, isCurrentQuarter, hasScoring, hasJira, hasCycleTime, cycleTimeData, cycleTimeProjects, hasActivityTypes, activityTypeNames, quarterLabels }: DetailViewProps) {
  const { selected, toggle, selectAll, clearAll } = useEngineerFilter(names);

  const commonProps = {
    quarters,
    names,
    colors,
    selectedEngineers: selected,
    currentQuarterIndex,
    isCurrentQuarter,
  };

  return (
    <div data-testid="tab-overview">
      <EngineerFilter
        names={names}
        colors={colors}
        selected={selected}
        onToggle={toggle}
        onSelectAll={selectAll}
        onClearAll={clearAll}
      />
      <div className="chart-row">
        <ChartCard
          title="PRs + MRs per Quarter"
          tooltip="GitHub PRs and GitLab MRs merged per engineer during the quarter."
          testId="chart-prs-trend"
        >
          <DetailLineChart
            {...commonProps}
            getValues={q => q.gh_prs.map((v, i) => v + q.gl_mrs[i])}
          />
        </ChartCard>
        <ChartCard
          title="Code Reviews per Quarter"
          tooltip="Merged PRs reviewed per engineer during the quarter. Excludes self-reviews."
          testId="chart-reviews-trend"
        >
          <DetailLineChart
            {...commonProps}
            getValues={q => q.reviews}
          />
        </ChartCard>
      </div>
      <div className="chart-row">
        {hasScoring && (
          <ChartCard
            title="Complexity per Quarter"
            tooltip="Complexity score per engineer. Each merged PR is sized XS–XL by taking the max of: diff size, files changed, review friction, and merge time signals. Size labels on PRs override the calculation."
            testId="chart-complexity-trend"
          >
            <DetailLineChart
              {...commonProps}
              getValues={q => q.sp}
              yAxisLabel="Complexity Points"
            />
          </ChartCard>
        )}
        {hasScoring && (
          <ChartCard
            title="Review Complexity per Quarter"
            tooltip="Complexity of merged PRs reviewed per engineer, scored identically to authored PRs."
            testId="chart-review-complexity-trend"
          >
            <DetailLineChart
              {...commonProps}
              getValues={q => q.review_sp}
              yAxisLabel="Complexity Points"
            />
          </ChartCard>
        )}
      </div>
      <div className="chart-row">
        {hasJira && (
          <ChartCard
            title="Verified Bugs SP per Quarter"
            tooltip="Story points of Jira bugs resolved as Done per engineer during the quarter."
            testId="chart-verified-bugs-trend"
          >
            <DetailLineChart
              {...commonProps}
              getValues={q => q.verified_bugs}
            />
          </ChartCard>
        )}
        {hasActivityTypes && (
          <ChartCard
            title="Story Points by Activity Type"
            tooltip="Per-engineer Jira story points broken down by activity type for the selected quarter. Issues without story points default to 2 SP."
            testId="chart-activity-type-breakdown"
          >
            <ActivityTypeChart
              quarters={quarters}
              names={names}
              colors={colors}
              selectedEngineers={selected}
              activityTypeNames={activityTypeNames}
              quarterLabels={quarterLabels}
            />
          </ChartCard>
        )}
      </div>
      <div className="chart-row">
        {hasCycleTime && (
          <ChartCard
            title="Team Cycle Time by Project (Business Days)"
            tooltip="Median total cycle time per project for issues assigned to or QA'd by team members."
            testId="chart-project-cycle-time"
          >
            <ProjectCycleTimeChart
              cycleTimeData={cycleTimeData}
              cycleTimeProjects={cycleTimeProjects}
              quarterLabels={quarterLabels}
              currentQuarterIndex={currentQuarterIndex}
              isCurrentQuarter={isCurrentQuarter}
            />
          </ChartCard>
        )}
        <ChartCard
          title="Median Merge Time per Quarter (days)"
          tooltip="Median days from PR/MR creation to merge per engineer for the quarter."
          testId="chart-merge-time-trend"
        >
          <DetailLineChart
            {...commonProps}
            getValues={q => q.merge_time}
            yAxisLabel="Days"
            yMax={20}
          />
        </ChartCard>
      </div>
    </div>
  );
}
