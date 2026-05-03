from __future__ import annotations

import json
from unittest.mock import patch

from teamdash.aggregate import _config_hash, _is_quarter_cache_fresh, _load_cache, _save_cache, collect_all_data
from teamdash.config import EngineerConfig, TeamConfig
from teamdash.models import Quarter


class TestConfigHash:
    def test_deterministic(self, sample_config):
        h1 = _config_hash(sample_config)
        h2 = _config_hash(sample_config)
        assert h1 == h2

    def test_different_configs_different_hashes(self, sample_config):
        other = TeamConfig(
            team_name="Other",
            gitlab_url=None,
            github_orgs=["other-org"],
            engineers=[EngineerConfig(name="Charlie", github="charlie")],
        )
        assert _config_hash(sample_config) != _config_hash(other)

    def test_hash_length(self, sample_config):
        assert len(_config_hash(sample_config)) == 12


class TestCache:
    def test_save_and_load(self, tmp_path, sample_config):
        data = {"2025-Q1": {"_meta": {"fetched_date": "2026-05-01"}, "Alice": {"github_prs": 5, "gitlab_mrs": 3, "reviews": 2}}}
        with patch("teamdash.aggregate.CACHE_DIR", tmp_path):
            _save_cache(sample_config, data)
            loaded = _load_cache(sample_config)
        assert loaded == data

    def test_load_missing_cache(self, tmp_path, sample_config):
        with patch("teamdash.aggregate.CACHE_DIR", tmp_path):
            assert _load_cache(sample_config) == {}

    def test_load_returns_quarters_regardless_of_date(self, tmp_path, sample_config):
        cache_file = tmp_path / f"{_config_hash(sample_config)}.json"
        cache_file.write_text(json.dumps({"quarters": {"2025-Q1": {"_meta": {"fetched_date": "2020-01-01"}}}}))
        with patch("teamdash.aggregate.CACHE_DIR", tmp_path):
            loaded = _load_cache(sample_config)
        assert "2025-Q1" in loaded


class TestIsQuarterCacheFresh:
    def test_completed_quarter_always_fresh(self):
        data = {"_meta": {"fetched_date": "2020-01-01"}, "Alice": {"github_prs": 5}}
        assert _is_quarter_cache_fresh(data, "2024-12-31") is True

    def test_current_quarter_fresh_if_fetched_today(self):
        from datetime import date
        today = date.today().isoformat()
        data = {"_meta": {"fetched_date": today}}
        assert _is_quarter_cache_fresh(data, "2099-12-31") is True

    def test_current_quarter_stale_if_fetched_yesterday(self):
        data = {"_meta": {"fetched_date": "2020-01-01"}}
        assert _is_quarter_cache_fresh(data, "2099-12-31") is False

    def test_no_meta_is_stale(self):
        data = {"Alice": {"github_prs": 5}}
        assert _is_quarter_cache_fresh(data, "2024-12-31") is False


class TestCollectAllData:
    def test_collects_from_fetch_functions(self, sample_config):
        quarters = [Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")]
        with (
            patch("teamdash.aggregate.check_gitlab_auth", return_value=True),
            patch("teamdash.aggregate.fetch_prs", return_value=10),
            patch("teamdash.aggregate.fetch_reviews", return_value=5),
            patch("teamdash.aggregate.fetch_mrs", return_value=3),
            patch("teamdash.aggregate.fetch_merge_times", return_value=[1.0, 2.0]),
            patch("teamdash.aggregate.fetch_mr_merge_times", return_value=[3.0]),
            patch("teamdash.aggregate.fetch_gitlab_reviews", return_value=2),
            patch("teamdash.aggregate._load_cache", return_value={}),
            patch("teamdash.aggregate._save_cache"),
        ):
            summaries = collect_all_data(sample_config, quarters, use_cache=False, enable_scoring=False)

        assert len(summaries) == 1
        assert len(summaries[0].engineers) == 2
        alice = summaries[0].engineers[0]
        assert alice.name == "Alice"
        assert alice.github_prs == 10
        assert alice.gitlab_mrs == 3
        assert alice.reviews == 7
        assert alice.merge_time_days == 2.0

    def test_uses_cached_data(self, sample_config):
        quarters = [Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")]
        cached = {
            "2025-Q1": {
                "_meta": {"fetched_date": "2025-04-01"},
                "Alice": {"github_prs": 8, "gitlab_mrs": 4, "reviews": 6, "merge_time_days": 1.5},
                "Bob": {"github_prs": 2, "gitlab_mrs": 1, "reviews": 3, "merge_time_days": 3.0},
            },
        }
        with (
            patch("teamdash.aggregate.check_gitlab_auth", return_value=True),
            patch("teamdash.aggregate.fetch_prs") as mock_prs,
            patch("teamdash.aggregate.fetch_reviews"),
            patch("teamdash.aggregate.fetch_mrs"),
            patch("teamdash.aggregate.fetch_merge_times"),
            patch("teamdash.aggregate.fetch_mr_merge_times"),
            patch("teamdash.aggregate._load_cache", return_value=cached),
            patch("teamdash.aggregate._save_cache"),
        ):
            summaries = collect_all_data(sample_config, quarters)

        mock_prs.assert_not_called()
        alice = summaries[0].engineers[0]
        assert alice.github_prs == 8
        assert alice.merge_time_days == 1.5

    def test_gitlab_auth_failure_skips_mrs(self, sample_config):
        quarters = [Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")]
        with (
            patch("teamdash.aggregate.check_gitlab_auth", return_value=False),
            patch("teamdash.aggregate.fetch_prs", return_value=10),
            patch("teamdash.aggregate.fetch_reviews", return_value=5),
            patch("teamdash.aggregate.fetch_mrs") as mock_mrs,
            patch("teamdash.aggregate.fetch_merge_times", return_value=[2.0]),
            patch("teamdash.aggregate.fetch_mr_merge_times") as mock_gl_mt,
            patch("teamdash.aggregate.fetch_gitlab_reviews") as mock_gl_reviews,
            patch("teamdash.aggregate._load_cache", return_value={}),
            patch("teamdash.aggregate._save_cache"),
        ):
            summaries = collect_all_data(sample_config, quarters, use_cache=False, enable_scoring=False)

        mock_mrs.assert_not_called()
        mock_gl_mt.assert_not_called()
        mock_gl_reviews.assert_not_called()
        assert summaries[0].engineers[0].gitlab_mrs == 0
        assert summaries[0].engineers[0].merge_time_days == 2.0

    def test_scoring_enabled_uses_detail_fetchers(self, sample_config):
        from teamdash.models import PRDetail

        quarters = [Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")]
        gh_details = [
            PRDetail(
                url="https://github.com/org/repo/pull/1",
                source="github", author="alice",
                additions=100, deletions=20, changed_files=4,
                merge_time_days=1.5,
            ),
        ]
        gl_details = [
            PRDetail(
                url="https://gitlab.example.com/mr/1",
                source="gitlab", author="alice_gl",
                additions=50, deletions=10, changed_files=2,
                merge_time_days=2.0,
            ),
        ]
        with (
            patch("teamdash.aggregate.check_gitlab_auth", return_value=True),
            patch("teamdash.aggregate.fetch_pr_details", return_value=gh_details),
            patch("teamdash.aggregate.fetch_mr_details", return_value=gl_details),
            patch("teamdash.aggregate.fetch_reviews", return_value=3),
            patch("teamdash.aggregate.fetch_gitlab_reviews", return_value=4),
            patch("teamdash.aggregate._load_cache", return_value={}),
            patch("teamdash.aggregate._save_cache"),
        ):
            summaries = collect_all_data(sample_config, quarters, use_cache=False, enable_scoring=True)

        alice = summaries[0].engineers[0]
        assert alice.github_prs == 1
        assert alice.gitlab_mrs == 1
        assert alice.story_points > 0
        assert len(alice.scored_prs) == 2

    def test_no_scoring_skips_detail_fetchers(self, sample_config):
        quarters = [Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")]
        with (
            patch("teamdash.aggregate.check_gitlab_auth", return_value=True),
            patch("teamdash.aggregate.fetch_prs", return_value=5),
            patch("teamdash.aggregate.fetch_reviews", return_value=2),
            patch("teamdash.aggregate.fetch_mrs", return_value=3),
            patch("teamdash.aggregate.fetch_merge_times", return_value=[1.0]),
            patch("teamdash.aggregate.fetch_mr_merge_times", return_value=[2.0]),
            patch("teamdash.aggregate.fetch_gitlab_reviews", return_value=0),
            patch("teamdash.aggregate.fetch_pr_details") as mock_details,
            patch("teamdash.aggregate._load_cache", return_value={}),
            patch("teamdash.aggregate._save_cache"),
        ):
            summaries = collect_all_data(sample_config, quarters, use_cache=False, enable_scoring=False)

        mock_details.assert_not_called()
        assert summaries[0].engineers[0].story_points == 0
