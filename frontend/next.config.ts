import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { parseEnv } from "node:util";
import type { NextConfig } from "next";

// Local development keeps one .env at the repo root. Only NEXT_PUBLIC_ values are loaded,
// so backend secrets does not enter the frontend process.
const rootEnv = path.resolve(process.cwd(), "..", ".env");
if (existsSync(rootEnv)) {
  for (const [key, value] of Object.entries(parseEnv(readFileSync(rootEnv, "utf8")))) {
    if (key.startsWith("NEXT_PUBLIC_") && value !== undefined) process.env[key] ??= value;
  }
}

const nextConfig: NextConfig = {
  agentRules: false,
  cacheComponents: true,
  partialPrefetching: true,
};

export default nextConfig;
