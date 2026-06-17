import { useCallback } from 'react';
import type { TableRowData } from '../types';
import { useTableSort } from '../hooks/useTableSort';

interface FullTableProps {
  tableRows: TableRowData[];
  quarterLabels: string[];
  hasScoring: boolean;
  hasJira: boolean;
}

export function FullTable({ tableRows, quarterLabels, hasScoring, hasJira }: FullTableProps) {
  const getCellValue = useCallback((row: TableRowData, colIdx: number): string | number => {
    if (colIdx === 0) return row.name;

    const numQuarters = quarterLabels.length;
    let offset = 1;

    // PRs+MRs columns
    if (colIdx < offset + numQuarters) {
      return row.quarters[colIdx - offset].total;
    }
    offset += numQuarters;

    // Growth column
    if (colIdx === offset) {
      const raw = row.growth.replace(/[^-\d.]/g, '');
      return raw ? parseFloat(raw) : 0;
    }
    offset += 1;

    // GH PRs columns
    if (colIdx < offset + numQuarters) {
      return row.quarters[colIdx - offset].github_prs;
    }
    offset += numQuarters;

    // GL MRs columns
    if (colIdx < offset + numQuarters) {
      return row.quarters[colIdx - offset].gitlab_mrs;
    }
    offset += numQuarters;

    // Reviews columns
    if (colIdx < offset + numQuarters) {
      return row.quarters[colIdx - offset].reviews;
    }
    offset += numQuarters;

    // Merge time columns
    if (colIdx < offset + numQuarters) {
      return row.quarters[colIdx - offset].merge_time ?? 0;
    }
    offset += numQuarters;

    // Story points columns (if scoring)
    if (hasScoring && colIdx < offset + numQuarters) {
      return row.quarters[colIdx - offset].story_points;
    }
    offset += numQuarters;

    // Review complexity columns (if scoring)
    if (hasScoring && colIdx < offset + numQuarters) {
      return row.quarters[colIdx - offset].review_story_points;
    }
    if (hasScoring) offset += numQuarters;

    // Verified bugs columns (if jira)
    if (hasJira && colIdx < offset + numQuarters) {
      return row.quarters[colIdx - offset].verified_bugs;
    }

    return 0;
  }, [quarterLabels.length, hasScoring, hasJira]);

  const { sortedRows, sortCol, sortAsc, handleSort } = useTableSort(tableRows, getCellValue);

  const headers: { label: string; isNum: boolean }[] = [
    { label: 'Engineer', isNum: false },
  ];
  for (const ql of quarterLabels) {
    headers.push({ label: `PRs+MRs ${ql}`, isNum: true });
  }
  headers.push({ label: 'Growth', isNum: true });
  for (const ql of quarterLabels) {
    headers.push({ label: `GH PRs ${ql}`, isNum: true });
  }
  for (const ql of quarterLabels) {
    headers.push({ label: `GL MRs ${ql}`, isNum: true });
  }
  for (const ql of quarterLabels) {
    headers.push({ label: `Reviews ${ql}`, isNum: true });
  }
  for (const ql of quarterLabels) {
    headers.push({ label: `Merge days ${ql}`, isNum: true });
  }
  if (hasScoring) {
    for (const ql of quarterLabels) {
      headers.push({ label: `Complexity ${ql}`, isNum: true });
    }
    for (const ql of quarterLabels) {
      headers.push({ label: `Review Cx ${ql}`, isNum: true });
    }
  }
  if (hasJira) {
    for (const ql of quarterLabels) {
      headers.push({ label: `Bugs SP ${ql}`, isNum: true });
    }
  }

  function renderRow(row: TableRowData) {
    const cells: (string | number)[] = [];
    for (const qm of row.quarters) cells.push(qm.total);
    cells.push(row.growth);
    for (const qm of row.quarters) cells.push(qm.github_prs);
    for (const qm of row.quarters) cells.push(qm.gitlab_mrs);
    for (const qm of row.quarters) cells.push(qm.reviews);
    for (const qm of row.quarters) cells.push(qm.merge_time !== null ? qm.merge_time : '-');
    if (hasScoring) {
      for (const qm of row.quarters) cells.push(qm.story_points);
      for (const qm of row.quarters) cells.push(qm.review_story_points);
    }
    if (hasJira) {
      for (const qm of row.quarters) cells.push(qm.verified_bugs);
    }

    return (
      <tr key={row.name}>
        <td><strong>{row.name}</strong></td>
        {cells.map((val, i) => (
          <td key={i} className="num">{val}</td>
        ))}
      </tr>
    );
  }

  const sortArrow = (colIdx: number) => {
    if (sortCol !== colIdx) return '';
    return sortAsc ? '▲' : '▼';
  };

  return (
    <div data-testid="tab-table">
      <div className="chart-card full">
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table" data-testid="main-table">
            <thead>
              <tr>
                {headers.map((h, i) => (
                  <th
                    key={i}
                    data-type={h.isNum ? 'num' : undefined}
                    onClick={() => handleSort(i)}
                  >
                    {h.label} <span className="sort-arrow">{sortArrow(i)}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRows.map(renderRow)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
