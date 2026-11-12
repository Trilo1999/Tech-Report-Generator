"""Initial database schema migration.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-11-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. users table
    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("username", sa.String(), unique=True, nullable=False),
            sa.Column("email", sa.String(), unique=True, nullable=True),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.String(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
        )

    # 2. roles table
    if "roles" not in existing_tables:
        op.create_table(
            "roles",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), unique=True, nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.String(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
        )

    # 3. components table
    if "components" not in existing_tables:
        op.create_table(
            "components",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), unique=True, nullable=False),
            sa.Column("component_uri", sa.String(), unique=True, nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.String(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
        )

    # 4. user_role_mapping table
    if "user_role_mapping" not in existing_tables:
        op.create_table(
            "user_role_mapping",
            sa.Column(
                "user_id",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "role_id",
                sa.String(),
                sa.ForeignKey("roles.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("user_id", "role_id"),
        )

    # 5. role_component_mapping table
    if "role_component_mapping" not in existing_tables:
        op.create_table(
            "role_component_mapping",
            sa.Column(
                "role_id",
                sa.String(),
                sa.ForeignKey("roles.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "component_id",
                sa.String(),
                sa.ForeignKey("components.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("role_id", "component_id"),
        )

    # 6. research_tasks table
    if "research_tasks" not in existing_tables:
        op.create_table(
            "research_tasks",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("topic", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("result", sa.Text(), nullable=True),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("updated_at", sa.String(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("research_tasks")
    op.drop_table("role_component_mapping")
    op.drop_table("user_role_mapping")
    op.drop_table("components")
    op.drop_table("roles")
    op.drop_table("users")
