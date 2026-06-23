from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from teamdash.fetch_github import (
    _gh_search_count,
    _gh_search_items,
    _orgs_query,
    _run_gh,
    check_auth,
    fetch_merge_times,
    fetch_pr_details,
    fetch_prs,
    fetch_reviews,
)


@pytest.fixture(autouse=True)
def reset_throttle():
    import teamdash.fetch_github as mod
    mod._request_times.clear()
    yield
    mod._request_times.clear()


class TestOrgsQuery:
    def test_single_org(self):
        assert _orgs_query(["myorg"]) == "org:myorg"

    def test_multiple_orgs(self):
        result = _orgs_query(["kubevirt", "kubevirt-ui", "openshift"])
        assert result == "org:kubevirt+org:kubevirt-ui+org:openshift"


class TestRunGh:
    def test_success(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout='{"ok": true}')
        with patch("teamdash.fetch_github.subprocess.run", return_value=fake):
            result = _run_gh(["gh", "api", "/test"])
        assert result.returncode == 0

    def test_retries_on_rate_limit(self):
        fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="403 rate limit exceeded")
        success = subprocess.CompletedProcess(args=[], returncode=0, stdout='{"ok": true}')
        with (
            patch("teamdash.fetch_github.subprocess.run", side_effect=[fail, success]),
            patch("teamdash.fetch_github.time.sleep"),
        ):
            result = _run_gh(["gh", "api", "/test"], retries=1)
        assert result.returncode == 0

    def test_gives_up_after_retries(self):
        fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="403 rate limit exceeded")
        with (
            patch("teamdash.fetch_github.subprocess.run", return_value=fail),
            patch("teamdash.fetch_github.time.sleep"),
        ):
            result = _run_gh(["gh", "api", "/test"], retries=2)
        assert result.returncode != 0

    def test_no_retry_on_non_rate_limit_error(self):
        fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="not found")
        with patch("teamdash.fetch_github.subprocess.run", return_value=fail) as mock:
            result = _run_gh(["gh", "api", "/test"])
        assert mock.call_count == 1
        assert result.returncode != 0

    def test_returns_none_on_file_not_found(self):
        with patch("teamdash.fetch_github.subprocess.run", side_effect=FileNotFoundError):
            assert _run_gh(["gh", "api", "/test"]) is None


class TestGhSearchCount:
    def test_success(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"total_count": 42}),
        )
        with patch("teamdash.fetch_github._run_gh", return_value=fake):
            assert _gh_search_count("test+query") == 42

    def test_zero_count(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"total_count": 0}),
        )
        with patch("teamdash.fetch_github._run_gh", return_value=fake):
            assert _gh_search_count("test") == 0

    def test_exits_on_none_result(self):
        with patch("teamdash.fetch_github._run_gh", return_value=None):
            with pytest.raises(SystemExit):
                _gh_search_count("test")

    def test_api_error(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="some error",
        )
        with patch("teamdash.fetch_github._run_gh", return_value=fake):
            assert _gh_search_count("test") == 0

    def test_invalid_json(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not json",
        )
        with patch("teamdash.fetch_github._run_gh", return_value=fake):
            assert _gh_search_count("test") == 0


class TestFetchPrs:
    def test_combined_query(self):
        with patch("teamdash.fetch_github._gh_search_count", return_value=15) as mock:
            result = fetch_prs("alice", ["org1", "org2"], "2025-01-01", "2025-03-31")
        assert result == 15
        assert mock.call_count == 1
        query = mock.call_args[0][0]
        assert "org:org1+org:org2" in query
        assert "author:alice" in query
        assert "merged:2025-01-01..2025-03-31" in query


class TestFetchReviews:
    def test_combined_query(self):
        with patch("teamdash.fetch_github._gh_search_count", return_value=10) as mock:
            result = fetch_reviews("alice", ["org1", "org2"], "2025-01-01", "2025-03-31")
        assert result == 10
        assert mock.call_count == 1
        query = mock.call_args[0][0]
        assert "reviewed-by:alice" in query
        assert "-author:alice" in query
        assert "org:org1+org:org2" in query


class TestGhSearchItems:
    def test_returns_items(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps({"total_count": 2, "items": [{"id": 1}, {"id": 2}]}),
        )
        with patch("teamdash.fetch_github._run_gh", return_value=fake):
            items = _gh_search_items("test+query")
        assert len(items) == 2

    def test_pagination(self):
        page1 = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps({"items": [{"id": i} for i in range(100)]}),
        )
        page2 = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps({"items": [{"id": 100}]}),
        )
        with patch("teamdash.fetch_github._run_gh", side_effect=[page1, page2]):
            items = _gh_search_items("test")
        assert len(items) == 101

    def test_exits_on_none_result(self):
        with patch("teamdash.fetch_github._run_gh", return_value=None):
            with pytest.raises(SystemExit):
                _gh_search_items("test")


class TestFetchMergeTimes:
    def test_computes_days(self):
        items = [
            {"created_at": "2025-01-01T00:00:00Z", "closed_at": "2025-01-03T12:00:00Z"},
            {"created_at": "2025-01-10T00:00:00Z", "closed_at": "2025-01-11T00:00:00Z"},
        ]
        with patch("teamdash.fetch_github._gh_search_items", return_value=items):
            result = fetch_merge_times("alice", ["org1"], "2025-01-01", "2025-03-31")
        assert len(result) == 2
        assert result[0] == 2.5
        assert result[1] == 1.0

    def test_empty_when_no_merged_prs(self):
        with patch("teamdash.fetch_github._gh_search_items", return_value=[]):
            result = fetch_merge_times("alice", ["org1"], "2025-01-01", "2025-03-31")
        assert result == []

    def test_combined_query(self):
        with patch("teamdash.fetch_github._gh_search_items", return_value=[]) as mock:
            fetch_merge_times("alice", ["org1", "org2"], "2025-01-01", "2025-03-31")
        assert mock.call_count == 1
        query = mock.call_args[0][0]
        assert "org:org1+org:org2" in query


class TestFetchPrDetails:
    def _graphql_response(self, nodes, has_next=False, cursor=None):
        return {
            "data": {
                "search": {
                    "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                    "nodes": nodes,
                },
            },
        }

    def test_returns_details(self):
        nodes = [
            {
                "url": "https://github.com/org/repo/pull/1",
                "additions": 100,
                "deletions": 50,
                "changedFiles": 5,
                "createdAt": "2025-01-01T00:00:00Z",
                "closedAt": "2025-01-03T00:00:00Z",
                "labels": {"nodes": [{"name": "feature"}]},
                "comments": {"totalCount": 2},
                "reviews": {
                    "totalCount": 2,
                    "nodes": [
                        {"state": "APPROVED"},
                        {"state": "CHANGES_REQUESTED"},
                    ],
                },
            },
        ]
        with patch("teamdash.fetch_github._gh_graphql", return_value=self._graphql_response(nodes)):
            result = fetch_pr_details("alice", ["org"], "2025-01-01", "2025-03-31")

        assert len(result) == 1
        d = result[0]
        assert d.additions == 100
        assert d.deletions == 50
        assert d.changed_files == 5
        assert d.labels == ["feature"]
        assert d.review_count == 2
        assert d.changes_requested_count == 1
        assert d.comments_count == 2
        assert d.merge_time_days == 2.0
        assert d.source == "github"

    def test_returns_empty_on_failed_graphql(self):
        with patch("teamdash.fetch_github._gh_graphql", return_value=None):
            result = fetch_pr_details("alice", ["org"], "2025-01-01", "2025-03-31")
        assert result == []

    def test_empty_search_results(self):
        with patch("teamdash.fetch_github._gh_graphql", return_value=self._graphql_response([])):
            result = fetch_pr_details("alice", ["org"], "2025-01-01", "2025-03-31")
        assert result == []

    def test_skips_empty_nodes(self):
        nodes = [None, {}, {"url": "https://github.com/org/repo/pull/1",
                            "additions": 10, "deletions": 5, "changedFiles": 1,
                            "createdAt": "2025-01-01T00:00:00Z", "closedAt": "2025-01-02T00:00:00Z",
                            "labels": {"nodes": []}, "comments": {"totalCount": 0},
                            "reviews": {"totalCount": 0, "nodes": []}}]
        with patch("teamdash.fetch_github._gh_graphql", return_value=self._graphql_response(nodes)):
            result = fetch_pr_details("alice", ["org"], "2025-01-01", "2025-03-31")
        assert len(result) == 1

    def test_pagination(self):
        page1 = self._graphql_response(
            [{"url": "https://github.com/org/repo/pull/1", "additions": 1, "deletions": 0,
              "changedFiles": 1, "createdAt": "2025-01-01T00:00:00Z", "closedAt": "2025-01-02T00:00:00Z",
              "labels": {"nodes": []}, "comments": {"totalCount": 0},
              "reviews": {"totalCount": 0, "nodes": []}}],
            has_next=True, cursor="abc123",
        )
        page2 = self._graphql_response(
            [{"url": "https://github.com/org/repo/pull/2", "additions": 2, "deletions": 0,
              "changedFiles": 1, "createdAt": "2025-01-01T00:00:00Z", "closedAt": "2025-01-02T00:00:00Z",
              "labels": {"nodes": []}, "comments": {"totalCount": 0},
              "reviews": {"totalCount": 0, "nodes": []}}],
        )
        with patch("teamdash.fetch_github._gh_graphql", side_effect=[page1, page2]) as mock:
            result = fetch_pr_details("alice", ["org"], "2025-01-01", "2025-03-31")
        assert len(result) == 2
        assert mock.call_count == 2


class TestCheckAuth:
    def test_authenticated(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("teamdash.fetch_github.subprocess.run", return_value=fake):
            assert check_auth() is True

    def test_not_authenticated(self):
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
        with patch("teamdash.fetch_github.subprocess.run", return_value=fake):
            assert check_auth() is False

    def test_gh_not_found(self):
        with patch("teamdash.fetch_github.subprocess.run", side_effect=FileNotFoundError):
            assert check_auth() is False
