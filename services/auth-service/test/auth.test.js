import test from 'node:test';
import assert from 'node:assert/strict';
import { app } from '../src/server.js';

let server;
let baseUrl;

test.before(async () => {
  process.env.NODE_ENV = 'test';
  await new Promise((resolve) => {
    server = app.listen(0, () => {
      const port = server.address().port;
      baseUrl = `http://127.0.0.1:${port}`;
      resolve();
    });
  });
});

test.after(async () => {
  await new Promise((resolve) => {
    server.close(resolve);
  });
});

// Helper for making JSON HTTP requests
async function request(path, options = {}) {
  const url = `${baseUrl}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
  const body = options.body ? JSON.stringify(options.body) : undefined;
  const res = await fetch(url, { ...options, headers, body });
  const data = await res.json().catch(() => null);
  return { status: res.status, data, headers: res.headers };
}

test('1. Health Check Endpoint returns 200 OK', async () => {
  const res = await request('/health');
  assert.equal(res.status, 200);
  assert.equal(res.data.status, 'healthy');
  assert.equal(res.data.engine, 'Node.js');
});

test('2. User Registration happy path', async () => {
  const payload = {
    email: `founder_${Date.now()}@newstartup.io`,
    password: 'SecurePassword2026!',
    full_name: 'David Vance',
    company_name: 'Vance Capital'
  };

  const res = await request('/api/v1/auth/register', {
    method: 'POST',
    body: payload
  });

  assert.equal(res.status, 201);
  assert.ok(res.data.access_token);
  assert.ok(res.data.refresh_token);
  assert.equal(res.data.user.email, payload.email.toLowerCase());
  assert.equal(res.data.user.full_name, payload.full_name);
  assert.equal(res.data.user.memberships.length, 1);
  assert.equal(res.data.user.memberships[0].role, 'owner');
  assert.equal(res.data.user.memberships[0].organization_name, 'Vance Capital');
});

test('3. Registration rejects duplicate email or weak password', async () => {
  const email = `dupe_${Date.now()}@test.io`;

  // First registration succeeds
  await request('/api/v1/auth/register', {
    method: 'POST',
    body: { email, password: 'StrongPassword123!', full_name: 'User One' }
  });

  // Duplicate registration fails
  const dupeRes = await request('/api/v1/auth/register', {
    method: 'POST',
    body: { email, password: 'StrongPassword123!', full_name: 'User Two' }
  });
  assert.equal(dupeRes.status, 400);
  assert.match(dupeRes.data.detail, /already exists/i);

  // Short password fails
  const shortPassRes = await request('/api/v1/auth/register', {
    method: 'POST',
    body: { email: `short_${Date.now()}@test.io`, password: '123', full_name: 'Short' }
  });
  assert.equal(shortPassRes.status, 400);
  assert.match(shortPassRes.data.detail, /at least 8 characters/i);
});

test('4. Login with pre-seeded Sarah Jenkins succeeds and returns JWT', async () => {
  const res = await request('/api/v1/auth/login', {
    method: 'POST',
    body: {
      email: 'sarah@acmecorp.com',
      password: 'DemoAudit123!'
    }
  });

  assert.equal(res.status, 200);
  assert.ok(res.data.access_token);
  assert.equal(res.data.user.full_name, 'Sarah Jenkins');
  assert.ok(res.data.user.memberships.length >= 1);
});

test('5. Login with invalid password fails with 401 Unauthorized', async () => {
  const res = await request('/api/v1/auth/login', {
    method: 'POST',
    body: {
      email: 'sarah@acmecorp.com',
      password: 'WrongPassword999!'
    }
  });

  assert.equal(res.status, 401);
  assert.equal(res.data.error, 'Unauthorized');
});

test('6. GET /api/v1/auth/me returns authenticated user details', async () => {
  const loginRes = await request('/api/v1/auth/login', {
    method: 'POST',
    body: { email: 'sarah@acmecorp.com', password: 'DemoAudit123!' }
  });
  const token = loginRes.data.access_token;

  const meRes = await request('/api/v1/auth/me', {
    headers: { Authorization: `Bearer ${token}` }
  });

  assert.equal(meRes.status, 200);
  assert.equal(meRes.data.email, 'sarah@acmecorp.com');
  assert.ok(meRes.data.memberships.length > 0);
});

test('7. GET /api/v1/auth/context returns tenant ID and RBAC permissions', async () => {
  const loginRes = await request('/api/v1/auth/login', {
    method: 'POST',
    body: { email: 'sarah@acmecorp.com', password: 'DemoAudit123!' }
  });
  const token = loginRes.data.access_token;

  const ctxRes = await request('/api/v1/auth/context', {
    headers: { Authorization: `Bearer ${token}` }
  });

  assert.equal(ctxRes.status, 200);
  assert.equal(ctxRes.data.organization_slug, 'acme-corp');
  assert.equal(ctxRes.data.role, 'owner');
  assert.ok(ctxRes.data.permissions.includes('*'));
  assert.ok(ctxRes.data.limits.monthly_resume_limit >= 500);
});

test('8. Token Refresh rotates and provides a new access token', async () => {
  const loginRes = await request('/api/v1/auth/login', {
    method: 'POST',
    body: { email: 'alex@acmecorp.com', password: 'DemoAudit123!' }
  });
  const refreshToken = loginRes.data.refresh_token;

  const refreshRes = await request('/api/v1/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken }
  });

  assert.equal(refreshRes.status, 200);
  assert.ok(refreshRes.data.access_token);
  assert.ok(refreshRes.data.refresh_token);
  assert.notEqual(refreshRes.data.refresh_token, refreshToken);
});

test('9. RBAC Enforcement: Recruiter / Admin vs Candidate role', async () => {
  // Recruiter Token (Sarah)
  const sarahLogin = await request('/api/v1/auth/login', {
    method: 'POST',
    body: { email: 'sarah@acmecorp.com', password: 'DemoAudit123!' }
  });
  const recruiterToken = sarahLogin.data.access_token;

  // Candidate Token (Baddela)
  const candidateLogin = await request('/api/v1/auth/login', {
    method: 'POST',
    body: { email: 'baddela.yadav@gmail.com', password: 'DemoAudit123!' }
  });
  const candidateToken = candidateLogin.data.access_token;

  // A. Recruiter accesses recruiter-protected route -> 200 OK
  const recRes = await request('/api/v1/recruiter/protected-action', {
    headers: { Authorization: `Bearer ${recruiterToken}` }
  });
  assert.equal(recRes.status, 200);
  assert.equal(recRes.data.user, 'sarah@acmecorp.com');

  // B. Candidate attempts to access recruiter-protected route -> 403 Forbidden!
  const forbiddenRes = await request('/api/v1/recruiter/protected-action', {
    headers: { Authorization: `Bearer ${candidateToken}` }
  });
  assert.equal(forbiddenRes.status, 403);
  assert.equal(forbiddenRes.data.error, 'Forbidden');
  assert.match(forbiddenRes.data.detail, /not authorized/i);

  // C. Candidate accesses candidate proctored assessment portal -> 200 OK
  const candAssessRes = await request('/api/v1/candidate/protected-assessment', {
    headers: { Authorization: `Bearer ${candidateToken}` }
  });
  assert.equal(candAssessRes.status, 200);
  assert.equal(candAssessRes.data.candidate_email, 'baddela.yadav@gmail.com');
});

test('10. Organization Switching: Switched token carries new tenant context', async () => {
  const sarahLogin = await request('/api/v1/auth/login', {
    method: 'POST',
    body: { email: 'sarah@acmecorp.com', password: 'DemoAudit123!' }
  });
  const token = sarahLogin.data.access_token;
  const targetOrgId = '550e8400-e29b-41d4-a716-446655440000'; // TechCorp Solutions

  const switchRes = await request('/api/v1/auth/switch-org', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: { organization_id: targetOrgId }
  });

  assert.equal(switchRes.status, 200);
  assert.ok(switchRes.data.access_token);
  assert.equal(switchRes.data.switched_to.organization_id, targetOrgId);
  assert.equal(switchRes.data.switched_to.organization_name, 'TechCorp Solutions');

  // Verify /context with the new switched token reflects TechCorp Solutions
  const ctxRes = await request('/api/v1/auth/context', {
    headers: { Authorization: `Bearer ${switchRes.data.access_token}` }
  });
  assert.equal(ctxRes.status, 200);
  assert.equal(ctxRes.data.organization_id, targetOrgId);
  assert.equal(ctxRes.data.organization_name, 'TechCorp Solutions');
});

test('11. Logout revokes refresh token', async () => {
  const loginRes = await request('/api/v1/auth/login', {
    method: 'POST',
    body: { email: 'alex@acmecorp.com', password: 'DemoAudit123!' }
  });
  const refreshToken = loginRes.data.refresh_token;

  // Logout
  const logoutRes = await request('/api/v1/auth/logout', {
    method: 'POST',
    body: { refresh_token: refreshToken }
  });
  assert.equal(logoutRes.status, 200);
  assert.equal(logoutRes.data.success, true);

  // Attempting to refresh with revoked token -> 401 Unauthorized
  const refreshFail = await request('/api/v1/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken }
  });
  assert.equal(refreshFail.status, 401);
  assert.match(refreshFail.data.detail, /revoked/i);
});
