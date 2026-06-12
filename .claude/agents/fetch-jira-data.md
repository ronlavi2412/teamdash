---
name: fetch-jira-data
description: Fetch verified bug counts and activity type breakdown from Jira for each engineer per quarter and write a JSON file for use with teamdash --jira-data
---

# Fetch Jira Data

Collect per-engineer, per-quarter verified bug counts and activity type issue counts from Jira and write a JSON file that teamdash can consume via `--jira-data`.

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

3. **Query Jira for verified bugs** — for each engineer/quarter combination, use the Atlassian MCP tool `searchJiraIssuesUsingJql` with:
   - `cloudId`: the `jira.cloud_id` from config
   - `jql`: `issuetype = Bug AND resolution = Done AND resolutiondate >= "{quarter_start}" AND resolutiondate <= "{quarter_end}" AND (assignee = "{jira_account_id}" OR cf[10470] = "{jira_account_id}") AND project in ({project_keys})`
   - The `cf[10470]` is the QA Contact custom field — bugs count for an engineer if they are the assignee OR the QA contact
   - `maxResults`: 1 (we only need the `total` count)
   - `fields`: `["summary"]`

   The `total` field in the response gives the bug count. If an engineer has no `jira_account_id`, skip them (count = 0).

4. **Discover the Activity Type custom field** — inspect a sample issue or use `getJiraIssueTypeMetaWithFields` to find the custom field ID for "Activity Type" (a dropdown field). The field name in JQL is typically `"Activity Type"` or `cf[XXXXX]`.

5. **Query Jira for activity type counts** — for each engineer/quarter/activity-type combination, query **all resolved issues** (not just bugs):
   - `jql`: `resolution = Done AND resolutiondate >= "{quarter_start}" AND resolutiondate <= "{quarter_end}" AND (assignee = "{jira_account_id}" OR cf[10470] = "{jira_account_id}") AND "Activity Type" = "{activity_type_value}" AND project in ({project_keys})`
   - `maxResults`: 1 (we only need the `total` count)
   - `fields`: `["summary"]`

   The 6 activity type values are:
   - Associate Wellness & Development
   - Future Sustainability
   - Incidents & Support
   - Quality / Stability / Reliability
   - Security & Compliance
   - Product / Portfolio Work

6. **Build the JSON structure**:
   ```json
   {
     "2025-Q3": {"Engineer Name": 5, "Other Engineer": 3},
     "2025-Q4": {"Engineer Name": 7, "Other Engineer": 1},
     "activity_types": {
       "2025-Q3": {
         "Engineer Name": {
           "Incidents & Support": 3,
           "Product / Portfolio Work": 2
         }
       }
     }
   }
   ```

7. **Write the JSON file** — save to `jira-data.json` in the project root (or a path specified by the user).

8. **Report summary** — print a table of engineer x quarter bug counts, followed by a table of activity type counts.

## Usage

After running this agent, use the generated file with teamdash:
```bash
teamdash config/team-rlavi.yaml --jira-data jira-data.json
```

## Notes

- The Atlassian MCP uses browser OAuth — first-time users will get a browser auth prompt.
- If Jira returns exactly 100 results for `maxResults: 1`, the `total` field still reflects the true count.
- Engineer names in the JSON must exactly match the names in the team YAML config.
- Activity type counts include all resolved issue types (Stories, Tasks, Bugs, etc.), not just bugs.
