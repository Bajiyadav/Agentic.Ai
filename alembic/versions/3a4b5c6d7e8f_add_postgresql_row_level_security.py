"""add_postgresql_row_level_security

Revision ID: 3a4b5c6d7e8f
Revises: 2a3b4c5d6e7f
Create Date: 2026-09-17 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '3a4b5c6d7e8f'
down_revision: Union[str, Sequence[str], None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DIRECT_TENANT_TABLES = [
    "candidates",
    "job_openings",
    "candidate_assessments",
    "candidate_job_evidence_audits",
    "job_assessments",
    "job_match_scores",
    "audit_logs",
    "email_connections",
    "technical_interviews",
    "generated_replies",
    "applications",
    "resumes",
    "audits",
    "jobs",
    "memberships",
    "pipeline_stages",
    "ats_integrations",
    "evidence_nodes",
]

CHILD_TABLES = [
    {
        "table": "resume_claims",
        "fk": "resume_id",
        "parent": "resumes",
    },
    {
        "table": "github_profiles",
        "fk": "candidate_id",
        "parent": "candidates",
    },
    {
        "table": "audit_flags",
        "fk": "audit_id",
        "parent": "audits",
    },
    {
        "table": "model_evaluations",
        "fk": "audit_id",
        "parent": "audits",
    },
]

def upgrade() -> None:
    # Only run PostgreSQL-specific RLS commands on postgresql dialect
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # 1. Create audit_app_user role if it does not exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'audit_app_user') THEN
                CREATE ROLE audit_app_user WITH LOGIN;
            END IF;
            GRANT USAGE ON SCHEMA public TO audit_app_user;
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO audit_app_user;
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO audit_app_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO audit_app_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO audit_app_user;
        END
        $$;
    """)

    # 2. Organizations table RLS
    op.execute("""
        ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS tenant_isolation_policy ON organizations;
        CREATE POLICY tenant_isolation_policy ON organizations
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            current_setting('app.current_tenant_id', true) IS NULL
            OR current_setting('app.current_tenant_id', true) = ''
            OR id::text = current_setting('app.current_tenant_id', true)
        )
        WITH CHECK (
            current_setting('app.current_tenant_id', true) IS NULL
            OR current_setting('app.current_tenant_id', true) = ''
            OR id::text = current_setting('app.current_tenant_id', true)
        );
    """)

    # 3. Direct tenant-owned tables
    for tbl in DIRECT_TENANT_TABLES:
        try:
            op.execute(f"""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{tbl}') THEN
                        ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;
                        ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;
                        DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};
                        CREATE POLICY tenant_isolation_policy ON {tbl}
                        AS PERMISSIVE
                        FOR ALL
                        TO PUBLIC
                        USING (
                            current_setting('app.current_tenant_id', true) IS NULL
                            OR current_setting('app.current_tenant_id', true) = ''
                            OR organization_id::text = current_setting('app.current_tenant_id', true)
                        )
                        WITH CHECK (
                            current_setting('app.current_tenant_id', true) IS NULL
                            OR current_setting('app.current_tenant_id', true) = ''
                            OR organization_id::text = current_setting('app.current_tenant_id', true)
                        );
                    END IF;
                END
                $$;
            """)
        except Exception:
            pass

    # 4. Child tables with indirect tenant ownership via foreign key
    for child in CHILD_TABLES:
        tbl = child["table"]
        fk = child["fk"]
        parent = child["parent"]
        try:
            op.execute(f"""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{tbl}') THEN
                        ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;
                        ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;
                        DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};
                        CREATE POLICY tenant_isolation_policy ON {tbl}
                        AS PERMISSIVE
                        FOR ALL
                        TO PUBLIC
                        USING (
                            current_setting('app.current_tenant_id', true) IS NULL
                            OR current_setting('app.current_tenant_id', true) = ''
                            OR EXISTS (
                                SELECT 1 FROM {parent}
                                WHERE {parent}.id = {tbl}.{fk}
                                AND {parent}.organization_id::text = current_setting('app.current_tenant_id', true)
                            )
                        )
                        WITH CHECK (
                            current_setting('app.current_tenant_id', true) IS NULL
                            OR current_setting('app.current_tenant_id', true) = ''
                            OR EXISTS (
                                SELECT 1 FROM {parent}
                                WHERE {parent}.id = {tbl}.{fk}
                                AND {parent}.organization_id::text = current_setting('app.current_tenant_id', true)
                            )
                        );
                    END IF;
                END
                $$;
            """)
        except Exception:
            pass

def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON organizations;")

    for tbl in DIRECT_TENANT_TABLES:
        try:
            op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;")
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};")
        except Exception:
            pass

    for child in CHILD_TABLES:
        tbl = child["table"]
        try:
            op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;")
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};")
        except Exception:
            pass
