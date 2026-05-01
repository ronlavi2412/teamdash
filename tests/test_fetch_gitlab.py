from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from teamdash.fetch_gitlab import (
    _extract_hostname,
    _glab_api_get,
    _in_date_range,
    check_auth,
    fetch_mr_details,
    fetch_mr_merge_times,
    fetch_mrs,
)


class TestExtractHostname:
    def test_https_url(self):
        assert _extract_hostname("https://gitlab.example.com") == "gitlab.example.com"

    def test_url_with_path(self):
        assert _extract_hostname("https://gitlab.example.com/api/v4") == "gitlab.example.com"

    def test_http_url(self):
        assert _extract_hostname("http://gitlab.local") == "gitlab.local"

    def test_no_scheme(self):
        assert _extract_hostname("gitlab.example.com") == "gitlab.example.com"


class TestFetchMrs:
    def test_single_page(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([
                {"id": 1, "merged_at": "2025-02-01T10:00:00Z"},
                {"id": 2, "merged_at": "2025-03-15T14:30:00Z"},
            ]),
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            result = fetch_mrs("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")
        assert result == 2

    def test_pagination(self):
        page1 = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([{"id": i, "merged_at": "2025-02-15T12:00:00Z"} for i in range(100)]),
        )
        page2 = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([
                {"id": 100, "merged_at": "2025-02-16T12:00:00Z"},
                {"id": 101, "merged_at": "2025-02-17T12:00:00Z"},
            ]),
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", side_effect=[page1, page2]):
            result = fetch_mrs("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")
        assert result == 102

    def test_glab_not_found(self):
        with patch("teamdash.fetch_gitlab.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit):
                fetch_mrs("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")

    def test_timeout_returns_partial(self):
        page1 = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([{"id": i, "merged_at": "2025-02-15T12:00:00Z"} for i in range(100)]),
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", side_effect=[page1, subprocess.TimeoutExpired(cmd="glab", timeout=30)]):
            result = fetch_mrs("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")
        assert result == 100

    def test_api_error_returns_partial(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error",
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            assert fetch_mrs("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31") == 0

    def test_invalid_json(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not json",
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            assert fetch_mrs("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31") == 0


class TestFetchMrMergeTimes:
    def test_computes_days(self):
        mrs = [
            {"created_at": "2025-01-01T00:00:00Z", "merged_at": "2025-01-04T00:00:00Z"},
            {"created_at": "2025-01-10T00:00:00Z", "merged_at": "2025-01-10T12:00:00Z"},
        ]
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(mrs),
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            result = fetch_mr_merge_times("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")
        assert len(result) == 2
        assert result[0] == 3.0
        assert result[1] == 0.5

    def test_empty_when_no_merged_mrs(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps([]),
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            result = fetch_mr_merge_times("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")
        assert result == []

    def test_skips_items_without_merged_at(self):
        mrs = [
            {"created_at": "2025-01-01T00:00:00Z", "merged_at": None},
            {"created_at": "2025-01-02T00:00:00Z", "merged_at": "2025-01-03T00:00:00Z"},
        ]
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(mrs),
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            result = fetch_mr_merge_times("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")
        assert len(result) == 1
        assert result[0] == 1.0


class TestGlabApiGet:
    def test_success(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps({"changes_count": "5"}),
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            result = _glab_api_get("https://gitlab.example.com", "/api/v4/projects/1/merge_requests/1")
        assert result == {"changes_count": "5"}

    def test_returns_none_on_error(self):
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            assert _glab_api_get("https://gitlab.example.com", "/endpoint") is None


class TestFetchMrDetails:
    def test_returns_details(self):
        mr_list = [
            {
                "project_id": 42,
                "iid": 1,
                "web_url": "https://gitlab.example.com/org/repo/-/merge_requests/1",
                "created_at": "2025-01-01T00:00:00Z",
                "merged_at": "2025-01-03T00:00:00Z",
                "closed_at": "2025-01-03T00:00:00Z",
                "labels": ["bug"],
                "author": {"username": "alice"},
            },
        ]
        mr_detail = {"changes_count": "4", "additions": 80, "deletions": 20}
        notes = [
            {"author": {"username": "bob"}, "system": False, "body": "looks good"},
            {"author": {"username": "alice"}, "system": False, "body": "thanks"},
            {"author": {"username": "system"}, "system": True, "body": "merged"},
        ]
        with (
            patch("teamdash.fetch_gitlab._fetch_mr_list", return_value=mr_list),
            patch("teamdash.fetch_gitlab._glab_api_get", side_effect=[mr_detail, notes]),
            patch("teamdash.fetch_gitlab.time.sleep"),
        ):
            result = fetch_mr_details("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")

        assert len(result) == 1
        d = result[0]
        assert d.additions == 80
        assert d.deletions == 20
        assert d.changed_files == 4
        assert d.labels == ["bug"]
        assert d.review_count == 1
        assert d.merge_time_days == 2.0
        assert d.source == "gitlab"

    def test_empty_mr_list(self):
        with patch("teamdash.fetch_gitlab._fetch_mr_list", return_value=[]):
            result = fetch_mr_details("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")
        assert result == []


class TestInDateRange:
    def test_z_suffix(self):
        assert _in_date_range("2025-02-15T12:00:00Z", "2025-01-01", "2025-03-31") is True

    def test_offset_suffix(self):
        assert _in_date_range("2025-02-15T12:00:00+00:00", "2025-01-01", "2025-03-31") is True

    def test_fractional_seconds(self):
        assert _in_date_range("2025-02-15T12:00:00.123Z", "2025-01-01", "2025-03-31") is True

    def test_before_range(self):
        assert _in_date_range("2024-12-31T23:59:59Z", "2025-01-01", "2025-03-31") is False

    def test_after_range(self):
        assert _in_date_range("2025-04-01T00:00:00Z", "2025-01-01", "2025-03-31") is False

    def test_at_start_boundary(self):
        assert _in_date_range("2025-01-01T00:00:00Z", "2025-01-01", "2025-03-31") is True

    def test_at_end_boundary(self):
        assert _in_date_range("2025-03-31T23:59:59Z", "2025-01-01", "2025-03-31") is True

    def test_end_boundary_fractional_seconds(self):
        assert _in_date_range("2025-03-31T23:59:59.999Z", "2025-01-01", "2025-03-31") is True


class TestCheckAuth:
    def test_authenticated(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            assert check_auth("https://gitlab.example.com") is True

    def test_not_authenticated(self):
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            assert check_auth("https://gitlab.example.com") is False

    def test_glab_not_found(self):
        with patch("teamdash.fetch_gitlab.subprocess.run", side_effect=FileNotFoundError):
            assert check_auth("https://gitlab.example.com") is False
