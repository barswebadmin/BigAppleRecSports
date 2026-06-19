"""
Configuration for the ShopifyProductUpdates lambda.

Period config (displayBracket, requiredTags, statusValue per period name, plus
division display strings) lives in ``data/period_templates.yaml`` and is
loaded once at import — update by editing the YAML and redeploying.

Image IDs (Shopify MediaImage GIDs, stored as integers) live in SSM Parameter
Store under ``SSM_IMAGES_PATH`` as a JSON object keyed by sport name.  They are
fetched with a TTL cache so a hot container re-fetches at most once per
``CACHE_TTL_SECONDS`` without requiring a redeploy.

Sold-out / waitlist images live under ``SSM_SOLD_OUT_IMAGES_PATH`` with the
same shape.  Used by the ``sold-out-image-check`` action.

Usage:
    from .config import PERIOD_CONFIG, load_images, load_sold_out_images
    PERIOD_CONFIG.periods["early"].displayBracket
    images = load_images()          # Box: {sport: image_gid}
    sold_out = load_sold_out_images()  # Box: {sport: image_gid}
"""

import os
from pathlib import Path

import yaml
from aws_lambda_powertools.utilities import parameters
from box import Box

CACHE_TTL_SECONDS = 300

IMAGES_PATH = os.environ.get("SSM_IMAGES_PATH", "/bars/shopify/image-ids")
SOLD_OUT_IMAGES_PATH = os.environ.get(
    "SSM_SOLD_OUT_IMAGES_PATH", "/bars/shopify/sold-out-image-ids"
)

_PERIOD_CONFIG_FILE = Path(__file__).parent / "data" / "period_templates.yaml"

_ssm = parameters.SSMProvider()


def _load_period_config() -> Box:
    with open(_PERIOD_CONFIG_FILE) as fh:
        raw = yaml.safe_load(fh)
    return Box(raw, box_dots=False)


PERIOD_CONFIG: Box = _load_period_config()


def load_images() -> Box:
    """Return the sport→image-GID mapping (SSM-backed, TTL-cached)."""
    return Box(_ssm.get(IMAGES_PATH, max_age=CACHE_TTL_SECONDS, transform="json"))


def load_sold_out_images() -> Box:
    """Return the sport→sold-out-image-GID mapping (SSM-backed, TTL-cached)."""
    return Box(
        _ssm.get(SOLD_OUT_IMAGES_PATH, max_age=CACHE_TTL_SECONDS, transform="json")
    )
