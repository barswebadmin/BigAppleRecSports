"""
Shopify product image enum — shared across lambda functions.

Maps sport names to their Shopify MediaImage file IDs.
"""

from enum import Enum


class ProductImage(Enum):
    KICKBALL         = 25861318049886
    DODGEBALL        = 25446377554014
    BOWLING_SUN_OPEN = 25927726006366
    BOWLING_MON_OPEN = 25927755989086
    BOWLING_MON_WTNB = 25927756021854
    PICKLEBALL       = 25536427425886
    WAITLIST         = 24743247085662

    @classmethod
    def from_tags(cls, tags: list[str]) -> ProductImage | None:
        """Resolve a sport image from product tags.

        For bowling, uses day:* and division info to pick the correct variant.
        """
        joined = " ".join(tags).lower()

        sport = None
        for s in ("kickball", "dodgeball", "bowling", "pickleball"):
            if s in joined:
                sport = s
                break
        if sport is None:
            return None

        if sport != "bowling":
            return cls[sport.upper()]

        day = None
        tags_lower = [t.lower() for t in tags]
        for t in tags_lower:
            if t.startswith("day:"):
                day = t.split(":", 1)[1]
                break

        is_wtnb = any(
            "wtnb" in t and ("division" in t or t.endswith("div"))
            for t in tags_lower
        )

        if day == "sunday" and not is_wtnb:
            return cls.BOWLING_SUN_OPEN
        if day == "monday" and is_wtnb:
            return cls.BOWLING_MON_WTNB
        if day == "monday":
            return cls.BOWLING_MON_OPEN
        return cls.BOWLING_MON_OPEN

    @classmethod
    def from_media_ids(cls, media_ids: list[str]) -> ProductImage | None:
        """Reverse-map Shopify media GIDs to a ProductImage value."""
        enum_by_value = {str(img.value): img for img in cls}
        for gid in media_ids:
            numeric_id = gid.rsplit("/", 1)[-1]
            if numeric_id in enum_by_value:
                return enum_by_value[numeric_id]
        return None

    @property
    def display_name(self) -> str:
        if self == ProductImage.WAITLIST:
            return "Closed - Waitlist Only"
        _NAMES = {
            ProductImage.BOWLING_SUN_OPEN: "Bowling Sunday Open Main",
            ProductImage.BOWLING_MON_OPEN: "Bowling Monday Open Main",
            ProductImage.BOWLING_MON_WTNB: "Bowling Monday WTNB Main",
        }
        return _NAMES.get(self, f"{self.name.title()} Main")
