"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-06

NOTE: If your database was already created via create_all (startup auto-init),
run `alembic stamp head` once to mark it as up-to-date before using migrations.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("repo_full_name", sa.String(255), nullable=False),
        sa.Column("clickup_task_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "commits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sha", sa.String(40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(255), nullable=False),
        sa.Column("author_email", sa.String(255), nullable=False),
        sa.Column("committed_at", sa.DateTime(), nullable=False),
        sa.Column("branch", sa.String(255), nullable=False),
        sa.Column("files_changed", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha"),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trigger", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("commit_count", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("clickup_comment_id", sa.String(255), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("commits")
    op.drop_table("projects")
