import { requireEnv } from "./env.js";

console.log(`Running ${requireEnv("APP_NAME")}`);
