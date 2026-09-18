"""
Database Row-Level Security (RLS) Migration for PostgreSQL.
Enforces kernel-level multi-tenancy isolation across all tables.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import asyncio
import logging
from sqlalchemy import text
from src.db.session import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rls_migration")

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

async def apply_rls():
    async with engine.begin() as conn:
        logger.info("Verifying/creating audit_app_user non-superuser role...")
        await conn.execute(text("""
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
        """))

        # 1. Organizations table
        logger.info("Applying RLS on organizations table...")
        await conn.execute(text("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;"))
        await conn.execute(text("ALTER TABLE organizations FORCE ROW LEVEL SECURITY;"))
        await conn.execute(text("DROP POLICY IF EXISTS tenant_isolation_policy ON organizations;"))
        await conn.execute(text("""
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
        """))

        # 2. Direct tenant-owned tables (having organization_id column)
        for tbl in DIRECT_TENANT_TABLES:
            logger.info(f"Applying RLS on direct tenant table: {tbl}")
            await conn.execute(text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;"))
            await conn.execute(text(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;"))
            await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};"))
            await conn.execute(text(f"""
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
            """))

        # 3. Child tables (indirect tenant ownership via foreign key)
        for child in CHILD_TABLES:
            tbl = child["table"]
            fk = child["fk"]
            parent = child["parent"]
            logger.info(f"Applying RLS on child table: {tbl} (parent: {parent}.{fk})")
            await conn.execute(text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;"))
            await conn.execute(text(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;"))
            await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};"))
            await conn.execute(text(f"""
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
            """))

    logger.info("Successfully applied PostgreSQL Row-Level Security across all tenant tables.")

if __name__ == "__main__":
    asyncio.run(apply_rls())
