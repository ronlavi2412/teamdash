from __future__ import annotations

import json

from teamdash.fetch_jira import JiraData, load_jira_data


class TestLoadJiraData:
    def test_valid_file(self, tmp_path):
        f = tmp_path / "jira.json"
        data = {"2025-Q1": {"Alice": 5, "Bob": 3}}
        f.write_text(json.dumps(data))
        result = load_jira_data(str(f))
        assert isinstance(result, JiraData)
        assert result.bugs == data
        assert result.activity_types == {}

    def test_missing_file_returns_none(self, tmp_path):
        result = load_jira_data(str(tmp_path / "nonexistent.json"))
        assert result is None

    def test_invalid_json_returns_none(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json")
        result = load_jira_data(str(f))
        assert result is None

    def test_non_dict_returns_none(self, tmp_path):
        f = tmp_path / "list.json"
        f.write_text(json.dumps([1, 2, 3]))
        result = load_jira_data(str(f))
        assert result is None

    def test_empty_dict(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("{}")
        result = load_jira_data(str(f))
        assert isinstance(result, JiraData)
        assert result.bugs == {}
        assert result.activity_types == {}

    def test_nested_structure(self, tmp_path):
        f = tmp_path / "jira.json"
        data = {
            "2025-Q1": {"Alice": 5},
            "2025-Q2": {"Alice": 7, "Bob": 2},
        }
        f.write_text(json.dumps(data))
        result = load_jira_data(str(f))
        assert result.bugs["2025-Q2"]["Bob"] == 2

    def test_with_activity_types(self, tmp_path):
        f = tmp_path / "jira.json"
        data = {
            "2025-Q1": {"Alice": 5},
            "activity_types": {
                "2025-Q1": {
                    "Alice": {
                        "Incidents & Support": 3,
                        "Product / Portfolio Work": 2,
                    }
                }
            },
        }
        f.write_text(json.dumps(data))
        result = load_jira_data(str(f))
        assert result.bugs == {"2025-Q1": {"Alice": 5}}
        assert result.activity_types["2025-Q1"]["Alice"]["Incidents & Support"] == 3

    def test_activity_types_excluded_from_bugs(self, tmp_path):
        f = tmp_path / "jira.json"
        data = {
            "2025-Q1": {"Alice": 5},
            "activity_types": {"2025-Q1": {"Alice": {"Bug": 1}}},
        }
        f.write_text(json.dumps(data))
        result = load_jira_data(str(f))
        assert "activity_types" not in result.bugs
