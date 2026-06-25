Fetch all data and generate the teamdash dashboard. Default is 4 quarters.

IMPORTANT: Always run commands from the project root directory. Use `python3 -m teamdash` (not the `teamdash` binary) to ensure you're running the latest source.

## Step 1: Ask about current quarter

Ask the user: "Include the current (in-progress) quarter?" Default is yes.

Based on the answer, set the `--include-current` flag for the commands below.

## Step 2: Check config

Verify `config.json` exists. If not, tell the user to run `/setup` first and stop.

Read `config.json` to check if it has a `jira` section.

## Step 3: Fetch Jira data (if configured)

If `config.json` has a `jira` section, run:
```
python3 -m python3 -m teamdash fetch-jira config.json -q 4 [--include-current] -o jira-data.json
```

If there's no `jira` section, skip this step.

## Step 4: Fetch GitHub/GitLab data

If Jira data was fetched:
```
python3 -m teamdash fetch config.json -q 4 [--include-current] --jira-data jira-data.json -o data.json
```

Otherwise:
```
python3 -m teamdash fetch config.json -q 4 [--include-current] -o data.json
```

## Step 5: Generate summaries

Follow the instructions in AGENTS.md under "Generating Summaries":
1. Read `data.json` to get all engineer metrics across quarters
2. For each engineer, write a concise narrative summary (2-3 paragraphs) for the last quarter covering PR/MR output, complexity trends, code review activity, merge time, verified bugs (if applicable), and activity type breakdown (if available). Skip engineers with no activity across all quarters.
3. Inject the summaries dict into `data.json` under the `"summaries"` key
4. Save the updated `data.json`

## Step 6: Generate dashboard

```
python3 -m teamdash generate data.json -o dashboard.html
```

Tell the user their dashboard is ready at `dashboard.html`.
