from __future__ import annotations

import pytest

from teamdash.config import load_config


VALID_YAML = """\
team_name: "Test Team"
github:
  orgs:
    - test-org
engineers:
  - name: Alice
    github: alice
"""


class TestLoadConfig:
    def test_valid_config(self, tmp_path):
        f = tmp_path / "team.yaml"
        f.write_text(VALID_YAML)
        config = load_config(str(f))
        assert config.team_name == "Test Team"
        assert config.github_orgs == ["test-org"]
        assert len(config.engineers) == 1
        assert config.engineers[0].name == "Alice"
        assert config.engineers[0].github == "alice"
        assert config.gitlab_url is None

    def test_full_config(self, tmp_path):
        f = tmp_path / "team.yaml"
        f.write_text("""\
team_name: "Full Team"
gitlab:
  url: "https://gitlab.example.com"
github:
  orgs:
    - org1
    - org2
engineers:
  - name: Alice
    github: alice
    gitlab: alice_gl
  - name: Bob
    gitlab: bob_gl
""")
        config = load_config(str(f))
        assert config.gitlab_url == "https://gitlab.example.com"
        assert config.github_orgs == ["org1", "org2"]
        assert len(config.engineers) == 2
        assert config.engineers[1].github is None
        assert config.engineers[1].gitlab == "bob_gl"

    def test_missing_file(self):
        with pytest.raises(SystemExit):
            load_config("/nonexistent/path.yaml")

    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(": :\n  - [invalid")
        with pytest.raises(SystemExit):
            load_config(str(f))

    def test_not_a_dict(self, tmp_path):
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2")
        with pytest.raises(SystemExit):
            load_config(str(f))

    def test_missing_team_name(self, tmp_path):
        f = tmp_path / "team.yaml"
        f.write_text("engineers:\n  - name: Alice\n    github: alice")
        with pytest.raises(SystemExit):
            load_config(str(f))

    def test_no_engineers(self, tmp_path):
        f = tmp_path / "team.yaml"
        f.write_text("team_name: Test\nengineers: []")
        with pytest.raises(SystemExit):
            load_config(str(f))

    def test_engineer_missing_name(self, tmp_path):
        f = tmp_path / "team.yaml"
        f.write_text("team_name: Test\nengineers:\n  - github: alice")
        with pytest.raises(SystemExit):
            load_config(str(f))

    def test_engineer_no_github_or_gitlab(self, tmp_path):
        f = tmp_path / "team.yaml"
        f.write_text("team_name: Test\nengineers:\n  - name: Alice")
        with pytest.raises(SystemExit):
            load_config(str(f))
