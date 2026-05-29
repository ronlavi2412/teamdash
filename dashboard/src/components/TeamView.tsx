import type { QuarterData } from '../types';
import { ChartCard } from './ChartCard';
import { TeamBarChart } from './TeamBarChart';
import { TeamLineChart } from './TeamLineChart';

interface TeamViewProps {
  quarters: QuarterData[];
  currentQuarterIndex: number;
  isCurrentQuarter: boolean;
  hasScoring: boolean;
  hasJira: boolean;
}

export function TeamView({ quarters, currentQuarterIndex, isCurrentQuarter, hasScoring, hasJira }: TeamViewProps) {
  return (
    <div data-testid="tab-team">
      <div className="chart-row">
        <ChartCard
          title="Total PRs + MRs per Quarter"
          tooltip="Sum of GitHub PRs and GitLab MRs merged during the quarter across all team members."
          testId="chart-team-prs"
        >
          <TeamBarChart
            quarters={quarters}
            getData={q => q.gh_prs.reduce((a, b) => a + b, 0) + q.gl_mrs.reduce((a, b) => a + b, 0)}
            color="#3b82f6"
            borderColor="#2563eb"
            label="Total PRs + MRs"
            currentQuarterIndex={currentQuarterIndex}
            isCurrentQuarter={isCurrentQuarter}
          />
        </ChartCard>
        <ChartCard
          title="Total Reviews per Quarter"
          tooltip="Total merged PRs reviewed by team members during the quarter. Excludes self-reviews."
          testId="chart-team-reviews"
        >
          <TeamBarChart
            quarters={quarters}
            getData={q => q.reviews.reduce((a, b) => a + b, 0)}
            color="#8b5cf6"
            borderColor="#7c3aed"
            label="Total Reviews"
            currentQuarterIndex={currentQuarterIndex}
            isCurrentQuarter={isCurrentQuarter}
          />
        </ChartCard>
      </div>
      <div className="chart-row">
        {hasScoring && (
          <ChartCard
            title="Total Complexity per Quarter"
            tooltip="Sum of complexity scores across all team members. Each merged PR is sized XS–XL based on diff size, files changed, review friction, and merge time, then mapped to points (XS=2, S=5, M=8, L=13, XL=21)."
            testId="chart-team-sp"
          >
            <TeamBarChart
              quarters={quarters}
              getData={q => q.sp.reduce((a, b) => a + b, 0)}
              color="#10b981"
              borderColor="#059669"
              label="Total Complexity"
              yAxisLabel="Complexity Points"
              currentQuarterIndex={currentQuarterIndex}
              isCurrentQuarter={isCurrentQuarter}
            />
          </ChartCard>
        )}
        {hasScoring && (
          <ChartCard
            title="Total Review Complexity per Quarter"
            tooltip="Sum of complexity scores for merged PRs reviewed by team members, scored the same way as authored PRs."
            testId="chart-team-review-sp"
          >
            <TeamBarChart
              quarters={quarters}
              getData={q => q.review_sp.reduce((a, b) => a + b, 0)}
              color="#f59e0b"
              borderColor="#d97706"
              label="Total Reviews Complexity"
              yAxisLabel="Complexity Points"
              currentQuarterIndex={currentQuarterIndex}
              isCurrentQuarter={isCurrentQuarter}
            />
          </ChartCard>
        )}
        {hasJira && (
          <ChartCard
            title="Total Verified Bugs per Quarter"
            tooltip="Total Jira bugs resolved as Done during the quarter across all team members."
            testId="chart-team-verified-bugs"
          >
            <TeamBarChart
              quarters={quarters}
              getData={q => q.verified_bugs.reduce((a, b) => a + b, 0)}
              color="#ef4444"
              borderColor="#dc2626"
              label="Total Verified Bugs"
              currentQuarterIndex={currentQuarterIndex}
              isCurrentQuarter={isCurrentQuarter}
            />
          </ChartCard>
        )}
        <ChartCard
          title="Median Merge Time per Quarter (days)"
          tooltip="Median days from PR/MR creation to merge across all team members for the quarter."
          testId="chart-team-merge-time"
        >
          <TeamLineChart
            quarters={quarters}
            currentQuarterIndex={currentQuarterIndex}
            isCurrentQuarter={isCurrentQuarter}
          />
        </ChartCard>
      </div>
    </div>
  );
}
