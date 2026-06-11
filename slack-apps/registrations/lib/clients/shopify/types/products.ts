export interface ShopifyProductVariant {
    id: string;
    title: string;
}

export interface ShopifyProduct {
    id: string;
    handle: string;
    tags: string[];
    variants: {
        nodes: ShopifyProductVariant[];
    };
}

export interface ProductQueryResult {
    ok: boolean;
    product: ShopifyProduct | null;
    error?: string;
}

// =======================================================
// GraphQL Schemas
// =======================================================

export const PRODUCT_FIELDS = `
    id
    handle
    tags
    variants(first: 10) { nodes { id title } }
`;

export const PRODUCT_BY_ID_QUERY = `
    query getProduct($id: ID!) {
        product(id: $id) { ${PRODUCT_FIELDS} }
    }
`;

export interface ProductByIdResponse {
    product: ShopifyProduct | null;
}
