import os
import sys
import json
import argparse
import logging
from typing import Dict, Optional, List, Tuple

from dotenv import load_dotenv, find_dotenv
import yaml
from rich import print as rprint
from rich.console import Console
from rich.syntax import Syntax

from backend.config.main import Config
from backend.modules.integrations.shopify.models.requests import FetchOrderRequest
from backend.modules.orders.services.orders_service import OrdersService
from backend.modules.integrations.shopify import ShopifyClient
from backend.modules.integrations.shopify.builders.shopify_request_builders import build_order_fetch_request_payload

# Toggle CLI debug logging here
DEBUG_LOGGING: bool = True
RAW_OUTPUT: bool = False


def _ensure_env_loaded() -> None:
    # Load nearest .env (works regardless of CWD)
    try:
        load_dotenv(find_dotenv(), override=False)
    except Exception:
        pass

def _initialize_services():
    """Initialize services after environment is properly loaded."""
    # Force production config for Shopify credentials/URLs  
    os.environ["ENVIRONMENT"] = "production"
    
    # Force a fresh config instance with the new environment
    from backend.config.main import Config
    fresh_config = Config()
    
    shopify_client = ShopifyClient(fresh_config)
    orders_service = OrdersService(shopify_client)
    return shopify_client, orders_service, fresh_config

def _fetch_order_details(ident: FetchOrderRequest, orders_service: OrdersService) -> Dict:
    """Fetch order details using OrdersService (now safe from circular imports)."""
    return orders_service.fetch_order_from_shopify(request_args=ident)


def cmd_fetch_order(identifier: str) -> int:
    if identifier.startswith("id:"):
        digits = identifier.split(":", 1)[1]
        ident = FetchOrderRequest.create({"order_id": digits})
    elif identifier.startswith("number:"):
        digits = identifier.split(":", 1)[1]
        ident = FetchOrderRequest.create({"order_number": digits})
    else:
        print("Expected identifier as 'id:123' or 'number:123'", file=sys.stderr)
        return 2

    _ensure_env_loaded()
    shopify_client, orders_service, cfg = _initialize_services()

    # Enable logging if requested
    if DEBUG_LOGGING and not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    # Print debug info before request
    if DEBUG_LOGGING:
        try:
            if isinstance(ident, FetchOrderRequest) and ident.order_id:
                search = f"id:{ident.order_id}"
            else:
                order_number = getattr(ident, "order_number", None)
                search = f"name:#{order_number}"
            print(f"[DEBUG] Config Endpoint: {cfg.Shopify.graphql_url}")
            print(f"[DEBUG] Variables: {{\"q\": \"{search}\"}}")
        except Exception as e:
            print(f"[DEBUG] Error getting debug info: {e}")
            pass

    if RAW_OUTPUT:
        payload = build_order_fetch_request_payload(ident)
        resp = shopify_client.send_request(payload)
        out = resp.to_dict() or {}
    else:
        out = _fetch_order_details(ident, orders_service)

    # Convert Enums and non-serializable objects to plain strings/values for YAML
    safe_obj = json.loads(json.dumps(out, default=lambda o: getattr(o, 'value', str(o))))
    rendered = yaml.safe_dump(safe_obj, sort_keys=False, default_flow_style=False)
    Console().print(Syntax(rendered, "yaml"))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="bars", description="BARS Shopify CLI")
    sub = parser.add_subparsers(dest="cmd")

    fetch = sub.add_parser("fetch", help="Fetch resources")
    fetch_sub = fetch.add_subparsers(dest="subcmd")

    order = fetch_sub.add_parser("order", help="Fetch a single order")
    order.add_argument("identifier", help="id:123 or number:123")

    # Parse global flags first, then parse command-specific args
    global RAW_OUTPUT
    flags, remaining = _parse_global_flags(sys.argv[1:])
    RAW_OUTPUT = flags.get("raw", False)
    args = parser.parse_args(remaining)

    if args.cmd == "fetch" and args.subcmd == "order":
        sys.exit(cmd_fetch_order(args.identifier))

    parser.print_help()
    sys.exit(1)


def _parse_global_flags(argv: List[str]) -> Tuple[Dict[str, bool], List[str]]:
    """Extract supported global flags anywhere in argv. Returns (flags, filtered_argv)."""
    flags: Dict[str, bool] = {"raw": False}
    filtered: List[str] = []
    for token in argv:
        if token in ("--raw", "-R"):
            flags["raw"] = True
            continue
        filtered.append(token)
    return flags, filtered


if __name__ == "__main__":
    main()


