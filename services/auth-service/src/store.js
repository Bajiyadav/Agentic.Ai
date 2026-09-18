import crypto from 'crypto';
import bcrypt from 'bcryptjs';
import { config } from './config.js';

export class AuthStore {
  constructor() {
    this.users = new Map();
    this.organizations = new Map();
    this.memberships = new Map(); // key: userId:orgId
    this.refreshTokens = new Set();
    this.auditLogs = [];
    this._seedInitialData();
  }

  _seedInitialData() {
    // 1. Seed Organizations
    const acmeOrg = {
      id: '897c74c7-b22b-4e78-8a64-a8c72ba10461',
      name: 'Acme Corporation',
      slug: 'acme-corp',
      plan_tier: 'growth',
      monthly_resume_limit: 500,
      monthly_resumes_used: 42,
      created_at: new Date().toISOString()
    };

    const techCorpOrg = {
      id: '550e8400-e29b-41d4-a716-446655440000',
      name: 'TechCorp Solutions',
      slug: 'techcorp-solutions',
      plan_tier: 'enterprise',
      monthly_resume_limit: 2000,
      monthly_resumes_used: 138,
      created_at: new Date().toISOString()
    };

    this.organizations.set(acmeOrg.id, acmeOrg);
    this.organizations.set(techCorpOrg.id, techCorpOrg);

    // Default password hash for "DemoAudit123!"
    const defaultPasswordHash = bcrypt.hashSync('DemoAudit123!', config.SALT_ROUNDS);

    // 2. Seed Users
    const sarah = {
      id: 'u-sarah-jenkins-001',
      email: 'sarah@acmecorp.com',
      hashed_password: defaultPasswordHash,
      full_name: 'Sarah Jenkins',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString()
    };

    const alex = {
      id: 'u-alex-mercer-002',
      email: 'alex@acmecorp.com',
      hashed_password: defaultPasswordHash,
      full_name: 'Alex Mercer',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString()
    };

    const candidate = {
      id: 'u-baddela-003',
      email: 'baddela.yadav@gmail.com',
      hashed_password: defaultPasswordHash,
      full_name: 'Baddela Yadav',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString()
    };

    this.users.set(sarah.id, sarah);
    this.users.set(alex.id, alex);
    this.users.set(candidate.id, candidate);

    // 3. Seed Memberships (User <-> Organization <-> Role)
    this.addMembership(sarah.id, acmeOrg.id, 'owner');
    this.addMembership(alex.id, acmeOrg.id, 'admin');
    this.addMembership(sarah.id, techCorpOrg.id, 'recruiter');
    this.addMembership(candidate.id, acmeOrg.id, 'candidate');
  }

  // --- Users ---
  findUserByEmail(email) {
    const normalized = email.toLowerCase().trim();
    for (const user of this.users.values()) {
      if (user.email.toLowerCase() === normalized) {
        return user;
      }
    }
    return null;
  }

  findUserById(id) {
    return this.users.get(id) || null;
  }

  createUser({ email, password, full_name }) {
    const id = crypto.randomUUID();
    const hashed_password = bcrypt.hashSync(password, config.SALT_ROUNDS);
    const user = {
      id,
      email: email.toLowerCase().trim(),
      hashed_password,
      full_name: full_name.trim(),
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString()
    };
    this.users.set(id, user);
    return user;
  }

  // --- Organizations ---
  findOrganizationById(id) {
    return this.organizations.get(id) || null;
  }

  findOrganizationBySlug(slug) {
    for (const org of this.organizations.values()) {
      if (org.slug === slug) return org;
    }
    return null;
  }

  createOrganization({ name, plan_tier = 'starter', monthly_limit = 100 }) {
    const id = crypto.randomUUID();
    const slugBase = name.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').slice(0, 30);
    const slug = `${slugBase}-${crypto.randomBytes(3).toString('hex')}`;
    const org = {
      id,
      name,
      slug,
      plan_tier,
      monthly_resume_limit: monthly_limit,
      monthly_resumes_used: 0,
      created_at: new Date().toISOString()
    };
    this.organizations.set(id, org);
    return org;
  }

  // --- Memberships & RBAC ---
  addMembership(userId, organizationId, role = 'recruiter') {
    const key = `${userId}:${organizationId}`;
    const membership = {
      id: crypto.randomUUID(),
      user_id: userId,
      organization_id: organizationId,
      role, // 'owner' | 'admin' | 'recruiter' | 'hiring_manager' | 'candidate'
      created_at: new Date().toISOString()
    };
    this.memberships.set(key, membership);
    return membership;
  }

  getMembershipsForUser(userId) {
    const result = [];
    for (const [key, membership] of this.memberships.entries()) {
      if (membership.user_id === userId) {
        const org = this.findOrganizationById(membership.organization_id);
        if (org) {
          result.push({
            organization_id: org.id,
            organization_name: org.name,
            organization_slug: org.slug,
            plan_tier: org.plan_tier,
            role: membership.role
          });
        }
      }
    }
    return result;
  }

  getMembership(userId, organizationId) {
    const key = `${userId}:${organizationId}`;
    return this.memberships.get(key) || null;
  }

  // --- Refresh Tokens ---
  addRefreshToken(token) {
    this.refreshTokens.add(token);
  }

  hasRefreshToken(token) {
    return this.refreshTokens.has(token);
  }

  revokeRefreshToken(token) {
    this.refreshTokens.delete(token);
  }

  // --- Audit Log ---
  logAudit({ organization_id, actor_id, action, target_type, target_id, details }) {
    const entry = {
      id: crypto.randomUUID(),
      organization_id,
      actor_id,
      action,
      target_type,
      target_id,
      details,
      timestamp: new Date().toISOString()
    };
    this.auditLogs.push(entry);
    return entry;
  }
}

// Export singleton instance
export const authStore = new AuthStore();
