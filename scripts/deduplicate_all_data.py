import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("DATABASE_URL not set in environment!")
    sys.exit(1)

engine = create_async_engine(db_url)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def deduplicate_all():
    print("Starting Comprehensive Database Deduplication...")
    async with async_session() as session:

        # =========================================================================
        # STEP 1: DEDUPLICATE JOB OPENINGS
        # =========================================================================
        print("\n--- [Step 1] Deduplicating Job Openings ---")
        res_job_groups = await session.execute(text('''
            SELECT organization_id, LOWER(title), COUNT(*)
            FROM job_openings
            GROUP BY organization_id, LOWER(title)
            HAVING COUNT(*) > 1
        '''))
        job_groups = res_job_groups.fetchall()
        print(f"Found {len(job_groups)} duplicate job opening title groups.")

        for org_id, title, cnt in job_groups:
            res_items = await session.execute(text('''
                SELECT id, created_at 
                FROM job_openings 
                WHERE organization_id = :org_id AND LOWER(title) = :title 
                ORDER BY created_at DESC, id DESC
            '''), {'org_id': org_id, 'title': title})
            rows = res_items.fetchall()
            canonical_id = rows[0][0]
            dup_ids = [r[0] for r in rows[1:]]

            for dup_id in dup_ids:
                # 1. Handle job_assessments (unique constraint on job_id)
                res_canon_ja = await session.execute(text('SELECT id FROM job_assessments WHERE job_id = :jid'), {'jid': canonical_id})
                canon_ja = res_canon_ja.scalar()

                res_dup_ja = await session.execute(text('SELECT id FROM job_assessments WHERE job_id = :jid'), {'jid': dup_id})
                dup_ja_list = res_dup_ja.scalars().all()

                for dup_ja_id in dup_ja_list:
                    if canon_ja:
                        await session.execute(text('UPDATE candidate_assessments SET assessment_id = :canon WHERE assessment_id = :dup'), {'canon': canon_ja, 'dup': dup_ja_id})
                        await session.execute(text('DELETE FROM job_assessments WHERE id = :dup'), {'dup': dup_ja_id})
                    else:
                        await session.execute(text('UPDATE job_assessments SET job_id = :canon WHERE id = :dup'), {'canon': canonical_id, 'dup': dup_ja_id})
                        canon_ja = dup_ja_id

                # 2. Handle candidate_job_evidence_audits (unique constraint on candidate_id, job_id)
                await session.execute(text('''
                    DELETE FROM candidate_job_evidence_audits 
                    WHERE job_id = :dup 
                    AND candidate_id IN (SELECT candidate_id FROM candidate_job_evidence_audits WHERE job_id = :canon)
                '''), {'dup': dup_id, 'canon': canonical_id})
                await session.execute(text('UPDATE candidate_job_evidence_audits SET job_id = :canon WHERE job_id = :dup'), {'canon': canonical_id, 'dup': dup_id})

                # 3. Handle job_match_scores (unique constraint on candidate_id, job_id)
                await session.execute(text('''
                    DELETE FROM job_match_scores 
                    WHERE job_id = :dup 
                    AND candidate_id IN (SELECT candidate_id FROM job_match_scores WHERE job_id = :canon)
                '''), {'dup': dup_id, 'canon': canonical_id})
                await session.execute(text('UPDATE job_match_scores SET job_id = :canon WHERE job_id = :dup'), {'canon': canonical_id, 'dup': dup_id})

                # 4. Handle other child tables
                await session.execute(text('UPDATE candidate_assessments SET job_id = :canon WHERE job_id = :dup'), {'canon': canonical_id, 'dup': dup_id})
                await session.execute(text('UPDATE applications SET job_id = :canon WHERE job_id = :dup'), {'canon': canonical_id, 'dup': dup_id})
                await session.execute(text('UPDATE resumes SET job_id = :canon WHERE job_id = :dup'), {'canon': canonical_id, 'dup': dup_id})
                await session.execute(text('UPDATE technical_interviews SET job_id = :canon WHERE job_id = :dup'), {'canon': canonical_id, 'dup': dup_id})
                await session.execute(text('UPDATE candidates SET job_id = :canon WHERE job_id = :dup'), {'canon': canonical_id, 'dup': dup_id})

                # 5. Delete duplicate job opening
                await session.execute(text('DELETE FROM job_openings WHERE id = :dup'), {'dup': dup_id})

        await session.commit()
        res_rem_jobs = await session.execute(text('SELECT COUNT(*) FROM job_openings'))
        print(f"Job Openings deduplication complete. Total unique jobs remaining: {res_rem_jobs.scalar()}")

        # =========================================================================
        # STEP 2: DEDUPLICATE CANDIDATES
        # =========================================================================
        print("\n--- [Step 2] Deduplicating Candidates ---")
        res_cand_groups = await session.execute(text('''
            SELECT LOWER(name), COUNT(*)
            FROM candidates
            GROUP BY LOWER(name)
            HAVING COUNT(*) > 1
        '''))
        cand_groups = res_cand_groups.fetchall()
        print(f"Found {len(cand_groups)} duplicate candidate name groups.")

        for name_lower, cnt in cand_groups:
            res_items = await session.execute(text('''
                SELECT id, email, github_username, created_at 
                FROM candidates 
                WHERE LOWER(name) = :name 
                ORDER BY 
                    (email IS NOT NULL AND email != '') DESC,
                    (github_username IS NOT NULL AND github_username != '' AND github_username != 'none') DESC,
                    created_at DESC, 
                    id DESC
            '''), {'name': name_lower})
            rows = res_items.fetchall()
            canonical_cand_id = rows[0][0]
            dup_cand_ids = [r[0] for r in rows[1:]]

            for dup_id in dup_cand_ids:
                # 1. github_profiles (unique constraint on candidate_id)
                res_canon_gh = await session.execute(text('SELECT id FROM github_profiles WHERE candidate_id = :cid'), {'cid': canonical_cand_id})
                if res_canon_gh.scalar():
                    await session.execute(text('DELETE FROM github_profiles WHERE candidate_id = :dup'), {'dup': dup_id})
                else:
                    await session.execute(text('UPDATE github_profiles SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})

                # 2. candidate_job_evidence_audits (unique constraint on candidate_id, job_id)
                await session.execute(text('''
                    DELETE FROM candidate_job_evidence_audits 
                    WHERE candidate_id = :dup 
                    AND job_id IN (SELECT job_id FROM candidate_job_evidence_audits WHERE candidate_id = :canon)
                '''), {'dup': dup_id, 'canon': canonical_cand_id})
                await session.execute(text('UPDATE candidate_job_evidence_audits SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})

                # 3. job_match_scores (unique constraint on candidate_id, job_id)
                await session.execute(text('''
                    DELETE FROM job_match_scores 
                    WHERE candidate_id = :dup 
                    AND job_id IN (SELECT job_id FROM job_match_scores WHERE candidate_id = :canon)
                '''), {'dup': dup_id, 'canon': canonical_cand_id})
                await session.execute(text('UPDATE job_match_scores SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})

                # 4. Other child tables
                await session.execute(text('UPDATE audits SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})
                await session.execute(text('UPDATE candidate_assessments SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})
                await session.execute(text('UPDATE applications SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})
                await session.execute(text('UPDATE resumes SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})
                await session.execute(text('UPDATE technical_interviews SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})
                await session.execute(text('UPDATE evidence_nodes SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})
                await session.execute(text('UPDATE generated_replies SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})
                await session.execute(text('UPDATE pipeline_stages SET candidate_id = :canon WHERE candidate_id = :dup'), {'canon': canonical_cand_id, 'dup': dup_id})

                # 5. Delete duplicate candidate
                await session.execute(text('DELETE FROM candidates WHERE id = :dup'), {'dup': dup_id})

        await session.commit()
        res_rem_cand = await session.execute(text('SELECT COUNT(*) FROM candidates'))
        print(f"Candidates deduplication complete. Total unique candidates remaining: {res_rem_cand.scalar()}")

        # =========================================================================
        # STEP 3: DEDUPLICATE CANDIDATE ASSESSMENTS
        # =========================================================================
        print("\n--- [Step 3] Deduplicating Candidate Assessments ---")
        res_ca_groups = await session.execute(text('''
            SELECT candidate_id, COALESCE(job_id, '00000000-0000-0000-0000-000000000000'::uuid), COUNT(*)
            FROM candidate_assessments
            GROUP BY candidate_id, COALESCE(job_id, '00000000-0000-0000-0000-000000000000'::uuid)
            HAVING COUNT(*) > 1
        '''))
        ca_groups = res_ca_groups.fetchall()
        print(f"Found {len(ca_groups)} duplicate candidate assessment groups.")

        for cand_id, job_id, cnt in ca_groups:
            if str(job_id) == '00000000-0000-0000-0000-000000000000':
                res_items = await session.execute(text('''
                    SELECT id FROM candidate_assessments 
                    WHERE candidate_id = :cid AND job_id IS NULL
                    ORDER BY score DESC, created_at DESC
                '''), {'cid': cand_id})
            else:
                res_items = await session.execute(text('''
                    SELECT id FROM candidate_assessments 
                    WHERE candidate_id = :cid AND job_id = :jid
                    ORDER BY score DESC, created_at DESC
                '''), {'cid': cand_id, 'jid': job_id})
            rows = res_items.fetchall()
            dup_cas = [r[0] for r in rows[1:]]
            for dup_ca in dup_cas:
                await session.execute(text('DELETE FROM candidate_assessments WHERE id = :id'), {'id': dup_ca})

        await session.commit()
        res_rem_ca = await session.execute(text('SELECT COUNT(*) FROM candidate_assessments'))
        print(f"Candidate Assessments deduplication complete. Remaining: {res_rem_ca.scalar()}")

        # =========================================================================
        # STEP 4: DEDUPLICATE APPLICATIONS
        # =========================================================================
        print("\n--- [Step 4] Deduplicating Applications ---")
        res_app_groups = await session.execute(text('''
            SELECT candidate_id, COALESCE(job_id, '00000000-0000-0000-0000-000000000000'::uuid), COUNT(*)
            FROM applications
            GROUP BY candidate_id, COALESCE(job_id, '00000000-0000-0000-0000-000000000000'::uuid)
            HAVING COUNT(*) > 1
        '''))
        app_groups = res_app_groups.fetchall()
        print(f"Found {len(app_groups)} duplicate application groups.")

        for cand_id, job_id, cnt in app_groups:
            if str(job_id) == '00000000-0000-0000-0000-000000000000':
                res_items = await session.execute(text('''
                    SELECT id FROM applications 
                    WHERE candidate_id = :cid AND job_id IS NULL
                    ORDER BY created_at DESC
                '''), {'cid': cand_id})
            else:
                res_items = await session.execute(text('''
                    SELECT id FROM applications 
                    WHERE candidate_id = :cid AND job_id = :jid
                    ORDER BY created_at DESC
                '''), {'cid': cand_id, 'jid': job_id})
            rows = res_items.fetchall()
            canonical_app = rows[0][0]
            dup_apps = [r[0] for r in rows[1:]]

            for dup_app in dup_apps:
                await session.execute(text('UPDATE audits SET application_id = :canon WHERE application_id = :dup'), {'canon': canonical_app, 'dup': dup_app})
                await session.execute(text('UPDATE pipeline_stages SET application_id = :canon WHERE application_id = :dup'), {'canon': canonical_app, 'dup': dup_app})
                await session.execute(text('DELETE FROM applications WHERE id = :dup'), {'dup': dup_app})

        await session.commit()
        res_rem_app = await session.execute(text('SELECT COUNT(*) FROM applications'))
        print(f"Applications deduplication complete. Remaining: {res_rem_app.scalar()}")

        # =========================================================================
        # STEP 5: DEDUPLICATE RESUMES & CLAIMS
        # =========================================================================
        print("\n--- [Step 5] Deduplicating Resumes & Claims ---")
        res_res_groups = await session.execute(text('''
            SELECT candidate_id, COUNT(*)
            FROM resumes
            GROUP BY candidate_id
            HAVING COUNT(*) > 1
        '''))
        res_groups = res_res_groups.fetchall()
        print(f"Found {len(res_groups)} candidates with multiple resume uploads.")

        for cand_id, cnt in res_groups:
            res_items = await session.execute(text('''
                SELECT id FROM resumes 
                WHERE candidate_id = :cid 
                ORDER BY created_at DESC
            '''), {'cid': cand_id})
            rows = res_items.fetchall()
            dup_resumes = [r[0] for r in rows[1:]]
            for dup_res in dup_resumes:
                await session.execute(text('DELETE FROM resume_claims WHERE resume_id = :rid'), {'rid': dup_res})
                await session.execute(text('DELETE FROM resumes WHERE id = :rid'), {'rid': dup_res})

        await session.commit()
        res_rem_resumes = await session.execute(text('SELECT COUNT(*) FROM resumes'))
        res_rem_claims = await session.execute(text('SELECT COUNT(*) FROM resume_claims'))
        print(f"Resumes deduplication complete. Remaining resumes: {res_rem_resumes.scalar()}, claims: {res_rem_claims.scalar()}")

        # =========================================================================
        # STEP 6: DEDUPLICATE ORGANIZATIONS
        # =========================================================================
        print("\n--- [Step 6] Deduplicating Organizations ---")
        demo_slug = "demo-workspace"
        res_org_groups = await session.execute(text('''
            SELECT LOWER(name), COUNT(*)
            FROM organizations
            GROUP BY LOWER(name)
            HAVING COUNT(*) > 1
        '''))
        org_groups = res_org_groups.fetchall()
        print(f"Found {len(org_groups)} duplicate organization name groups.")

        for org_name, cnt in org_groups:
            res_items = await session.execute(text('''
                SELECT id, slug, created_at 
                FROM organizations 
                WHERE LOWER(name) = :name 
                ORDER BY 
                    (slug = :demo_slug) DESC,
                    created_at ASC
            '''), {'name': org_name, 'demo_slug': demo_slug})
            rows = res_items.fetchall()
            canonical_org_id = rows[0][0]
            dup_org_ids = [r[0] for r in rows[1:]]

            for dup_org_id in dup_org_ids:
                # Memberships unique constraint on (user_id, organization_id)
                await session.execute(text('''
                    DELETE FROM memberships 
                    WHERE organization_id = :dup 
                    AND user_id IN (SELECT user_id FROM memberships WHERE organization_id = :canon)
                '''), {'dup': dup_org_id, 'canon': canonical_org_id})
                await session.execute(text('UPDATE memberships SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})

                # Re-point child records
                await session.execute(text('UPDATE candidates SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE job_openings SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE job_assessments SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE candidate_assessments SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE applications SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE resumes SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE audits SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE technical_interviews SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE pipeline_stages SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE audit_logs SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE jobs SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE email_connections SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                await session.execute(text('UPDATE generated_replies SET organization_id = :canon WHERE organization_id = :dup'), {'canon': canonical_org_id, 'dup': dup_org_id})
                
                # Delete duplicate organization
                await session.execute(text('DELETE FROM organizations WHERE id = :dup'), {'dup': dup_org_id})

        await session.commit()
        res_rem_orgs = await session.execute(text('SELECT COUNT(*) FROM organizations'))
        print(f"Organizations deduplication complete. Total unique organizations remaining: {res_rem_orgs.scalar()}")

        # =========================================================================
        # STEP 7: CLEAN UP NON-RESUME ARTIFACTS
        # =========================================================================
        print("\n--- [Step 7] Pruning Non-Resume Placeholder Artifacts ---")
        res_inv = await session.execute(text('''
            SELECT id FROM candidates 
            WHERE LOWER(name) IN ('non-resume document', 'corrupt document', 'invalid document')
        '''))
        inv_ids = [r[0] for r in res_inv.fetchall()]
        print(f"Found {len(inv_ids)} invalid/test document placeholder candidates.")
        for inv_id in inv_ids:
            await session.execute(text('DELETE FROM candidate_assessments WHERE candidate_id = :id'), {'id': inv_id})
            await session.execute(text('DELETE FROM applications WHERE candidate_id = :id'), {'id': inv_id})
            await session.execute(text('DELETE FROM resumes WHERE candidate_id = :id'), {'id': inv_id})
            await session.execute(text('DELETE FROM audits WHERE candidate_id = :id'), {'id': inv_id})
            await session.execute(text('DELETE FROM candidates WHERE id = :id'), {'id': inv_id})

        await session.commit()
        print("Non-resume placeholders cleaned.")

        # =========================================================================
        # SUMMARY
        # =========================================================================
        res_final_cand = await session.execute(text('SELECT COUNT(*) FROM candidates'))
        res_final_jobs = await session.execute(text('SELECT COUNT(*) FROM job_openings'))
        res_final_orgs = await session.execute(text('SELECT COUNT(*) FROM organizations'))
        res_final_apps = await session.execute(text('SELECT COUNT(*) FROM applications'))
        res_final_res = await session.execute(text('SELECT COUNT(*) FROM resumes'))
        res_final_claims = await session.execute(text('SELECT COUNT(*) FROM resume_claims'))

        print("\n=======================================================")
        print("🎉 COMPREHENSIVE DEDUPLICATION SUMMARY:")
        print(f"  • Unique Organizations: {res_final_orgs.scalar()}")
        print(f"  • Unique Job Openings:  {res_final_jobs.scalar()}")
        print(f"  • Unique Candidates:    {res_final_cand.scalar()}")
        print(f"  • Unique Resumes:       {res_final_res.scalar()}")
        print(f"  • Unique Claims:        {res_final_claims.scalar()}")
        print(f"  • Unique Applications:  {res_final_apps.scalar()}")
        print("=======================================================")

if __name__ == '__main__':
    asyncio.run(deduplicate_all())
