---
name: fetch-jira-bugs
description: Fetch verified bug counts from Jira for each engineer per quarter and write a JSON file for use with teamdash --jira-data
---

# Fetch Jira Verified Bugs

Collect per-engineer, per-quarter verified bug counts from Jira and write a JSON file that teamdash can consume via `--jira-data`.

## Steps

1. **Read team config** — load the team YAML config file (default: `config/team-rlavi.yaml`) to get:
   - `jira.cloud_id` — the Atlassian cloud instance
   - `jira.project_keys` — list of Jira project keys to query
   - Each engineer's `name` and `jira_account_id`

2. **Determine quarters** — calculate the last 4 quarters (matching teamdash defaults). Each quarter is:
   - Q1: Jan 1 – Mar 31
   - Q2: Apr 1 – Jun 30
   - Q3: Jul 1 – Sep 30
   - Q4: Oct 1 – Dec 31

3. **Query Jira for each engineer/quarter** — for each combination, use the Atlassian MCP tool `searchJiraIssuesUsingJql` with:
   - `cloudId`: the `jira.cloud_id` from config
   - `jql`: `issuetype = Bug AND resolution = Done AND resolutiondate >= "{quarter_start}" AND resolutiondate <= "{quarter_end}" AND (assignee = "{jira_account_id}" OR cf[10470] = "{jira_account_id}") AND project in ({project_keys})`
   - The `cf[10470]` is the QA Contact custom field — bugs count for an engineer if they are the assignee OR the QA contact
   - `maxResults`: 1 (we only need the `total` count)
   - `fields`: `["summary"]`

   The `total` field in the response gives the bug count. If an engineer has no `jira_account_id`, skip them (count = 0).

4. **Build the JSON structure**:
   ```json
   {
     "2025-Q3": {"Engineer Name": 5, "Other Engineer": 3},
     "2025-Q4": {"Engineer Name": 7, "Other Engineer": 1}
   }
   ```

5. **Write the JSON file** — save to `jira-bugs.json` in the project root (or a path specified by the user).

6. **Report summary** — print a table of engineer x quarter bug counts.

## Usage

After running this agent, use the generated file with teamdash:
```bash
teamdash config/team-rlavi.yaml --jira-data jira-bugs.json
```

## Notes

- The Atlassian MCP uses browser OAuth — first-time users will get a browser auth prompt.
- If Jira returns exactly 100 results for `maxResults: 1`, the `total` field still reflects the true count.
- Engineer names in the JSON must exactly match the names in the team YAML config.
