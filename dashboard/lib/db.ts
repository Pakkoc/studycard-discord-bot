import { Pool, PoolConfig } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var __pgPool: Pool | undefined;
}

function createPool(): Pool {
  // Supabase uses certificates that may not be in the default trust chain.
  // Disable strict TLS validation for database connections.
  // eslint-disable-next-line no-process-env
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is not set");
  }

  const config: PoolConfig = {
    connectionString: databaseUrl,
    // Supabase requires SSL. Disable strict cert validation for local/dev.
    ssl: { rejectUnauthorized: false },
    // Supabase 무료 플랜은 동시 연결 수가 제한됨
    max: 1,
    // 연결 대기 시간 (30초)
    connectionTimeoutMillis: 30000,
    // 유휴 연결 종료 시간 (10초) - 빠르게 반환
    idleTimeoutMillis: 10000,
  };
  return new Pool(config);
}

export function getPool(): Pool {
  if (!global.__pgPool) {
    global.__pgPool = createPool();
  }
  return global.__pgPool;
}


