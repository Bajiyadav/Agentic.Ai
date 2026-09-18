import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables from repo root or local directory
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });
dotenv.config({ path: path.resolve(__dirname, '../.env') });

export const config = {
  PORT: process.env.AUTH_PORT ? parseInt(process.env.AUTH_PORT, 10) : 8001,
  JWT_SECRET: process.env.SECRET_KEY || process.env.JWT_SECRET || '3-wYk2BafHEbBZXTBNbByPMb03q9ui9OQMiIDyIsRZA',
  JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '24h',
  REFRESH_SECRET: process.env.REFRESH_SECRET || 'auditagent-super-secret-refresh-key-2026-secure',
  REFRESH_EXPIRES_IN: process.env.REFRESH_EXPIRES_IN || '7d',
  SALT_ROUNDS: 10,
  DEFAULT_MONTHLY_LIMIT: 100
};
