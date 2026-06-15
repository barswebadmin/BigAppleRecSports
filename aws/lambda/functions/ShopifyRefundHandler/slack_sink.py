"""POST the refund evaluation payload to a Slack Workflow trigger.

Configured via one env var following the BARS double-underscore namespacing
convention (mirrors ``SLACK__<BOT>__<FIELD>`` used elsewhere in the
shared_utilities + lambda env_config files):

  - ``SLACK__REFUND_EVAL_TRIGGER_URL`` : the ``https://hooks.slack.com/triggers/…``
                                         URL for the refund-eval workflow.
                                         The auth token is already in the URL
                                         path — no separate bearer needed.

When unset the function returns silently (acts as a no-op for local dev / new
deploys before the workflow is wired). Never raises — network failures and
non-2xx all log and return, so the HTTP response path is unaffected.

The Slack webhook trigger maps a single workflow variable, ``evaluation_json``,
so we wrap the evaluation dict as ``{"evaluation_json": "<json string>"}``. The
Deno function parses that string back into the RefundEvaluationPayload.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_URL_ENV = "SLACK__REFUND_EVAL_TRIGGER_URL"


def maybe_post_to_slack(payload: dict[str, Any], *, timeout: float = 10.0) -> None:
    """Best-effort POST. Returns None whether it succeeds, fails, or is unconfigured.

    The lambda's HTTP response to GAS does not depend on this — Slack delivery
    is fire-and-log. Errors get logged at WARNING; the lambda still returns 200
    to GAS.
    """
    url = os.environ.get(_URL_ENV)
    if not url:
        logger.info("%s not set — skipping Slack POST", _URL_ENV)
        return

    # The webhook trigger reads a single ``evaluation_json`` variable, so wrap
    # the payload as a JSON string under that key.
    body = {"evaluation_json": json.dumps(payload, default=str)}

    try:
        response = httpx.post(
            url,
            content=json.dumps(body, default=str),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
    except httpx.RequestError as e:
        logger.warning("Slack POST request error to %s: %s", url, e)
        return

    if response.status_code >= 400:
        logger.warning(
            "Slack POST returned %s — body: %s", response.status_code, response.text[:500]
        )
        return

    logger.info("Slack POST returned %s", response.status_code)
