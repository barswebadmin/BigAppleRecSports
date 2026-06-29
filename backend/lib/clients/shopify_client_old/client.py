"""Shopify Admin GraphQL client."""

from typing import Any, cast

import requests

from shared_utilities.config import Config

from .gql import GqlQuery, GqlResult, build_shopify_gid
from .queries import (
    AdjustInventory,
    FileUpdateProductRef,
    GetCustomer,
    GetInventoryInfo,
    GetOrdersByProduct,
    GetProduct,
    GetVariant,
    SearchCustomerByEmail,
    SearchCustomersByEmails,
    UpdateCustomerTags,
    UpdateProduct,
    BulkUpdateVariantPrices,
)


class ShopifyClient:
    """Thin Shopify Admin GraphQL client.

    Config is read from env vars at instantiation time — populated from .env
    locally, Render dashboard on Render, or Lambda environment variables.
    """

    def __init__(self) -> None:
        shopify_config = Config().shopify
        self.url = shopify_config.url.api_graph_ql
        self.token = shopify_config.token.admin
        self.location_id = shopify_config.location_id
        self.store_id = shopify_config.store_id

    # ── identifier helpers ────────────────────────────────────────

    def build_url(
        self, resource_type: str, id_value: str | int
    ) -> str:
        """Build a Shopify admin URL using this client's store_id."""
        slug = resource_type.lower().rstrip("s") + "s"
        id_slug = str(id_value).rsplit("/", maxsplit=1)[-1]
        return (
            f"https://admin.shopify.com/store/"
            f"{self.store_id}/{slug}/{id_slug}"
        )

    def parse_identifier(
        self,
        resource_type: str,
        identifier: str | int,
    ) -> dict[str, str] | None:
        """Normalise a Shopify identifier (GID, admin URL, or bare ID).

        Returns a dict with keys: id, gid, url — or None if empty.
        """
        if not identifier:
            return None

        identifier = str(identifier)
        first_5 = identifier[:5]

        if first_5 == "gid:/":
            resource_id = identifier.rsplit("/", maxsplit=1)[-1]
            return {
                "id": resource_id,
                "gid": identifier,
                "url": self.build_url(resource_type, resource_id),
            }

        if first_5 == "https":
            resource_id = identifier.rsplit("/", maxsplit=1)[-1]
            return {
                "id": resource_id,
                "gid": build_shopify_gid(resource_type, resource_id),
                "url": identifier,
            }

        return {
            "id": identifier,
            "gid": build_shopify_gid(resource_type, identifier),
            "url": self.build_url(resource_type, identifier),
        }

    # ── core ──────────────────────────────────────────────────────

    def send_request(
        self, query_type: type[GqlQuery], **kwargs: Any
    ) -> GqlResult:
        """Instantiate query_type, build the request, POST it,
        parse the response."""
        gql = query_type()
        query, variables = gql.build_query(**kwargs)
        response = requests.post(
            self.url,
            json={"query": query, "variables": variables},
            headers={
                "X-Shopify-Access-Token": self.token,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        return gql.parse_response(response)

    # ── private helpers ───────────────────────────────────────────

    def _get_variant_node(
        self, variant_id: str | int
    ) -> GqlResult:
        return self.send_request(
            GetInventoryInfo, variant_id=variant_id
        )

    def _adjust_inventory_for_variant(
        self, variant_id: str | int, delta: int
    ) -> GqlResult:
        data, errors = self._get_variant_node(variant_id)
        if errors or data is None:
            return None, errors
        inventory_item_id = data["inventoryItem"]["id"]
        return self.send_request(
            AdjustInventory,
            inventory_item_id=inventory_item_id,
            location_gid=build_shopify_gid(
                "Location", self.location_id
            ),
            delta=delta,
        )

    def update_product(
        self,
        product_id: str | int,
        *,
        new_image_id: int | str | None = None,
        current_media_ids: list[str] | None = None,
        **fields: Any,
    ) -> GqlResult:
        """Send a productUpdate mutation, then swap media if
        new_image_id is provided.

        Uses fileUpdate(referencesToAdd/referencesToRemove) to
        associate/disassociate library files from the product —
        this preserves source files in Content > Files.
        """
        _, errors = self.send_request(
            UpdateProduct, product_id=product_id, **fields
        )
        if errors:
            return None, errors

        if new_image_id is not None:
            _, errors = self.send_request(
                FileUpdateProductRef,
                file_id=new_image_id,
                product_id=product_id,
                attach=True,
            )
            if errors:
                return None, errors

            new_id_str = str(new_image_id)
            for gid in current_media_ids or []:
                existing_id = gid.rsplit("/", 1)[-1]
                if existing_id != new_id_str:
                    self.send_request(
                        FileUpdateProductRef,
                        file_id=existing_id,
                        product_id=product_id,
                        attach=False,
                    )

        return None, None

    # ── public API ────────────────────────────────────────────────

    def get_product(self, identifier: str | int) -> GqlResult:
        """Fetch a product by any identifier (GID, admin URL,
        or numeric ID)."""
        ref = self.parse_identifier("Product", identifier)
        if not ref:
            return None, [{"message": "Invalid product identifier"}]
        data, errors = self.send_request(
            GetProduct, product_id=ref["id"]
        )
        if errors or data is None:
            return None, errors
        data.update(ref)
        return data, None

    def get_variant(self, identifier: str | int) -> GqlResult:
        """Fetch a variant by any identifier (GID, admin URL,
        or numeric ID)."""
        ref = self.parse_identifier("ProductVariant", identifier)
        if not ref:
            return None, [{"message": "Invalid variant identifier"}]
        data, errors = self.send_request(
            GetVariant, variant_id=ref["id"]
        )
        if errors or data is None:
            return None, errors
        data.update(ref)
        return data, None

    def get_product_variants(
        self, product_id: str | int
    ) -> GqlResult:
        """Return the variants list for a product."""
        data, errors = self.get_product(product_id)
        if errors or data is None:
            return None, errors
        return data["variants"]["nodes"], None

    def get_variant_inventory(
        self, variant_id: str | int
    ) -> GqlResult:
        """Return the available inventory quantity for a variant."""
        data, errors = self._get_variant_node(variant_id)
        if errors or data is None:
            return None, errors
        return data["inventoryQuantity"], None

    def set_product_title(
        self, product_id: str | int, new_title: str
    ) -> GqlResult:
        """Update a product's title."""
        return self.update_product(product_id, title=new_title)

    def bulk_update_variant_prices(
        self,
        product_id: str | int,
        variant_prices: list[dict],
    ) -> GqlResult:
        """Update prices for multiple variants in one mutation."""
        return self.send_request(
            BulkUpdateVariantPrices,
            product_id=product_id,
            variant_prices=variant_prices,
        )

    def add_inventory_to_variant(
        self, variant_id: str | int, units: int
    ) -> GqlResult:
        """Add inventory units to a variant."""
        if units <= 0:
            raise ValueError(f"units must be positive, got {units}")
        return self._adjust_inventory_for_variant(variant_id, units)

    def remove_inventory_from_variant(
        self, variant_id: str | int, units: int
    ) -> GqlResult:
        """Remove inventory units from a variant."""
        if units <= 0:
            raise ValueError(f"units must be positive, got {units}")
        return self._adjust_inventory_for_variant(
            variant_id, -units
        )

    def drain_inventory_from_variant(
        self, variant_id: str | int, units: int
    ) -> int:
        """Remove as much inventory as possible, retrying with
        one less unit on each failure.

        Returns the number of units actually removed.
        """
        attempt = units
        while attempt > 0:
            _, errors = self.remove_inventory_from_variant(
                variant_id, attempt
            )
            if not errors:
                return attempt
            print(
                f"   ⚠️  Remove {attempt} failed ({errors})"
                f" — retrying with {attempt - 1}"
            )
            attempt -= 1
        return 0

    def add_tag(
        self,
        resource_type: str,
        resource_id: str | int,
        tag: str,
    ) -> GqlResult:
        """Add a tag to a product or customer.

        Args:
            resource_type: "product" or "customer"
            resource_id: ID (GID, admin URL, numeric) or email
            tag: Tag to add
        """
        resource_type_lower = resource_type.lower()

        if resource_type_lower == "product":
            return self._add_product_tag(resource_id, tag)

        if resource_type_lower == "customer":
            return self._add_customer_tag(resource_id, tag)

        return None, [
            {
                "message": (
                    f"Invalid resource_type: {resource_type}."
                    " Must be 'product' or 'customer'"
                )
            }
        ]

    def _add_product_tag(
        self, resource_id: str | int, tag: str
    ) -> GqlResult:
        ref = self.parse_identifier("Product", resource_id)
        if not ref:
            return None, [{"message": "Invalid product identifier"}]

        data, errors = self.get_product(ref["id"])
        if errors or data is None:
            return None, errors

        existing_tags = data.get("tags", [])
        if tag in existing_tags:
            return data, None

        return self.send_request(
            UpdateProduct,
            product_id=ref["id"],
            tags=existing_tags + [tag],
        )

    def _add_customer_tag(
        self, resource_id: str | int, tag: str
    ) -> GqlResult:
        if "@" in str(resource_id):
            data, errors = self.send_request(
                SearchCustomerByEmail, email=str(resource_id)
            )
        else:
            ref = self.parse_identifier("Customer", resource_id)
            if not ref:
                return None, [
                    {"message": "Invalid customer identifier"}
                ]
            data, errors = self.send_request(
                GetCustomer, customer_id=ref["id"]
            )

        if errors or data is None:
            return None, errors

        existing_tags = data.get("tags", [])
        if tag in existing_tags:
            return data, None

        return self.send_request(
            UpdateCustomerTags,
            customer_id=data["id"],
            tags=existing_tags + [tag],
        )

    def get_orders_by_product(
        self,
        product_id: str | int,
        *,
        first: int = 100,
        after: str | None = None,
        created_at_min: str | None = None,
        created_at_max: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Fetch orders containing a specific product with
        pagination.

        Returns (orders_list, next_cursor) where next_cursor is
        None if no more pages.
        """
        ref = self.parse_identifier("Product", str(product_id))
        if not ref:
            return [], None

        data, errors = self.send_request(
            GetOrdersByProduct,
            product_id=ref["id"],
            first=first,
            after=after,
            created_at_min=created_at_min,
            created_at_max=created_at_max,
        )

        if errors or data is None:
            return [], None

        orders = data.get("nodes", [])
        page_info = data.get("pageInfo", {})
        next_cursor = (
            page_info.get("endCursor")
            if page_info.get("hasNextPage")
            else None
        )

        return orders, next_cursor
    def get_customer(
        self, identifier: str | int
    ) -> dict | None:
        """Fetch a customer by numeric ID, GID, or email.

        Returns the customer dict or None if not found.
        """
        if "@" in str(identifier):
            data, errors = self.send_request(
                SearchCustomerByEmail, email=str(identifier)
            )
        else:
            ref = self.parse_identifier("Customer", identifier)
            if not ref:
                return None
            data, errors = self.send_request(
                GetCustomer, customer_id=ref["id"]
            )

        if errors or not data:
            return None
        return data

    def search_customers_by_emails(
        self, emails: list[str], batch_size: int = 250
    ) -> tuple[list[dict], list[str]]:
        """Search for customers by email addresses in batches.

        Args:
            emails: List of email addresses to search for
            batch_size: Max emails per query (Shopify limit: 250)

        Returns:
            (found, not_found) where:
                found: list of {id, email, tags} dicts
                not_found: list of email strings not found in Shopify
        """
        found_by_email: dict[str, dict] = {}

        for i in range(0, len(emails), batch_size):
            chunk = emails[i:i + batch_size]
            customers, errors = self.send_request(
                SearchCustomersByEmails, emails=chunk
            )
            if errors:
                print(f"⚠️ Error searching customers batch {i//batch_size + 1}: {errors}")
                continue

            for customer in cast(list[dict[str, Any]], customers or []):
                found_by_email[customer["email"].lower()] = customer

        found = list(found_by_email.values())
        not_found = [email for email in emails if email.lower() not in found_by_email]

        return found, not_found

    def batch_update_customer_tags(
        self, updates: list[dict], batch_size: int = 75
    ) -> list[tuple[str, str]]:
        """Update customer tags in batches using aliased mutations.

        Args:
            updates: List of {id, email, tags} dicts
            batch_size: Max mutations per request (recommended: 75)

        Returns:
            List of (email, status) tuples where status is 'updated' or 'error'
        """
        import requests

        results = []

        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]

            mutations = []
            variables = {}

            for idx, customer in enumerate(batch):
                alias = f"customer{idx}"
                mutations.append(
                    f"{alias}: customerUpdate(input: $input{idx}) {{"
                    f"  customer {{ id }}"
                    f"  userErrors {{ field message }}"
                    f"}}"
                )
                variables[f"input{idx}"] = {
                    "id": customer["id"],
                    "tags": customer["tags"],
                }

            input_defs = ", ".join(f"$input{idx}: CustomerInput!" for idx in range(len(batch)))
            query = f"mutation BatchUpdateTags({input_defs}) {{ {' '.join(mutations)} }}"

            try:
                resp = requests.post(
                    self.url,
                    json={"query": query, "variables": variables},
                    headers={
                        "X-Shopify-Access-Token": self.token,
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
                resp.raise_for_status()

                data = resp.json().get("data", {})

                for idx, customer in enumerate(batch):
                    alias = f"customer{idx}"
                    result = data.get(alias, {})
                    user_errors = result.get("userErrors", [])

                    if user_errors:
                        error_msgs = "; ".join(e["message"] for e in user_errors)
                        results.append((customer["email"], f"error: {error_msgs}"))
                    elif result.get("customer"):
                        results.append((customer["email"], "updated"))
                    else:
                        results.append((customer["email"], "error: no response"))

            except requests.RequestException as e:
                for customer in batch:
                    results.append((customer["email"], f"error: {e}"))

        return results



    @staticmethod
    def order_to_csv_dict(order: dict, *, product_tags: list[str] | None = None) -> dict:
        """Convert an order dict to CSV-compatible format."""
        order_id = order.get("id", "").rsplit("/", 1)[-1]
        total_price = order.get("totalPriceSet", {})
        shop_money = total_price.get("shopMoney", {})
        customer = order.get("customer") or {}
        line_items = order.get("lineItems", {}).get("nodes", [])

        custom_attrs: dict[str, str] = {}
        for attr in order.get("customAttributes", []):
            if attr.get("key"):
                custom_attrs[f"order.{attr['key']}"] = attr["value"]
        if line_items:
            for attr in line_items[0].get("customAttributes", []):
                if attr.get("key"):
                    custom_attrs[attr["key"]] = attr.get("value", "")

        customer_tags = customer.get("tags", [])

        result = {
            "Order ID": order_id,
            "Name": order.get("name", ""),
            "Created at": order.get("createdAt", ""),
            "Total": shop_money.get("amount", "0"),
            "Currency": shop_money.get("currencyCode", "USD"),
            "Email": customer.get("email", ""),
            "First Name": customer.get("firstName", ""),
            "Last Name": customer.get("lastName", ""),
            "Customer Tags": ", ".join(customer_tags) if customer_tags else "",
            "Product Tags": ", ".join(product_tags) if product_tags else "",
            "Line Item Count": len(line_items),
        }
        result.update(custom_attrs)
        return result
