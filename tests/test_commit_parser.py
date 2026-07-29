"""Tests for the GitHub commit parser."""

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
        }
    ],
}


def test_parse_push_payload() -> None:
    commits = CommitParser.parse_push_payload(SAMPLE_PUSH_PAYLOAD)
    assert len(commits) == 1
    commit = commits[0]
    assert commit.sha == "abc123def456abc123def456abc123def456abc1"
    assert commit.repository == "my-org/smartead"
    assert commit.author_name == "Alvaro Alencar"
    assert commit.author_email == "alvaro@example.com"
    assert commit.message.startswith("feat: add authentication module")
    assert commit.branch == "main"
    assert commit.files_changed == 3
    assert commit.additions == ["app/auth/jwt.py", "app/auth/__init__.py"]
    assert commit.modifications == ["app/main.py"]
    assert commit.deletions == []
