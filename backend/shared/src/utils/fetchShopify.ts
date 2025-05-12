import { loadEnv } from "./loadEnv"

loadEnv();
const DEFAULT_SHOPIFY_TOKEN = process.env.SHOPIFY_ACCESS_TOKEN
const DEFAULT_SHOPIFY_GRAPHQL_URL = process.env.SHOPIFY_GRAPHQL_URL

export const fetchShopify = async (query: string, variables: Record<string, unknown> = {}, endpoint: string | undefined = DEFAULT_SHOPIFY_GRAPHQL_URL, accessToken: string | undefined = DEFAULT_SHOPIFY_TOKEN) => {
  
	if (!endpoint || !accessToken) throw new Error('incorrect access token or endpoint!')
		
	const res = await fetch(endpoint, {
	  method: "POST",
	  headers: {
		"Content-Type": "application/json",
		"X-Shopify-Access-Token": accessToken,
	  },
	  body: JSON.stringify({ query, variables }),
	});
  
	return await res.json();
  };