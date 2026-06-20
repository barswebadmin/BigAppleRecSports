"""
DynamoDB persistence for RegularSeason records.

Uses PynamoDB for typed access to known fields plus MapAttribute for the
free-form `registrationPeriods` map (so arbitrary period names work without
schema migration). Lambda code interacts with `Box`-wrapped dicts, never with
the PynamoDB instance directly, to keep dotted-access semantics throughout.
"""
import os
from datetime import datetime, timezone

from box import Box
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.models import Model


class RegularSeason(Model):
    class Meta:
        table_name = os.environ.get("REGULAR_SEASON_TABLE", "bars-regular-seasons-dev")
        region = os.environ.get("AWS_REGION", "us-east-1")
        billing_mode = "PAY_PER_REQUEST"

    id = UnicodeAttribute(hash_key=True)
    sport = UnicodeAttribute()
    division = UnicodeAttribute()
    dayOfPlay = UnicodeAttribute()
    season = UnicodeAttribute()
    year = NumberAttribute()
    status = UnicodeAttribute()
    baseTitle = UnicodeAttribute()
    handle = UnicodeAttribute(null=True)
    shopifyProductId = UnicodeAttribute()
    tags = ListAttribute(of=UnicodeAttribute, default=list)
    registrationPeriods = MapAttribute(default=dict)
    createdAt = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    updatedAt = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))


def get_season(season_id: str) -> Box:
    record = RegularSeason.get(season_id)
    return Box(record.attribute_values)


def upsert_season(season_id: str, **fields) -> None:
    fields["updatedAt"] = datetime.now(timezone.utc)
    actions = [getattr(RegularSeason, k).set(v) for k, v in fields.items()]
    RegularSeason(id=season_id).update(actions=actions)
