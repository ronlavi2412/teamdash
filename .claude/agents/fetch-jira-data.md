---
name: fetch-jira-data
description: Fetch verified bug story point sums and activity type story point sums from Jira for each engineer per quarter and write a JSON file for use with teamdash --jira-data
---

# Fetch Jira Data

Collect per-engineer, per-quarter verified bug story point sums and activity type story point sums from Jira and write a JSON file that teamdash can consume via `--jira-data`.

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

3. **Query Jira for verified bugs (story points)** — for each engineer/quarter combination, use the Atlassian MCP tool `searchJiraIssuesUsingJql` with:
   - `cloudId`: the `jira.cloud_id` from config
   - `jql`: `issuetype = Bug AND resolution in (Done, "Done-Errata") AND resolutiondate >= "{quarter_start}" AND resolutiondate <= "{quarter_end}" AND cf[10470] = "{jira_account_id}" AND project in ({project_keys})`
   - The `cf[10470]` is the QA Contact custom field — bugs count for an engineer if they are the QA contact
   - `maxResults`: 100
   - `fields`: `["summary", "customfield_10028"]`

   The `customfield_10028` field is "Story Points". For each returned issue, read this field. **If story points is null, 0, or missing, use a default of 2.** Sum the story points for all issues to get the total for that engineer/quarter. If results exceed `maxResults`, paginate using `nextPageToken` until all issues are fetched. If an engineer has no `jira_account_id`, skip them (SP = 0).

4. **Discover the Activity Type and Story Points custom fields** — inspect a sample issue (use `getJiraIssue` with `fields: ["*all"]`) or use `getJiraIssueTypeMetaWithFields` to find:
   - The custom field ID for "Activity Type" (a dropdown field). The field name in JQL is typically `"Activity Type"` or `cf[XXXXX]`.
   - The field name for story points. Common names: `story_points` (Jira Cloud next-gen) or `customfield_10016` (Jira Cloud classic). Check which one is present on sample issues.

5. **Query Jira for activity type story point sums** — for each engineer/quarter/activity-type combination, query **all resolved issues** (not just bugs):
   - `jql`: `resolution in (Done, "Done-Errata") AND issuetype in (Bug, Task, Story, Vulnerability) AND resolutiondate >= "{quarter_start}" AND resolutiondate <= "{quarter_end}" AND (assignee = "{jira_account_id}" OR cf[10470] = "{jira_account_id}") AND "Activity Type" = "{activity_type_value}" AND project in ({project_keys})`
   - `maxResults`: 100
   - `fields`: `["summary", "story_points"]` (or the discovered story points field name)
   - If results exceed `maxResults`, paginate using `nextPageToken` until all issues are fetched.

   For each returned issue, read the story points field. **If story points is null, 0, or missing, use a default of 2.** Sum the story points for all issues in the result set to get the total for that activity type.

   The 6 activity type values are:
   - Associate Wellness & Development
   - Future Sustainability
   - Incidents & Support
   - Quality / Stability / Reliability
   - Security & Compliance
   - Product / Portfolio Work

6. **Build the JSON structure** (all values are story point sums — both verified bugs and activity types):
   ```json
   {
     "2025-Q3": {"Engineer Name": 5, "Other Engineer": 3},
     "2025-Q4": {"Engineer Name": 7, "Other Engineer": 1},
     "activity_types": {
       "2025-Q3": {
         "Engineer Name": {
           "Incidents & Support": 14,
           "Product / Portfolio Work": 8
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
- Activity type story point sums include all resolved issue types (Stories, Tasks, Bugs, etc.), not just bugs.
- Issues without story points (null, 0, or missing) default to 2 SP.
