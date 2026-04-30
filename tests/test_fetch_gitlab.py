from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from teamdash.fetch_gitlab import _extract_hostname, check_auth, fetch_mr_merge_times, fetch_mrs


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
            stdout=json.dumps([{"id": 1}, {"id": 2}]),
        )
        with patch("teamdash.fetch_gitlab.subprocess.run", return_value=fake):
            result = fetch_mrs("https://gitlab.example.com", "alice", "2025-01-01", "2025-03-31")
        assert result == 2

    def test_pagination(self):
        page1 = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([{"id": i} for i in range(100)]),
        )
        page2 = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([{"id": 100}, {"id": 101}]),
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
            stdout=json.dumps([{"id": i} for i in range(100)]),
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
