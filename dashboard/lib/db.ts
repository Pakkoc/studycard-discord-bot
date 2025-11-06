import { Pool, PoolConfig } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var __pgPool: Pool | undefined;
}

function createPool(): Pool {
  // Development convenience: avoid self-signed cert issues locally only
  if (process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-process-env
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
  }
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is not set");
  }

  const config: PoolConfig = {
    connectionString: databaseUrl,
    // Supabase requires SSL. Disable strict cert validation for local/dev.
    ssl: { rejectUnauthorized: false },
    max: 5,
  };
  return new Pool(config);
}

export function getPool(): Pool {
  if (!global.__pgPool) {
    global.__pgPool = createPool();
  }
  return global.__pgPool;
}


