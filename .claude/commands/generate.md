Generate the teamdash dashboard. Uses cached/existing data by default for speed.

IMPORTANT: Always run commands from the project root directory. Use `python3 -m teamdash` (not the `teamdash` binary) to ensure you're running the latest source.

## Step 1: Ask the user

Use AskUserQuestion with three questions:

1. "Include the current (in-progress) quarter?" — options: Yes / No (default No)
2. "Force refetch all data from scratch?" — options: Yes / No (default No)
3. "Generate engineer summaries?" — options: Yes / No (default No)

## Step 2: Check config

Verify `config.json` exists. If not, tell the user to run `/setup` first and stop.

Read `config.json` to check if it has a `jira` section.

## PTO data

Check if a PTO data file exists (XLSX or CSV). Look for files matching `pto*.xlsx`, `pto*.csv`, or `*Time_Off*.xlsx` in the project root and `~/Downloads/`. If found, add `--pto-data <path>` to the fetch commands below. If multiple files are found, ask the user which one to use.

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

If `data.json` already exists, skip fetching entirely — use it to build the dashboard. If a PTO file was found, inject PTO data into the existing data.json:

```
python3 -c "
from teamdash.pto import load_pto_data
from teamdash.config import load_config
import json
config = load_config('config.json')
pto = load_pto_data('<pto_file_path>', target_names=[e.name for e in config.engineers])
with open('data.json') as f:
    data = json.load(f)
names = data['names']
for q in data['quarters']:
    q['pto_days'] = [pto.get(q['label'], {}).get(n, 0) for n in names]
data['hasPto'] = True
with open('data.json', 'w') as f:
    json.dump(data, f, indent=2)
print('PTO data injected into data.json')
"
```

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

## Step 4: Handle summaries

If summaries=No, clear any previously stored summaries and continue to Step 5. Do not read summary input or generate narrative text:

```
python3 -m teamdash.summary_input clear data.json
```

If summaries=Yes, extract the small summary input and read **only** that file. Do not read the full `data.json` or the full PR list into the assistant context:

```
python3 -m teamdash.summary_input extract data.json -o /tmp/summary-input.json
```

1. Read `/tmp/summary-input.json`. It has the latest quarter, optional previous-quarter metrics, repo counts, up to 12 representative PR titles, and up to 15 representative Jira issues per active engineer. `merge_time` is in days. `verified_bugs` is team-wide, so do not attribute it to an engineer. `pto_days` is per engineer. Each `jira_issues` entry includes `key`, `summary`, `sp`, `type`, `activity_type`, and optionally `customer_cases` with `case_id` and `customer_name`.
2. Write a manager-friendly, sectioned summary per engineer, typically 350–500 words. Prioritize concrete detail and readability over a fixed word count. If there are no listed engineers, skip writing summaries and run the clear command above.
   - Use standalone `## Heading` blocks and `- Label: detail` bullet lists, with a blank line between headings, paragraphs, and lists. Keep each bullet on one line in the stored string. The dashboard renders these as headings and lists, not raw Markdown; do not use HTML or other Markdown formatting.
   - **Quarter at a glance**: Explain the main work themes and meaningful changes in 2–3 sentences. Distinguish observed metrics from inferred impact; do not assign a performance rating from counts alone.
   - **Delivery and technical highlights**: Separate output, repository breakdown, size mix, and merge time from 2–3 specific technical contributions. Reference PR titles or Jira keys and explain what changed. PR complexity points are distinct from Jira activity SP.
   - **Jira activity by category**: Give each recorded category its own labeled bullet with its SP total and 1–2 representative issue keys and plain-language descriptions. Use consistent order: Product / Portfolio Work; Quality / Stability / Reliability; Security & Compliance; Future Sustainability; Incidents & Support; Associate Wellness & Development. Omit categories absent from the data. State when a category has no representative issue; never invent one or relabel training/documentation as shipped features or security fixes.
   - **Customer-facing work**: Use one bullet per customer-linked issue, with its key, problem, and customer names. If none are listed, say that the extract contains no customer cases, not that the engineer had no customer-facing work. Shared Jira entries do not establish sole ownership, and issue titles alone do not prove completion.
   - **Reviews and availability**: Report review count and review complexity points, compare with the previous quarter, and give recorded PTO as availability context. Do not imply PTO caused a change or normalize productivity without evidence.
   - **Compared with {previous quarter}**: Give absolute before/after PR/MR, complexity, review, and merge-time figures, followed by a concise interpretation of the changed work mix. Avoid percentage changes from zero and unsupported explanations for slower merges.
   - Preserve the latest-quarter-only scope. Do not attribute team-wide verified bugs to individuals. State that Jira SP and PR/review complexity points are different estimates, not measures of quality.
3. Write the summaries dict as JSON to `/tmp/summaries.json`, structured as `{"Q2'26": {"Engineer Name": "summary text", ...}}` (latest quarter only).
4. Inject into data.json using a script (avoids triggering PostToolUse hooks on a data file):

```
python3 -c "
import json
with open('/tmp/summaries.json') as f:
    summaries = json.load(f)
with open('data.json') as f:
    d = json.load(f)
d['summaries'] = summaries
with open('data.json', 'w') as f:
    json.dump(d, f, indent=2)
print('Summaries injected into data.json')
"
```

## Step 5: Generate dashboard

Rebuild the frontend so the HTML uses the current Summaries tab behavior, then generate the dashboard:

```
npm run build --prefix dashboard
python3 -m teamdash generate data.json -o dashboard.html
```

When engineer summaries are included, the Summaries view opens on **Team Summary**, followed by the engineer tabs. The team comparison is derived automatically from the selected quarter and its predecessor in `data.json`; do not add a fake engineer or copy historical report figures into the summaries dictionary. It includes Cycle Time, Velocity, Resolution Time, work-mix changes, and metric-scope caveats. Verify that improvements and regressions are both visible, cycle time is labeled in business days, merge time is labeled in calendar days, and verified-bug SP is not presented as a bug count.

Tell the user their dashboard is ready at `dashboard.html`. Ask if they'd like to open it in the browser before running `xdg-open`.
