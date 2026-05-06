"""Unit tests for the GitHub commit parser. No DB or external deps required."""

import json
from pathlib import Path

import pytest

from app.integrations.github.commit_parser import CommitParser

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "github_push_payload.json"


@pytest.fixture
def raw_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture
def parser() -> CommitParser:
    return CommitParser()


def test_parse_commit_count(parser, raw_payload):
    assert len(parser.parse(raw_payload)) == 2


def test_parse_repo_and_branch(parser, raw_payload):
    commits = parser.parse(raw_payload)
    assert all(c.repo_full_name == "my-org/smartead" for c in commits)
    assert all(c.branch == "main" for c in commits)


def test_parse_branch_strips_refs_prefix(parser, raw_payload):
    raw_payload["ref"] = "refs/heads/feature/my-branch"
    commits = parser.parse(raw_payload)
    assert commits[0].branch == "feature/my-branch"


def test_parse_first_commit_fields(parser, raw_payload):
    commit = parser.parse(raw_payload)[0]
    assert commit.short_sha == "abc1234"
    assert commit.subject == "feat: add user authentication module"
    assert commit.author_name == "Alvaro Alencar"
    assert commit.author_email == "alvaro@example.com"


def test_parse_file_count(parser, raw_payload):
    commit = parser.parse(raw_payload)[0]
    assert len(commit.files) == 4  # 2 added + 2 modified


def test_parse_file_statuses(parser, raw_payload):
    commit = parser.parse(raw_payload)[0]
    by_name = {f.filename: f.status for f in commit.files}
    assert by_name["app/auth/jwt.py"] == "added"
    assert by_name["app/auth/__init__.py"] == "added"
    assert by_name["app/main.py"] == "modified"
    assert by_name["pyproject.toml"] == "modified"


def test_parse_removed_file(parser, raw_payload):
    commit = parser.parse(raw_payload)[1]
    removed = [f for f in commit.files if f.status == "removed"]
    assert len(removed) == 1
    assert removed[0].filename == "app/auth/old_auth.py"


def test_parse_empty_commits_returns_empty_list(parser, raw_payload):
    raw_payload["commits"] = []
    assert parser.parse(raw_payload) == []


def test_parse_affected_directories(parser, raw_payload):
    commit = parser.parse(raw_payload)[0]
    assert "app/auth" in commit.affected_directories
    assert "app" in commit.affected_directories


def test_parse_affected_extensions(parser, raw_payload):
    commit = parser.parse(raw_payload)[0]
    assert "py" in commit.affected_extensions
    assert "toml" in commit.affected_extensions


def test_parse_is_not_merge_commit(parser, raw_payload):
    commit = parser.parse(raw_payload)[0]
    assert not commit.is_merge_commit


def test_parse_merge_commit_detection(parser, raw_payload):
    raw_payload["commits"][0]["message"] = "Merge pull request #42 from feature/auth"
    commit = parser.parse(raw_payload)[0]
    assert commit.is_merge_commit
