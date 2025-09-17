from fastapi import APIRouter, HTTPException, Request
import logging
import json

from services.orders import OrdersService
from services.slack import SlackService
from services.slack_management.usergroup_client import SlackUsergroupClient
from services.slack_management.users_client import SlackUsersClient
from config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])

orders_service = OrdersService()
slack_service = SlackService()
# Note: These clients are not currently used in the simplified router
# usergroup_client = SlackUsergroupClient(config.active_slack_bot_token or "")
# users_client = SlackUsersClient(config.active_slack_bot_token or "")


# Note: parse_original_message_data function removed - data now preserved in button values


@router.post("/interactions")
async def handle_slack_interactions(request: Request):
    """
    Handle Slack button interactions and other interactive components
    This endpoint receives webhooks when users click buttons in Slack messages
    """
    try:
        # Get raw request data
        body = await request.body()

        # Get headers for verification
        timestamp = request.headers.get("X-Slack-Request-Timestamp")
        signature = request.headers.get("X-Slack-Signature")

        logger.info("Processing Slack interaction request")

        # Parse form data (Slack sends as application/x-www-form-urlencoded)
        payload = None
        try:
            form_data = await request.form()
            payload_str = form_data.get("payload")

            if payload_str:
                # Parse JSON payload
                payload = json.loads(str(payload_str))
                logger.info(f"Parsed Slack payload: {payload.get('type', 'unknown')}")
            else:
                logger.warning("No 'payload' found in form data")

        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        except Exception as e:
            logger.error(f"Form Parse Error: {e}")
            raise HTTPException(status_code=400, detail="Invalid form data")

        # Delegate to Slack service for processing
        return await slack_service.handle_slack_interaction(
            payload=payload,
            body=body,
            timestamp=timestamp,
            signature=signature
        )

    except HTTPException:
        # Re-raise HTTPExceptions as-is to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error handling Slack interaction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook")
async def handle_slack_webhook(request: Request):
    """
    Handle Slack webhook - supports both URL verification and button interactions
    This is a compatibility endpoint that delegates to the main interactions handler
    """
    try:
        # Check if this is a URL verification challenge (JSON body)
        content_type = request.headers.get("Content-Type", "")

        if "application/json" in content_type:
            # Handle URL verification challenge
            body = await request.json()
            if "challenge" in body:
                # Slack URL verification - echo back the challenge
                return {"challenge": body["challenge"]}

        # Otherwise, delegate to the main interactions handler
        return await handle_slack_interactions(request)

    except HTTPException:
        # Re-raise HTTPExceptions as-is to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error handling Slack webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/commands")
async def handle_slash_commands(request: Request):
    """
    Minimal slash command endpoint to trigger CSV sync via URL:
    e.g. /sync-groups csv_url=https://.../groups.csv apply=true
    """
    try:
        form = await request.form()
        text_field = form.get("text")
        text = str(text_field).strip() if text_field else ""
        # naive parse: key=value pairs
        args = {}
        for token in text.split():
            if "=" in token:
                k, v = token.split("=", 1)
                args[k.strip()] = v.strip()

        csv_url = args.get("csv_url")
        apply_flag = (args.get("apply", "false").lower() in ("1", "true", "yes"))
        if not csv_url:
            return {"response_type": "ephemeral", "text": "Usage: /sync-groups csv_url=https://... apply=true|false"}

        # Download CSV
        import requests as rq
        r = rq.get(csv_url, timeout=30)
        if r.status_code != 200:
            return {"response_type": "ephemeral", "text": f"Failed to fetch CSV: {r.status_code}"}

        # Write to temp file
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp.write(r.content)
        tmp.flush()

        # Run CSV sync CLI (dry-run or apply)
        from services.leadership.leadership_csv_sync_cli import main as csv_sync_main
        import sys
        sys.argv = ["csv_sync", "--csv", tmp.name]
        if apply_flag:
            sys.argv.append("--apply")
        code = csv_sync_main()

        return {"response_type": "ephemeral", "text": "CSV sync completed" if code == 0 else "CSV sync failed"}
    except Exception as e:
        logger.error(f"Slash command error: {e}")
        return {"response_type": "ephemeral", "text": f"Error: {e}"}


@router.post("/file-uploaded")
async def handle_file_uploaded(request: Request):
    """
    Basic file upload event handler: expects Slack event payload with file URL
    (You will configure Events API to send file_shared and files events)
    """
    try:
        body = await request.json()
        event = body.get("event", {})
        file_info = (event.get("file") or {})
        csv_url = file_info.get("url_private_download")
        if not csv_url:
            return {"ok": True}

        # Use bot token to download private file
        import requests as rq
        # Note: This would need to be updated to use the new SlackConfig system
        # headers = {"Authorization": f"Bearer {config.active_slack_bot_token}"}
        headers = {"Authorization": "Bearer xoxb-token-placeholder"}
        resp = rq.get(csv_url, headers=headers)
        if resp.status_code != 200:
            return {"ok": False, "error": f"download_failed:{resp.status_code}"}

        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp.write(resp.content)
        tmp.flush()

        from services.leadership.leadership_csv_sync_cli import main as csv_sync_main
        import sys
        sys.argv = ["csv_sync", "--csv", tmp.name]
        # Default to dry-run when uploaded via DM; you can add apply=true in file title to apply
        title = (file_info.get("title") or "").lower()
        if "apply=true" in title:
            sys.argv.append("--apply")
        code = csv_sync_main()
        return {"ok": code == 0}
    except Exception as e:
        logger.error(f"File uploaded handler error: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/health")
async def health_check():
    """Health check endpoint for the Slack service"""
    return {"status": "healthy", "service": "slack"}
