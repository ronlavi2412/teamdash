---
name: fetch-jira-data
description: "DEPRECATED: Use `teamdash fetch-jira` CLI command instead. This agent previously fetched Jira data via MCP tools but has been replaced by a deterministic Python script with proper pagination."
---

# Fetch Jira Data (Deprecated)

This agent is **deprecated**. Use the `teamdash fetch-jira` CLI command instead, which fetches Jira data directly via the REST API with proper pagination.

## Usage

```bash
# Set credentials
export JIRA_EMAIL=your-email@redhat.com
export JIRA_API_TOKEN=your-token  # from https://id.atlassian.com/manage-profile/security/api-tokens

# Fetch Jira data
teamdash fetch-jira config/team-rlavi.yaml --include-current -o jira-data.json

# Then generate the dashboard
teamdash config/team-rlavi.yaml --jira-data jira-data.json --include-current
```

See `teamdash/fetch_jira_api.py` for the implementation.
