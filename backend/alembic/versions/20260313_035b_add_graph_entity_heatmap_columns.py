"""Phase 3.5b: add heatmap persistence fields to graph_entities

Revision ID: 20260313_035b
Revises:
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260313_035b"
down_revision = None
branch_labels = None
depends_on = None


TABLE_NAME = "graph_entities"
WEIGHT_COL = "weight"
LAST_ACCESSED_COL = "last_accessed_at"
WEIGHT_IDX = "ix_graph_entities_weight"
LAST_ACCESSED_IDX = "ix_graph_entities_last_accessed_at"


def _get_columns(connection):
    inspector = sa.inspect(connection)
    return {col["name"] for col in inspector.get_columns(TABLE_NAME)}


def _get_indexes(connection):
    inspector = sa.inspect(connection)
    return {idx["name"] for idx in inspector.get_indexes(TABLE_NAME)}


def upgrade() -> None:
    connection = op.get_bind()
    columns = _get_columns(connection)

    if WEIGHT_COL not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(WEIGHT_COL, sa.Float(), nullable=False, server_default="0.0"),
        )
        op.alter_column(TABLE_NAME, WEIGHT_COL, server_default=None)

    if LAST_ACCESSED_COL not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(LAST_ACCESSED_COL, sa.DateTime(timezone=True), nullable=True),
        )

    indexes = _get_indexes(connection)
    if WEIGHT_IDX not in indexes:
        op.create_index(WEIGHT_IDX, TABLE_NAME, [WEIGHT_COL], unique=False)
    if LAST_ACCESSED_IDX not in indexes:
        op.create_index(LAST_ACCESSED_IDX, TABLE_NAME, [LAST_ACCESSED_COL], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    columns = _get_columns(connection)
    indexes = _get_indexes(connection)

    if LAST_ACCESSED_IDX in indexes:
        op.drop_index(LAST_ACCESSED_IDX, table_name=TABLE_NAME)
    if WEIGHT_IDX in indexes:
        op.drop_index(WEIGHT_IDX, table_name=TABLE_NAME)

    if LAST_ACCESSED_COL in columns:
        op.drop_column(TABLE_NAME, LAST_ACCESSED_COL)
    if WEIGHT_COL in columns:
        op.drop_column(TABLE_NAME, WEIGHT_COL)
