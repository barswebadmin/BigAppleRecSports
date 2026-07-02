Status: drop (ad-hoc, script-embedded)
Resource: Order
Path: backend/lib/clients/shopify_client_old/get_orders_by_contact.py:65 (inline `"""query searchOrders …"""`)
Replacement: `OrdersGet(query="email:… OR phone:…", first=…)`

Inline op inside a one-off CSV-export CLI. Selection set is smaller than
`OrdersGet` — a straight substitution + column projection at the script side.
Script itself is a candidate for retirement.
