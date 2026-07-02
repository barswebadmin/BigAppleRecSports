Status: keep
Target: shopify/queries/fragments/customer.graphql
Path: backend/src/clients/shopify/queries/fragments/customer.graphql
Generated model: shopify/generated/fragments.py → `Customer`

# Customer fragment

```graphql
fragment Customer on Customer {
  id
  firstName
  lastName
  defaultEmailAddress { emailAddress }
  defaultPhoneNumber  { phoneNumber }
  createdAt
  updatedAt
  numberOfOrders
  note
  tags
  verifiedEmail
  state
}
```

Uses non-deprecated `defaultEmailAddress.emailAddress` /
`defaultPhoneNumber.phoneNumber` (not `email`/`phone`).

Composed into: `Order` fragment (as `OrderCustomer(Customer)`), `CustomersGet`,
`CustomerUpdate`.
