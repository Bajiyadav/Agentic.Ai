import jwt from 'jsonwebtoken';
import { config } from '../config.js';
import { authStore } from '../store.js';

// Canonical Role Hierarchy & Permissions
export const ROLE_PERMISSIONS = {
  owner: ['*'], // Super-admin over tenant organization
  admin: [
    'org:manage', 'user:invite', 'job:create', 'job:update', 'job:delete',
    'candidate:screen', 'candidate:upload', 'assessment:create', 'assessment:view',
    'recruiter:override', 'report:export', 'audit:view'
  ],
  recruiter: [
    'job:create', 'job:update', 'candidate:screen', 'candidate:upload',
    'assessment:view', 'interview:schedule', 'report:export'
  ],
  hiring_manager: [
    'job:view', 'scorecard:view', 'candidate:compare', 'recruiter:override',
    'assessment:view', 'report:export'
  ],
  candidate: [
    'assessment:take', 'assessment:submit'
  ]
};

/**
 * Middleware: Verifies Bearer JWT token and resolves active tenant context.
 */
export function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.startsWith('Bearer ') ? authHeader.substring(7) : null;

  if (!token) {
    return res.status(401).json({
      error: 'Unauthorized',
      detail: 'Missing or malformed Authorization header. Expected: Bearer <token>'
    });
  }

  jwt.verify(token, config.JWT_SECRET, (err, decoded) => {
    if (err) {
      const isExpired = err.name === 'TokenExpiredError';
      return res.status(401).json({
        error: isExpired ? 'Token Expired' : 'Invalid Token',
        detail: isExpired ? 'Access token has expired. Please refresh your session.' : 'Token signature verification failed.'
      });
    }

    const user = authStore.findUserById(decoded.sub);
    if (!user || !user.is_active) {
      return res.status(401).json({
        error: 'Unauthorized',
        detail: 'User account not found or is currently deactivated.'
      });
    }

    // Resolve tenant organization from token or default to first organization
    const targetOrgId = decoded.org_id;
    let membership = null;

    if (targetOrgId) {
      membership = authStore.getMembership(user.id, targetOrgId);
    }
    if (!membership) {
      const allMemberships = authStore.getMembershipsForUser(user.id);
      if (allMemberships.length > 0) {
        membership = authStore.getMembership(user.id, allMemberships[0].organization_id);
      }
    }

    req.user = {
      id: user.id,
      email: user.email,
      full_name: user.full_name,
      is_verified: user.is_verified
    };

    req.tenant = membership ? {
      organization_id: membership.organization_id,
      role: membership.role,
      permissions: ROLE_PERMISSIONS[membership.role] || []
    } : null;

    next();
  });
}

/**
 * Middleware: Enforces minimum role requirement.
 * @param  {...string} allowedRoles Roles permitted to access the route
 */
export function requireRole(...allowedRoles) {
  return (req, res, next) => {
    if (!req.tenant) {
      return res.status(403).json({
        error: 'Forbidden',
        detail: 'No active organization tenancy associated with this account.'
      });
    }

    const userRole = req.tenant.role;
    // 'owner' can access all roles
    if (userRole === 'owner' || allowedRoles.includes(userRole)) {
      return next();
    }

    return res.status(403).json({
      error: 'Forbidden',
      detail: `Role '${userRole}' is not authorized for this resource. Required one of: [${allowedRoles.join(', ')}]`
    });
  };
}

/**
 * Middleware: Enforces specific functional permissions.
 * @param  {...string} requiredPermissions
 */
export function requirePermission(...requiredPermissions) {
  return (req, res, next) => {
    if (!req.tenant) {
      return res.status(403).json({
        error: 'Forbidden',
        detail: 'No active organization tenancy context.'
      });
    }

    const userPermissions = req.tenant.permissions || [];
    if (userPermissions.includes('*')) {
      return next();
    }

    const hasAll = requiredPermissions.every(p => userPermissions.includes(p));
    if (hasAll) {
      return next();
    }

    return res.status(403).json({
      error: 'Forbidden',
      detail: `Insufficient permissions. Required: [${requiredPermissions.join(', ')}]`
    });
  };
}
