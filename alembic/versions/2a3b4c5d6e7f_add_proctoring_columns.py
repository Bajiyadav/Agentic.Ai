"""add_proctoring_columns

Revision ID: 2a3b4c5d6e7f
Revises: 15f8fe3f7945
Create Date: 2026-09-11 16:42:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, Sequence[str], None] = '15f8fe3f7945'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    cols = [
        sa.Column('access_token', sa.String(length=128), nullable=True),
        sa.Column('otp_code', sa.String(length=10), nullable=True),
        sa.Column('otp_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('strike_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_strikes', sa.Integer(), server_default='3', nullable=False),
        sa.Column('disqualification_reason', sa.Text(), nullable=True),
        sa.Column('proctoring_logs', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('integrity_score', sa.Integer(), server_default='100', nullable=False),
        sa.Column('snapshots_json', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('sandbox_results', sa.JSON(), server_default='{}', nullable=False),
    ]
    for col in cols:
        try:
            op.add_column('candidate_assessments', col)
        except Exception:
            pass

def downgrade() -> None:
    cols = [
        'access_token', 'otp_code', 'otp_expires_at', 'strike_count',
        'max_strikes', 'disqualification_reason', 'proctoring_logs',
        'integrity_score', 'snapshots_json', 'sandbox_results'
    ]
    for c in cols:
        try:
            op.drop_column('candidate_assessments', c)
        except Exception:
            pass
