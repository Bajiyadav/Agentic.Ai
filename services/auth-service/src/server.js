import express from 'express';
import cors from 'cors';
import { config } from './config.js';
import { authRouter } from './routes/auth.js';
import { authenticateToken, requireRole } from './middleware/auth.js';

export const app = express();

// Security & Parsing Middlewares
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json({ limit: '2mb' }));

// Telemetry Timing Middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    if (process.env.NODE_ENV !== 'test') {
      console.log(`[AUTH ${req.method}] ${req.originalUrl} - ${res.statusCode} (${duration}ms)`);
    }
  });
  next();
});

// Health Check Endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'auditagent-auth-service',
    engine: 'Node.js',
    node_version: process.version,
    timestamp: new Date().toISOString(),
    uptime_seconds: Math.floor(process.uptime())
  });
});

// Mount Auth & Multi-Tenancy Router
app.use('/api/v1/auth', authRouter);

// ================= RBAC PROTECTED ROUTE DEMONSTRATIONS =================
// 1. Recruiter / Admin only
app.get('/api/v1/recruiter/protected-action', authenticateToken, requireRole('recruiter', 'admin'), (req, res) => {
  res.json({
    message: 'Access granted to Recruiter/Admin protected action',
    user: req.user.email,
    role: req.tenant.role,
    organization_id: req.tenant.organization_id
  });
});

// 2. Admin / Owner only
app.post('/api/v1/admin/protected-settings', authenticateToken, requireRole('admin'), (req, res) => {
  res.json({
    message: 'Access granted to Admin-only organization settings',
    user: req.user.email,
    role: req.tenant.role
  });
});

// 3. Candidate Portal access
app.get('/api/v1/candidate/protected-assessment', authenticateToken, requireRole('candidate', 'recruiter'), (req, res) => {
  res.json({
    message: 'Access granted to Candidate proctored assessment portal',
    candidate_email: req.user.email,
    role: req.tenant.role
  });
});

// 404 Handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    detail: `Route ${req.method} ${req.originalUrl} not found.`
  });
});

// Global Error Handler
app.use((err, req, res, next) => {
  console.error('[AUTH ERROR]', err);
  res.status(500).json({
    error: 'Internal Server Error',
    detail: err.message || 'An unexpected error occurred.'
  });
});

import { fileURLToPath } from 'url';

// Start Server if run directly as main entry point
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const server = app.listen(config.PORT, () => {
    console.log(`🚀 AuditAgent Node.js Auth & RBAC Service running on http://localhost:${config.PORT}`);
    console.log(`   Health Check: http://localhost:${config.PORT}/health`);
    console.log(`   Auth API:     http://localhost:${config.PORT}/api/v1/auth`);
  });

  process.on('SIGTERM', () => {
    console.log('SIGTERM signal received. Closing auth server gracefully...');
    server.close(() => process.exit(0));
  });
}
