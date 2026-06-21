"""Orders module — controllers and services.

Stage 5 § 5.f added ``modules.orders.controllers.orders_controller`` for
the ``DELETE /orders/{order_id}`` route. Importers should target the
specific submodule they need (``modules.orders.controllers.orders_controller``
for the router, ``modules.orders.services.orders_service`` for the
service class) — the package-level eager re-export of ``OrdersService``
that previously lived here was removed because it pulled in
``modules.integrations.shopify`` transitively at import time, which
broke any code path that only needed the new controllers.
"""
