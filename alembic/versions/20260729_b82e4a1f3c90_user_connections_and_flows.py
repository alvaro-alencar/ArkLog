"""user_connections_and_flows

Revision ID: b82e4a1f3c90
Revises: 10cdca965784
Create Date: 2026-07-29 19:15:00

This migration is deliberately defensive because some early ArkLog installations
were bootstrapped with ``Base.metadata.create_all`` instead of a complete Alembic
history. Every addition is guarded by schema inspection.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b82e4a1f3c90"
down_revision: str | None = "10cdca965784"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> dict[str, dict]:
    return {
        item["name"]: item
        for item in sa.inspect(op.get_bind()).get_columns(table)
    }


def upgrade() -> None:
    tables = _tables()

    if "users" in tables:
        user_columns = _columns("users")
        with op.batch_alter_table("users") as batch_op:
            if "timezone" not in user_columns:
                batch_op.add_column(
                    sa.Column(
                        "timezone",
                        sa.String(length=100),
                        nullable=False,
                        server_default="America/Sao_Paulo",
                    )
                )
            if "language" not in user_columns:
                batch_op.add_column(
                    sa.Column(
                        "language",
                        sa.String(length=10),
                        nullable=False,
                        server_default="pt-BR",
                    )
                )
            if "ark_user_id" not in user_columns:
                batch_op.add_column(sa.Column("ark_user_id", sa.String(length=64)))
            if "ark_organization_id" not in user_columns:
                batch_op.add_column(
                    sa.Column("ark_organization_id", sa.String(length=64))
                )
            if "is_platform_admin" not in user_columns:
                batch_op.add_column(
                    sa.Column(
                        "is_platform_admin",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.false(),
                    )
                )
        indexes = {
            item["name"]
            for item in sa.inspect(op.get_bind()).get_indexes("users")
        }
        if "users_ark_user_id_idx" not in indexes:
            op.create_index(
                "users_ark_user_id_idx",
                "users",
                ["ark_user_id"],
                unique=True,
            )

    tables = _tables()
    if "arklog_access" not in tables:
        op.create_table(
            "arklog_access",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
            sa.Column("report_limit", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reports_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("trial_granted_at", sa.DateTime(), nullable=True),
            sa.Column("blocked_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    tables = _tables()
    if "integration_connections" not in tables:
        op.create_table(
            "integration_connections",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.String(length=64), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("label", sa.String(length=160), nullable=False),
            sa.Column("external_account_id", sa.String(length=255), nullable=True),
            sa.Column("external_account_name", sa.String(length=255), nullable=True),
            sa.Column("encrypted_credentials", sa.Text(), nullable=False),
            sa.Column("scopes", sa.JSON(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
            sa.Column("connected_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "organization_id",
                "provider",
                "external_account_id",
                name="uix_connection_external_account",
            ),
        )

    tables = _tables()
    if "automation_flows" not in tables:
        op.create_table(
            "automation_flows",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("source_connection_id", sa.Integer(), nullable=False),
            sa.Column("destination_connection_id", sa.Integer(), nullable=False),
            sa.Column("source_config", sa.JSON(), nullable=False),
            sa.Column("destination_config", sa.JSON(), nullable=False),
            sa.Column("report_config", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(
                ["source_connection_id"], ["integration_connections.id"]
            ),
            sa.ForeignKeyConstraint(
                ["destination_connection_id"], ["integration_connections.id"]
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "name", name="uix_flow_user_name"),
        )

    tables = _tables()
    if "reports" in tables:
        report_columns = _columns("reports")
        with op.batch_alter_table("reports") as batch_op:
            if "flow_id" not in report_columns:
                batch_op.add_column(sa.Column("flow_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    "fk_reports_flow_id",
                    "automation_flows",
                    ["flow_id"],
                    ["id"],
                )
            project_column = report_columns.get("project_id")
            if project_column and not project_column.get("nullable", True):
                batch_op.alter_column(
                    "project_id",
                    existing_type=sa.Integer(),
                    nullable=True,
                )

    tables = _tables()
    if "report_usages" not in tables:
        op.create_table(
            "report_usages",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("idempotency_key", sa.String(length=100), nullable=False),
            sa.Column("trigger", sa.String(length=50), nullable=False, server_default="instant"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="RESERVED"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("flow_id", sa.Integer(), nullable=True),
            sa.Column("report_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["flow_id"], ["automation_flows.id"]),
            sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "idempotency_key",
                name="uix_report_usage_idempotency",
            ),
        )
    else:
        usage_columns = _columns("report_usages")
        with op.batch_alter_table("report_usages") as batch_op:
            if "flow_id" not in usage_columns:
                batch_op.add_column(sa.Column("flow_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    "fk_report_usages_flow_id",
                    "automation_flows",
                    ["flow_id"],
                    ["id"],
                )
            project_column = usage_columns.get("project_id")
            if project_column and not project_column.get("nullable", True):
                batch_op.alter_column(
                    "project_id",
                    existing_type=sa.Integer(),
                    nullable=True,
                )


def downgrade() -> None:
    tables = _tables()
    if "report_usages" in tables:
        columns = _columns("report_usages")
        if "flow_id" in columns:
            op.execute("DELETE FROM report_usages WHERE flow_id IS NOT NULL")
            with op.batch_alter_table("report_usages") as batch_op:
                batch_op.drop_column("flow_id")

    tables = _tables()
    if "reports" in tables:
        columns = _columns("reports")
        if "flow_id" in columns:
            op.execute("DELETE FROM reports WHERE flow_id IS NOT NULL")
            with op.batch_alter_table("reports") as batch_op:
                batch_op.drop_column("flow_id")

    tables = _tables()
    if "automation_flows" in tables:
        op.drop_table("automation_flows")
    tables = _tables()
    if "integration_connections" in tables:
        op.drop_table("integration_connections")
