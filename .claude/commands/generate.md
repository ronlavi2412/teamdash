Generate the teamdash dashboard. Uses cached/existing data by default for speed.

IMPORTANT: Always run commands from the project root directory. Use `python3 -m teamdash` (not the `teamdash` binary) to ensure you're running the latest source.

## Step 1: Ask the user

Use AskUserQuestion with two questions:

1. "Include the current (in-progress) quarter?" — options: Yes / No (default No)
2. "Force refetch all data from scratch?" — options: Yes / No (default No)

## Step 2: Check config

Verify `config.json` exists. If not, tell the user to run `/setup` first and stop.

Read `config.json` to check if it has a `jira` section.

## Step 3: Fetch data (based on answers)

### If force=Yes:

Refetch everything from scratch.

If Jira is configured:
```
python3 -m teamdash fetch-jira config.json -q 4 [--include-current] -o jira-data.json
python3 -m teamdash fetch config.json -q 4 --no-cache [--include-current] --jira-data jira-data.json -o data.json
```

Without Jira:
```
python3 -m teamdash fetch config.json -q 4 --no-cache [--include-current] -o data.json
```

Add `--include-current` only if current=Yes.

### If current=Yes (but not force):

Fetch with `--include-current`. The cache automatically serves past quarters — only the current quarter is fetched fresh.

If Jira is configured:
```
python3 -m teamdash fetch-jira config.json -q 4 --include-current -o jira-data.json
python3 -m teamdash fetch config.json -q 4 --include-current --jira-data jira-data.json -o data.json
```

Without Jira:
```
python3 -m teamdash fetch config.json -q 4 --include-current -o data.json
```

### If both No (default):

If `data.json` already exists, skip fetching entirely — just regenerate summaries and dashboard.

If `data.json` does not exist, fetch completed quarters only:

If Jira is configured:
```
python3 -m teamdash fetch-jira config.json -q 4 -o jira-data.json
python3 -m teamdash fetch config.json -q 4 --jira-data jira-data.json -o data.json
```

Without Jira:
```
python3 -m teamdash fetch config.json -q 4 -o data.json
```

## Step 3.5: Validate fetched data

After fetching, check for engineers with zero PR/MR/review contributions in the most recent quarter:

```
python3 -c "
import json
with open('data.json') as f:
    d = json.load(f)
names = d['names']
last_q = d['quarters'][-1]
label = d['quarterLabels'][-1]
flagged = []
for i, name in enumerate(names):
    prs = last_q['gh_prs'][i]
    mrs = last_q['gl_mrs'][i]
    reviews = last_q['reviews'][i]
    has_jira = last_q.get('verified_bugs', 0) > 0 or bool(last_q.get('activity_types', [{}])[i])
    if prs == 0 and mrs == 0 and reviews == 0:
        flagged.append({'name': name, 'has_jira': has_jira})
if flagged:
    for f in flagged:
        tag = 'Jira-only' if f['has_jira'] else 'no activity'
        print(f'{f[\"name\"]} ({tag})')
else:
    print('ALL_OK')
"
```

If `ALL_OK`, proceed to Step 4.

If engineers are flagged, **verify their usernames actually exist** before prompting:

- **GitHub**: Run `gh api users/{username}` for each flagged engineer's GitHub username. A 404 means the username is wrong.
- **GitLab**: Run `glab api "users?search={username}" --hostname {gitlab_url}` and check if the expected user appears.

For any username that doesn't exist:
- Search for the correct one: `gh api "search/users?q={engineer_name}" --jq '.items[:5] | .[] | "\(.login) - \(.html_url)"'`
- If a likely match is found, suggest it to the user.

Then use AskUserQuestion to show the findings:
- "These engineers have 0 PRs/MRs in {quarter}: {list with details}. {Username} doesn't exist on GitHub — did you mean {suggestion}? What would you like to do?"
- Options: "Fix config and re-fetch" / "Continue anyway"

If "Fix config and re-fetch": update the username(s) in `config.json`, then go back to Step 3 to re-fetch data for the affected engineers.
If "Continue anyway": proceed to Step 4.

## Step 4: Generate summaries

Follow the instructions in AGENTS.md under "Generating Summaries":
1. Read `data.json` to get all engineer metrics across quarters. The file includes a `pr_details` field with per-engineer per-quarter PR lists containing title, repo, size, and source.
   The quarter object fields are: `gh_prs`, `gl_mrs`, `reviews`, `merge_time` (hours), `cp` (complexity points), `xl_count`, `review_cp`, `size_dist` (object with XS/S/M/L/XL counts), `verified_bugs` (team-wide total, single number), `activity_types` (per-engineer array of objects mapping category to count), `pr_details` (list of objects with title/repo/size/source).
2. For the most recent quarter only, and for each engineer, write a comprehensive narrative summary (up to 3 paragraphs) that goes beyond raw numbers:
   - **Paragraph 1 — What they worked on:** Group PRs by repo to describe which projects the engineer contributed to. Mention dominant themes from PR titles (bug fixes, new features, refactoring, i18n, CI/CD, testing, etc.). Highlight 1-2 notable or impactful PRs by name (especially XL-sized ones).
   - **Paragraph 2 — Output and complexity:** Summarize quantitative metrics — total PRs/MRs, complexity points, size distribution, merge time. Compare against the previous quarter where available.
   - **Paragraph 3 — Reviews and Jira activity:** Cover code review volume and review complexity points. Include activity type breakdown (if available from Jira). Note any quarter-over-quarter trends.
   - Skip engineers with no activity in that quarter.
3. Inject the summaries dict into `data.json` under the `"summaries"` key, structured as `{"Q2'26": {"Engineer Name": "summary text", ...}}` (latest quarter only)
4. Save the updated `data.json`

## Step 5: Generate dashboard

```
python3 -m teamdash generate data.json -o dashboard.html
```

Tell the user their dashboard is ready at `dashboard.html`. Ask if they'd like to open it in the browser before running `xdg-open`.
