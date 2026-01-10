from typing import TypedDict, Optional, Any, Callable, List
from backend_services.shopify.models.sgqlc_models import Customer

class CustomerDisplayField(TypedDict):
    """Type definition for customer display field configuration."""
    field_name: str
    display_label: str
    default: Optional[str]
    formatter: Optional[Callable[[Any], str]]

def _format_customer_option(customer: Customer) -> str:
    """Format customer for display in selection options."""
    name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
    full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
    email = customer.email or 'N/A'  # type: ignore[attr-defined]
    return f"{full_name} ({email})"

def _format_customer_name(customer: Any) -> str:
    """Format customer full name from firstName, lastName, or displayName."""
    name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
    full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
    return full_name


customer_display_fields: List[CustomerDisplayField] = [
    {"field_name": "id", "display_label": "ID", "default": None, "formatter": None},
    {"field_name": "name", "display_label": "Name", "default": None, "formatter": _format_customer_name},
    {"field_name": "displayName", "display_label": "Display Name", "default": "N/A", "formatter": None},
    {"field_name": "email", "display_label": "Email", "default": "N/A", "formatter": None},
    {"field_name": "phone", "display_label": "Phone", "default": "N/A", "formatter": None},
    {"field_name": "state", "display_label": "State", "default": "N/A", "formatter": None},
    {"field_name": "verifiedEmail", "display_label": "Verified", "default": None, "formatter": None},
    {"field_name": "numberOfOrders", "display_label": "Orders Count", "default": "N/A", "formatter": None},
    {"field_name": "createdAt", "display_label": "Created", "default": "N/A", "formatter": None},
    {"field_name": "updatedAt", "display_label": "Updated", "default": "N/A", "formatter": None},
]


def format_customer(customer: Any) -> str:
    """Format customer data for display."""
    output = []
    output.append("\n✅ Customer Found!")
    output.append("=" * 60)
    
    for field_config in customer_display_fields:
        field_name = field_config["field_name"]
        display_label = field_config["display_label"]
        default = field_config["default"]
        formatter = field_config["formatter"]
        
        if formatter:
            value = formatter(customer)
        else:
            value = getattr(customer, field_name, None)  # type: ignore[attr-defined]
            if value is None:
                value = default
            else:
                value = str(value)
        
        output.append(f"{display_label:<15} {value}")
    
    if customer.tags:  # type: ignore[attr-defined]
        tags_list = list(customer.tags)  # type: ignore[attr-defined]
        output.append(f"\nTags ({len(tags_list)}):")
        for tag in tags_list:
            output.append(f"  • {tag}")
    
    if customer.defaultAddress:  # type: ignore[attr-defined]
        addr = customer.defaultAddress  # type: ignore[attr-defined]
        output.append("\nDefault Address:")
        if addr.address1:  # type: ignore[attr-defined]
            output.append(f"  {addr.address1}")  # type: ignore[attr-defined]
        if addr.address2:  # type: ignore[attr-defined]
            output.append(f"  {addr.address2}")  # type: ignore[attr-defined]
        city_parts = [str(p) for p in [addr.city, addr.province, addr.zip] if p]  # type: ignore[attr-defined]
        if city_parts:
            output.append(f"  {', '.join(city_parts)}")
        if addr.country:  # type: ignore[attr-defined]
            output.append(f"  {addr.country}")  # type: ignore[attr-defined]
    
    # Access orders from sgqlc Connection structure
    orders_connection = customer.orders  # type: ignore[attr-defined]
    recent_orders = orders_connection.nodes if orders_connection and hasattr(orders_connection, 'nodes') else []  # type: ignore[attr-defined]
    if recent_orders:
        output.append(f"\nRecent Orders ({len(recent_orders)}):")
        for order in recent_orders:
            output.append(f"  • {order.name or 'N/A'} (created: {order.createdAt or 'N/A'})")  # type: ignore[attr-defined]
            output.append(f"    ID: {order.id}")  # type: ignore[attr-defined]
    
    output.append("=" * 60)
    return '\n'.join(output)