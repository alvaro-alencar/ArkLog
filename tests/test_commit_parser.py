"""Tests for the GitHub commit parser."""

import pytest

from app.integrations.github.commit_parser import CommitParser


SAMPLE_PUSH_PAYLOAD = {
    "ref": "refs/heads/main",
    "repository": {"full_name": "my-org/smartead"},
    "commits": [
        {
            "id": "abc123def456abc123def456abc123def456abc1",
            "message": "feat: add authentication module\n\nIntroduces JWT-based auth.",
            "timestamp": "2025-05-06T10:30:00Z",
            "url": "https://github.com/my-org/smartead/commit/abc123",
            "author": {"name": "Alvaro Alencar", "email": "alvaro@example.com"},
            "added": ["app/auth/jwt.py", "app/auth/__init__.py"],
            "modified": ["app/main.py"],
            "removed": [],
        },
        {
            "id": "def456abc123def456abc123def456abc123def4",
            "message": "fix: correct token expiry calculation",
            "timestamp": "2025-05-06T11:00:00Z",
            "url": "https://github.com/my-org/smartead/commit/def456",
            "author": {"name": "Alvaro Alencar", "email": "alvaro@example.com"},
            "added": [],
            "modified": ["app/auth/jwt.py"],
            "removed": [],
        },
    ],
}


def test_parse_returns_correct_count():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    assert len(commits) == 2


def test_parse_extracts_branch():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    assert all(c.branch == "main" for c in commits)


def test_parse_extracts_sha():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    assert commits[0].sha == "abc123def456abc123def456abc123def456abc1"


def test_parse_extracts_subject():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    assert commits[0].subject == "feat: add authentication module"


def test_parse_extracts_author():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    assert commits[0].author_name == "Alvaro Alencar"


def test_parse_files_status():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    first = commits[0]
    statuses = {f.status for f in first.files}
    assert "added" in statuses
    assert "modified" in statuses


def test_parse_file_count():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    # 2 added + 1 modified = 3 files
    assert len(commits[0].files) == 3


def test_parse_empty_commits_returns_empty_list():
    payload = {**SAMPLE_PUSH_PAYLOAD, "commits": []}
    assert CommitParser().parse(payload) == []


def test_parse_repo_full_name():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    assert all(c.repo_full_name == "my-org/smartead" for c in commits)


def test_affected_directories():
    commits = CommitParser().parse(SAMPLE_PUSH_PAYLOAD)
    dirs = commits[0].affected_directories
    assert "app/auth" in dirs


def test_extract_branch_strips_prefix():
    assert CommitParser._extract_branch("refs/heads/feature/x") == "feature/x"
    assert CommitParser._extract_branch("main") == "main"
