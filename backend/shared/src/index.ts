import { loadEnv } from "@shared/utils/loadEnv";

loadEnv();

const URL = process.env.SHOPIFY_GRAPHQL_URL

console.log(`✅ Loaded .env values! url: ${URL}`);