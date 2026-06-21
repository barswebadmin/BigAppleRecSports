# Registrations Service

The Shopify client (`clients.shopify`) is a module-level singleton instantiated on first import. Env variable changes (e.g. `SHOPIFY__API_TOKEN`) require redeployment to take effect. Build `reset()` / `cache_clear()` logic if hot-reload is needed later.

Public mutation methods (e.g. future `update_customer`, `cancel_order`) are responsible for checking `userErrors` in the response. Internal helpers (`_send_and_resolve`) only check top-level GQL errors (auth, throttle, syntax). This keeps internal methods agnostic and lets each public method define its own error tolerance (fail-all vs partial-success). If query vs mutation error handling diverges significantly, consider splitting `_send_and_resolve` into separate query/mutation variants.
