from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from teamdash.fetch_github import (
    _gh_search_count,
    _gh_search_items,
    check_auth,
    fetch_merge_times,
    fetch_prs,
    fetch_reviews,
)


class TestGhSearchCount:
    def test_success(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"total_count": 42}),
        )
        with patch("teamdash.fetch_github.subprocess.run", return_value=fake):
            assert _gh_search_count("test+query") == 42

    def test_zero_count(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"total_count": 0}),
        )
        with patch("teamdash.fetch_github.subprocess.run", return_value=fake):
            assert _gh_search_count("test") == 0

    def test_gh_not_found(self):
        with patch("teamdash.fetch_github.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit):
                _gh_search_count("test")

    def test_timeout(self):
        with patch("teamdash.fetch_github.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=30)):
            assert _gh_search_count("test") == 0

    def test_api_error(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="some error",
        )
        with patch("teamdash.fetch_github.subprocess.run", return_value=fake):
            assert _gh_search_count("test") == 0

    def test_rate_limit_retry_success(self):
        fail = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="403 rate limit exceeded",
        )
        success = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"total_count": 5}),
        )
        with patch("teamdash.fetch_github.subprocess.run", side_effect=[fail, success]):
            with patch("teamdash.fetch_github.time.sleep"):
                assert _gh_search_count("test") == 5

    def test_invalid_json(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not json",
        )
        with patch("teamdash.fetch_github.subprocess.run", return_value=fake):
            assert _gh_search_count("test") == 0


class TestFetchPrs:
    def test_sums_across_orgs(self):
        with patch("teamdash.fetch_github._gh_search_count", side_effect=[10, 5]):
            result = fetch_prs("alice", ["org1", "org2"], "2025-01-01", "2025-03-31")
        assert result == 15

    def test_query_format(self):
        with patch("teamdash.fetch_github._gh_search_count", return_value=0) as mock:
            fetch_prs("alice", ["myorg"], "2025-01-01", "2025-03-31")
        query = mock.call_args[0][0]
        assert "type:pr" in query
        assert "author:alice" in query
        assert "org:myorg" in query
        assert "created:2025-01-01..2025-03-31" in query


class TestFetchReviews:
    def test_query_format(self):
        with patch("teamdash.fetch_github._gh_search_count", return_value=0) as mock:
            fetch_reviews("alice", ["myorg"], "2025-01-01", "2025-03-31")
        query = mock.call_args[0][0]
        assert "reviewed-by:alice" in query
        assert "-author:alice" in query

    def test_sums_across_orgs(self):
        with patch("teamdash.fetch_github._gh_search_count", side_effect=[3, 7]):
            result = fetch_reviews("bob", ["org1", "org2"], "2025-01-01", "2025-03-31")
        assert result == 10


class TestGhSearchItems:
    def test_returns_items(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps({"total_count": 2, "items": [{"id": 1}, {"id": 2}]}),
        )
        with patch("teamdash.fetch_github.subprocess.run", return_value=fake):
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
        with patch("teamdash.fetch_github.subprocess.run", side_effect=[page1, page2]):
            items = _gh_search_items("test")
        assert len(items) == 101

    def test_timeout_returns_partial(self):
        with patch("teamdash.fetch_github.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=30)):
            assert _gh_search_items("test") == []


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

    def test_query_format(self):
        with patch("teamdash.fetch_github._gh_search_items", return_value=[]) as mock:
            fetch_merge_times("alice", ["myorg"], "2025-01-01", "2025-03-31")
        query = mock.call_args[0][0]
        assert "is:merged" in query
        assert "author:alice" in query
        assert "org:myorg" in query

    def test_sums_across_orgs(self):
        items1 = [{"created_at": "2025-01-01T00:00:00Z", "closed_at": "2025-01-02T00:00:00Z"}]
        items2 = [{"created_at": "2025-01-05T00:00:00Z", "closed_at": "2025-01-08T00:00:00Z"}]
        with patch("teamdash.fetch_github._gh_search_items", side_effect=[items1, items2]):
            result = fetch_merge_times("alice", ["org1", "org2"], "2025-01-01", "2025-03-31")
        assert len(result) == 2


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
