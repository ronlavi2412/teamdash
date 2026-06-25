Walk the user through setting up teamdash step by step. Run each check, report results, and help fix any issues before moving on.

## Step 1: Check prerequisites

Run these checks and report which pass/fail:
- `python3 --version` — needs 3.10+
- `node --version` — needs 18+
- `gh --version` — GitHub CLI must be installed

If anything is missing, tell the user how to install it and stop.

## Step 2: Check authentication

- Run `gh auth status` — must be authenticated. If not, tell the user to run `! gh auth login`
- If the user has GitLab in their config or mentions GitLab: run `glab auth status` and guide through `! glab auth login --hostname <url>` if needed

## Step 3: Install dependencies

Run these commands from the project root:
```
pip install -e .
npm install --prefix dashboard
npm run build --prefix dashboard
```

If any step fails, show the error and help debug.

## Step 4: Create config

Check if `config.json` exists. If not:
1. Copy `config.example.json` to `config.json`
2. Ask the user for their team name
3. Ask which GitHub orgs their team contributes to
4. Ask if they use GitLab (and the URL if yes)
5. Ask if they use Jira (and the cloud ID / project keys if yes)
6. Ask for each engineer's name, GitHub username, and optionally GitLab username
7. For Jira users: help find account IDs by querying `https://<cloud_id>/rest/api/3/user/search?query=<name>` — suggest the user open this in their browser, or if they have the Atlassian MCP tools available, use those to look up users
8. Write the completed config to `config.json`

If `config.json` already exists, ask the user if they want to update it or keep it.

## Step 5: Check Jira credentials (if Jira is configured)

If `config.json` has a `jira` section:
- Check if `JIRA_EMAIL` env var is set: `echo $JIRA_EMAIL`
- Check if `JIRA_API_TOKEN` env var is set: `echo ${JIRA_API_TOKEN:+set}`
- If either is missing, tell the user:
  - Set `JIRA_EMAIL` to their Atlassian account email
  - Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens
  - Set `JIRA_API_TOKEN` to that token
  - Add both to their shell profile (`.bashrc` / `.zshrc`)

## Done

Tell the user setup is complete. Mention they can generate their dashboard by asking Claude Code to "regenerate the dashboard".

## Notes

- Be conversational and guide the user through each step
- Don't skip steps — run the checks even if things look fine
- If a step fails, help fix it before proceeding
