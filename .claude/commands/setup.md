Walk the user through setting up teamdash step by step. Run each check, report results, and help fix any issues before moving on.

## Step 1: Check prerequisites

Run these checks and report which pass/fail:
- `python3 --version` — needs 3.10+
- `node --version` — needs 18+
- `gh --version` — GitHub CLI must be installed
- `glab --version` — GitLab CLI (required only if using GitLab; ask the user if they use GitLab before failing on this)

If a required tool is missing, tell the user how to install it and stop.

## Step 2: Check GitHub authentication

- Run `gh auth status` — must be authenticated. If not, tell the user to run `! gh auth login`
- Check that the token scopes include `read:org` and `repo` (visible in `gh auth status` output). If missing, tell the user to run `! gh auth refresh -s read:org,repo` to add them — these are needed to fetch PR data across orgs.

## Step 3: Install dependencies

Run these commands from the project root:
```
pip install -e .
npm install --prefix dashboard
npm run build --prefix dashboard
```

If `npm run build` fails with "Cannot resolve entry module index.html", the `dashboard/index.html` file is missing. Create it with a standard Vite entry point (div#root, script src="/src/main.tsx").

If any other step fails, show the error and help debug.

## Step 4: Create config

Check if `config.json` exists. If it does, ask the user if they want to update it or keep it.

If creating a new config:
1. Ask the user for their **team name** as free text — just ask "What's your team name?", don't offer placeholder options.
2. Ask which **GitHub orgs** their team contributes to.
3. Ask if they use **GitLab** (and the URL if yes).
4. Ask if they use **Jira** (and the cloud ID / project keys if yes).
5. Ask for **engineers** — prompt the user to paste a list in this format (one per line):
   ```
   Name, github_username, gitlab_username
   ```
   Use a single free-text prompt for this, not AskUserQuestion with structured options. The gitlab_username is optional. Parse the response into the engineers array.
6. For **Jira users**: look up account IDs for each engineer. If the Atlassian MCP tools are available (check with `mcp__atlassian__lookupJiraAccountId`), use them to search by name. Otherwise, suggest the user open `https://<cloud_id>/rest/api/3/user/search?query=<name>` in their browser.
7. Write the completed config to `config.json`.
8. **Validate the config** by running:
   ```
   python3 -c "from teamdash.config import load_config; c = load_config('config.json'); print(f'Config OK: {len(c.engineers)} engineers')"
   ```
   If validation fails, show the error and fix the config.
9. If Jira is configured, check whether any engineers are **missing `jira_account_id`**. If so, warn the user: "These engineers will be silently skipped in Jira data fetches: [names]. You can add their Jira account IDs to config.json later."

## Step 5: Check auth for configured services

Now that config.json exists and we know which services are configured, verify authentication for each:

**GitLab** (if `gitlab` section exists in config):
- Run `glab auth status --hostname <gitlab_url>` using the URL from config.
- If not authenticated, guide the user through `! glab auth login --hostname <url>`.

**Jira** (if `jira` section exists in config):
- Check if `JIRA_EMAIL` env var is set: `echo $JIRA_EMAIL`
- Check if `JIRA_API_TOKEN` env var is set: `echo ${JIRA_API_TOKEN:+set}`
- If either is missing, tell the user:
  - Set `JIRA_EMAIL` to their Atlassian account email
  - Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens
  - Set `JIRA_API_TOKEN` to that token
  - Add both to their shell profile (`.bashrc` / `.zshrc`)
  - Then re-run `/setup` to verify
- If both are set, **actually test the credentials** by running:
  ```
  python3 -c "from teamdash.fetch_jira_api import check_auth; import os; ok = check_auth('CLOUD_ID', os.environ['JIRA_EMAIL'], os.environ['JIRA_API_TOKEN']); print('Jira auth: OK' if ok else 'Jira auth: FAILED')"
  ```
  (Replace `CLOUD_ID` with the actual cloud_id from config.) If the test fails, help debug — common causes are wrong email, expired token, or incorrect cloud_id.

## Done

Tell the user setup is complete. Explain the workflow:
- **Fetch + generate in one step:** run `/generate` or ask Claude to "generate the dashboard"
- **Fetch and generate separately:** `teamdash fetch` pulls data from GitHub/GitLab, `teamdash fetch-jira` pulls Jira data, `teamdash generate` builds the HTML from cached data
- **Include current quarter:** pass `--include-current` to include the current (incomplete) quarter in the dashboard

## Notes

- Be conversational and guide the user through each step
- Don't skip steps — run the checks even if things look fine
- If a step fails, help fix it before proceeding
