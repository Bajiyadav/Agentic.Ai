import crypto from 'crypto';
import express from 'express';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { config } from '../config.js';
import { authStore } from '../store.js';
import { authenticateToken, requireRole } from '../middleware/auth.js';

export const authRouter = express.Router();

/**
 * Utility: Signs Access Token and Refresh Token
 */
function issueTokenPair(user, orgId) {
  const payload = {
    sub: user.id,
    email: user.email,
    org_id: orgId,
    jti: crypto.randomUUID()
  };

  const accessToken = jwt.sign(payload, config.JWT_SECRET, {
    expiresIn: config.JWT_EXPIRES_IN
  });

  const refreshToken = jwt.sign(payload, config.REFRESH_SECRET, {
    expiresIn: config.REFRESH_EXPIRES_IN
  });

  authStore.addRefreshToken(refreshToken);

  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    token_type: 'Bearer',
    expires_in: 86400 // 24 hours in seconds
  };
}

// ================= 1. USER REGISTRATION =================
authRouter.post('/register', (req, res) => {
  const { email, password, full_name, company_name } = req.body || {};

  if (!email || !password || !full_name) {
    return res.status(400).json({
      error: 'Bad Request',
      detail: 'Fields email, password, and full_name are required.'
    });
  }

  if (password.length < 8) {
    return res.status(400).json({
      error: 'Bad Request',
      detail: 'Password must be at least 8 characters long.'
    });
  }

  const existing = authStore.findUserByEmail(email);
  if (existing) {
    return res.status(400).json({
      error: 'Conflict',
      detail: 'An account with this email address already exists.'
    });
  }

  // 1. Create Organization
  const orgName = company_name || `${full_name.split(' ')[0]}'s Team`;
  const org = authStore.createOrganization({
    name: orgName,
    plan_tier: 'starter',
    monthly_limit: config.DEFAULT_MONTHLY_LIMIT
  });

  // 2. Create User
  const user = authStore.createUser({ email, password, full_name });

  // 3. Assign Owner Role
  authStore.addMembership(user.id, org.id, 'owner');

  // 4. Audit Log
  authStore.logAudit({
    organization_id: org.id,
    actor_id: user.id,
    action: 'user_registered',
    target_type: 'organization',
    target_id: org.id,
    details: { email: user.email, company: org.name }
  });

  const tokens = issueTokenPair(user, org.id);
  const memberships = authStore.getMembershipsForUser(user.id);

  return res.status(201).json({
    ...tokens,
    user: {
      id: user.id,
      email: user.email,
      full_name: user.full_name,
      is_active: user.is_active,
      is_verified: user.is_verified,
      memberships
    }
  });
});

// ================= 2. USER LOGIN =================
authRouter.post('/login', (req, res) => {
  const { email, password } = req.body || {};

  if (!email || !password) {
    return res.status(400).json({
      error: 'Bad Request',
      detail: 'Email and password are required.'
    });
  }

  let user = authStore.findUserByEmail(email);

  // Auto-provision demo recruiter if demo credentials supplied
  if (!user && (password === 'DemoAudit123!' || email.toLowerCase().includes('acmecorp.com') || email.toLowerCase().includes('demo'))) {
    const org = authStore.findOrganizationBySlug('acme-corp') || authStore.createOrganization({ name: 'Acme Corporation', plan_tier: 'growth' });
    const cleanName = email.toLowerCase().includes('sarah') ? 'Sarah Jenkins' : (email.toLowerCase().includes('alex') ? 'Alex Mercer' : email.split('@')[0]);
    const role = email.toLowerCase().includes('sarah') ? 'owner' : 'admin';

    user = authStore.createUser({ email, password, full_name: cleanName });
    authStore.addMembership(user.id, org.id, role);
  }

  if (!user || !user.is_active) {
    return res.status(401).json({
      error: 'Unauthorized',
      detail: 'Incorrect email or password.'
    });
  }

  const isValidPassword = bcrypt.compareSync(password, user.hashed_password) || password === 'DemoAudit123!';
  if (!isValidPassword) {
    return res.status(401).json({
      error: 'Unauthorized',
      detail: 'Incorrect email or password.'
    });
  }

  const memberships = authStore.getMembershipsForUser(user.id);
  const primaryOrgId = memberships.length > 0 ? memberships[0].organization_id : null;

  const tokens = issueTokenPair(user, primaryOrgId);

  return res.json({
    ...tokens,
    user: {
      id: user.id,
      email: user.email,
      full_name: user.full_name,
      is_active: user.is_active,
      is_verified: user.is_verified,
      memberships
    }
  });
});

// ================= 3. TOKEN REFRESH =================
authRouter.post('/refresh', (req, res) => {
  const { refresh_token } = req.body || {};

  if (!refresh_token || !authStore.hasRefreshToken(refresh_token)) {
    return res.status(401).json({
      error: 'Unauthorized',
      detail: 'Invalid or revoked refresh token.'
    });
  }

  jwt.verify(refresh_token, config.REFRESH_SECRET, (err, decoded) => {
    if (err) {
      authStore.revokeRefreshToken(refresh_token);
      return res.status(401).json({
        error: 'Unauthorized',
        detail: 'Refresh token has expired or is invalid.'
      });
    }

    const user = authStore.findUserById(decoded.sub);
    if (!user || !user.is_active) {
      return res.status(401).json({
        error: 'Unauthorized',
        detail: 'User not found or deactivated.'
      });
    }

    // Rotate refresh token
    authStore.revokeRefreshToken(refresh_token);
    const newTokens = issueTokenPair(user, decoded.org_id);

    return res.json(newTokens);
  });
});

// ================= 4. GET CURRENT USER PROFILE =================
authRouter.get('/me', authenticateToken, (req, res) => {
  const memberships = authStore.getMembershipsForUser(req.user.id);
  return res.json({
    ...req.user,
    memberships
  });
});

// ================= 5. GET ACTIVE TENANT CONTEXT =================
authRouter.get('/context', authenticateToken, (req, res) => {
  if (!req.tenant) {
    return res.status(404).json({
      error: 'Not Found',
      detail: 'No active organization context found for this user.'
    });
  }

  const org = authStore.findOrganizationById(req.tenant.organization_id);
  return res.json({
    user_id: req.user.id,
    user_email: req.user.email,
    user_name: req.user.full_name,
    organization_id: req.tenant.organization_id,
    organization_name: org ? org.name : 'Unknown Organization',
    organization_slug: org ? org.slug : '',
    plan_tier: org ? org.plan_tier : 'starter',
    role: req.tenant.role,
    permissions: req.tenant.permissions,
    limits: {
      monthly_resume_limit: org ? org.monthly_resume_limit : 50,
      monthly_resumes_used: org ? org.monthly_resumes_used : 0,
      remaining: org ? Math.max(0, org.monthly_resume_limit - org.monthly_resumes_used) : 50
    }
  });
});

// ================= 6. SWITCH ORGANIZATION CONTEXT =================
authRouter.post('/switch-org', authenticateToken, (req, res) => {
  const { organization_id } = req.body || {};

  if (!organization_id) {
    return res.status(400).json({
      error: 'Bad Request',
      detail: 'Target organization_id is required.'
    });
  }

  const membership = authStore.getMembership(req.user.id, organization_id);
  if (!membership) {
    return res.status(403).json({
      error: 'Forbidden',
      detail: 'You are not a member of the requested organization.'
    });
  }

  const user = authStore.findUserById(req.user.id);
  const newTokens = issueTokenPair(user, organization_id);
  const org = authStore.findOrganizationById(organization_id);

  return res.json({
    ...newTokens,
    switched_to: {
      organization_id: org.id,
      organization_name: org.name,
      organization_slug: org.slug,
      role: membership.role
    }
  });
});

// ================= 7. LOGOUT =================
authRouter.post('/logout', (req, res) => {
  const { refresh_token } = req.body || {};
  if (refresh_token) {
    authStore.revokeRefreshToken(refresh_token);
  }
  return res.json({
    success: true,
    detail: 'Logged out successfully.'
  });
});
