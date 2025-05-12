import { loadEnv } from "../loadEnv";
loadEnv();

export class ShopifyClientCore {
  protected endpoint: string;
  protected accessToken: string;

  constructor({
    endpoint = process.env.SHOPIFY_GRAPHQL_URL,
    accessToken = process.env.SHOPIFY_ACCESS_TOKEN,
  }: {
    endpoint?: string;
    accessToken?: string;
  } = {}) {
    if (!endpoint || !accessToken) {
      throw new Error("Missing Shopify credentials: endpoint or access token");
    }
    this.endpoint = endpoint;
    this.accessToken = accessToken;
  }

  protected async request<T = any>(query: string, variables: Record<string, unknown> = {}): Promise<T> {
    const res = await fetch(this.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": this.accessToken,
      },
      body: JSON.stringify({ query, variables }),
    });

    if (!res.ok) {
      const errorBody = await res.text();
      throw new Error(`Shopify error (${res.status}): ${errorBody}`);
    }

    return res.json();
  }
}