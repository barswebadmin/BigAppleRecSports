"""POST workflow variables to a Slack Workflow webhook trigger URL.

Fire-and-log transport: one generic ``post_to_slack`` that takes the trigger
URL and the dict of workflow variables to send. Reusable for any webhook
trigger — the refund evaluation now, and (later) the cancel / refund result
notifications — since each one just maps a different set of variables.

Webhook trigger URLs (``https://hooks.slack.com/triggers/…``) carry their auth
token in the path, so no bearer / signing secret is needed. The caller (main)
decides which URL to pass and how to name the variables.
"""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def post_to_slack(
    url: str | None,
    variables: dict[str, Any],
    *,
    timeout: float = 10.0,
) -> None:
    """Best-effort POST of ``variables`` to a Slack webhook trigger ``url``.

    No-ops when ``url`` is falsy, so unconfigured / local deploys run cleanly.
    Never raises — network errors and non-2xx responses log at WARNING and
    return, so the caller's own response path is unaffected by Slack delivery.

    ``variables`` is the exact JSON body the trigger receives; the caller maps
    its payload onto the trigger's input variable names, e.g.
    ``{"evaluation_json": json.dumps(payload)}``.
    """
    if not url:
        logger.info("No Slack trigger URL provided — skipping POST")
        return

    # TODO: replace this ad-hoc httpx.post with a shared/DRY httpx client
    # (timeout + retries + structured logging in one place). shopify_client
    # already stands up its own httpx setup; both should converge on a single
    # helper in lib/ instead of each module hand-rolling a request.
    try:
        response = httpx.post(
            url,
            content=json.dumps(variables, default=str),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
    except httpx.RequestError as e:
        logger.warning("Slack POST request error to %s: %s", url, e)
        return

    if response.status_code >= 400:
        logger.warning("Slack POST returned %s — body: %s", response.status_code, response.text[:500])
        return

    logger.info("Slack POST returned %s", response.status_code)
