export interface ShopifyAddress {
    id?: string;
    address1?: string | null;
    address2?: string | null;
    city?: string | null;
    province?: string | null;
    provinceCode?: string | null;
    zip?: string | null;
    phone?: string | null;
    firstName?: string | null;
    lastName?: string | null;
}

export interface ShopifyCustomer {
    id: string;
    email: string | null;
    firstName: string | null;
    lastName: string | null;
    phone: string | null;
    tags: string[];
    note: string | null;
    state: string | null;
    createdAt: string | null;
    updatedAt: string | null;
    lastOrder: { id: string; createdAt: string } | null;
    defaultAddress: ShopifyAddress | null;
}

export interface CreateCustomerInput {
    firstName: string;
    lastName: string;
    email: string;
    phone?: string;
    tags?: string[];
    note?: string;
}

export interface UpdateCustomerInput {
    id: string;
    firstName?: string;
    lastName?: string;
    email?: string;
    phone?: string;
    tags?: string[];
    note?: string;
}

export interface CustomerOpResult {
    ok: boolean;
    customer: ShopifyCustomer | null;
    error?: string;
}

export interface ShopifyUserError {
    field: string;
    message: string;
}

export interface CustomerSearchResponse {
    customers: { nodes: ShopifyCustomer[] };
}

export interface CustomerCreateResponse {
    customerCreate: {
        customer: ShopifyCustomer | null;
        userErrors: ShopifyUserError[];
    };
}

export interface CustomerUpdateResponse {
    customerUpdate: {
        customer: ShopifyCustomer | null;
        userErrors: ShopifyUserError[];
    };
}

// =======================================================
// GraphQL Schemas
// =======================================================

export const CUSTOMER_FIELDS = `
    id email firstName lastName phone tags note
    state createdAt updatedAt
    lastOrder { id createdAt }
    defaultAddress {
        id address1 address2 city province provinceCode zip phone firstName lastName
    }
`;

export const CUSTOMER_BY_IDENTIFIER_QUERY = `
    query customerByIdentifier($identifier: CustomerIdentifierInput!) {
        customer: customerByIdentifier(identifier: $identifier) {
            ${CUSTOMER_FIELDS}
        }
    }
`;

export const CUSTOMER_SEARCH_QUERY = `
    query searchCustomer($query: String!) {
        customers(first: 1, query: $query) {
            nodes { ${CUSTOMER_FIELDS} }
        }
    }
`;

export const CUSTOMER_CREATE_MUTATION = `
    mutation customerCreate($input: CustomerInput!) {
        customerCreate(input: $input) {
            customer { ${CUSTOMER_FIELDS} }
            userErrors { field message }
        }
    }
`;

export const CUSTOMER_UPDATE_MUTATION = `
    mutation customerUpdate($input: CustomerInput!) {
        customerUpdate(input: $input) {
            customer { ${CUSTOMER_FIELDS} }
            userErrors { field message }
        }
    }
`;

export interface CustomerByIdentifierResponse {
    customer: ShopifyCustomer | null;
}
