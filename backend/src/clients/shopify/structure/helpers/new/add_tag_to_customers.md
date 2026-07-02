Status: decide (mixed — CLI utility + business flow)
Path: backend/src/clients/shopify/add_tag_to_customers.py

Standalone script that lives inside the client dir. Not part of the client
surface proper; wants a home either under a `scripts/` dir or absorbed into a
`customers` service module. Revisit once the codegen client is unified.
