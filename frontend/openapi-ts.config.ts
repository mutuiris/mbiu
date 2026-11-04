import { defineConfig } from "@hey-api/openapi-ts";

// Generates TypeScript types and Zod schemas from the backend's contract (run `just types`).
export default defineConfig({
  input: "./src/lib/api/openapi.json",
  output: "./src/lib/api/generated",
  plugins: ["@hey-api/typescript", "zod"],
});
