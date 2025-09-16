from fastapi import APIRouter, HTTPException, Request
import logging
import json

from services.orders import OrdersService
from services.slack import SlackService
from services.slack.usergroup_client import SlackUsergroupClient
from services.slack.users_client import SlackUsersClient
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])

orders_service = OrdersService()
slack_service = SlackService()
usergroup_client = SlackUsergroupClient(settings.active_slack_bot_token or "")
users_client = SlackUsersClient(settings.active_slack_bot_token or "")


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
        request.headers.get("Content-Type")

        print("\n🔍 === SLACK INTERACTIONS ROUTER ===")
        # print(f"📋 Headers:")
        # print(f"   X-Slack-Request-Timestamp: {timestamp}")
        # print(f"   X-Slack-Signature: {signature}")
        # print(f"   Content-Type: {content_type}")
        # print(f"   User-Agent: {request.headers.get('User-Agent', 'Not provided')}")

        # print(f"📦 Raw Body ({len(body)} bytes):")
        # body_str = body.decode('utf-8', errors='replace')
        # print(f"   {body_str}")

        # Verify signature if present
        if timestamp and signature:
            signature_valid = slack_service.verify_slack_signature(
                body, timestamp, signature
            )
            print(f"🔐 Signature Valid: {signature_valid}")
            if not signature_valid:
                print("❌ SIGNATURE VERIFICATION FAILED - but continuing for debug...")
        else:
            print("⚠️  No signature headers provided")

        # Parse form data (Slack sends as application/x-www-form-urlencoded)
        payload = None  # Initialize payload to avoid UnboundLocalError
        try:
            form_data = await request.form()
            payload_str = form_data.get("payload")

            if payload_str:
                print("📝 Form payload found:")
                print(f"   {payload_str}")

                # Parse JSON payload
                payload = json.loads(str(payload_str))
                print("✅ Parsed JSON successfully!")
                print(f"   Type: {payload.get('type', 'Not specified')}")
                print(f"   Keys: {list(payload.keys())}")

                # Show user info
                user_info = payload.get("user", {})
                print(
                    f"👤 User: {user_info.get('name', 'Unknown')} (ID: {user_info.get('id', 'Unknown')})"
                )

                # Show action info if it's a button click
                if payload.get("type") == "block_actions":
                    actions = payload.get("actions", [])
                    if actions:
                        action = actions[0]
                        print("🔘 Action:")
                        print(
                            f"   Action ID: {action.get('action_id', 'Not specified')}"
                        )
                        print(f"   Value: {action.get('value', 'Not specified')}")
                        print(
                            f"   Text: {action.get('text', {}).get('text', 'Not specified')}"
                        )

            else:
                print("❌ No 'payload' found in form data")
                print(f"   Form keys: {list(form_data.keys())}")

        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        except Exception as e:
            print(f"❌ Form Parse Error: {e}")
            raise HTTPException(status_code=400, detail="Invalid form data")

        # print("=== END DEBUG ===\n")

        # Process modal submissions
        if payload and payload.get("type") == "view_submission":
            print("\n📝 === MODAL SUBMISSION RECEIVED ===")
            print(f"📋 Payload: {json.dumps(payload, indent=2)}")
            print("=== END MODAL SUBMISSION DEBUG ===\n")

            view = payload.get("view", {})
            callback_id = view.get("callback_id")

            if callback_id == "edit_request_details_submission":
                return await slack_service.handle_edit_request_details_submission(
                    payload
                )
            elif callback_id == "deny_refund_request_modal_submission":
                return await slack_service.handle_deny_refund_request_modal_submission(
                    payload
                )
            elif callback_id == "restock_confirmation_modal":
                return await slack_service.handle_restock_confirmation_submission(
                    payload
                )
            elif callback_id == "custom_refund_submit":
                print("🧾 Received custom refund modal submission")

                # Extract values from the modal input
                values = payload["view"]["state"]["values"]
                refund_amount = values["refund_input_block"]["custom_refund_amount"][
                    "value"
                ]

                # Extract metadata
                private_metadata = payload["view"].get("private_metadata")
                if not private_metadata:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing private_metadata in view submission",
                    )

                metadata = json.loads(private_metadata)

                # Extract requestor information from metadata or Slack user
                slack_user_name = metadata.get("slack_user_name", "Unknown User")
                requestor_name = {
                    "first": metadata.get("requestor_first_name", ""),
                    "last": metadata.get("requestor_last_name", ""),
                }
                requestor_email = metadata.get("requestor_email", "")

                # Build the request_data to match what process_refund expects
                request_data = {
                    "orderId": metadata["orderId"],
                    "rawOrderNumber": metadata["rawOrderNumber"],
                    "refundAmount": refund_amount,
                    "refundType": metadata["refundType"],
                    "orderCancelled": "false",
                }

                # Call process_refund with the updated amount
                return await slack_service.handle_process_refund(
                    request_data=request_data,
                    channel_id=metadata["channel_id"],
                    requestor_name=requestor_name,
                    requestor_email=requestor_email,
                    thread_ts=metadata["thread_ts"],
                    slack_user_name=slack_user_name,
                    current_message_full_text=metadata["current_message_full_text"],
                    slack_user_id=payload["user"]["id"],
                    trigger_id=payload.get("trigger_id"),
                )
            else:
                logger.warning(f"Unknown modal callback_id: {callback_id}")
                return {"response_action": "clear"}

        # Process button actions
        if payload and payload.get("type") == "block_actions":
            actions = payload.get("actions", [])

            if actions:
                action = actions[0]
                action_id = action.get("action_id")
                action_value = action.get("value", "")
                slack_user_id = payload.get("user", {}).get("id", "Unknown")
                slack_user_name = payload.get("user", {}).get("name", "Unknown")

                # Extract trigger_id for modal dialogs
                trigger_id = payload.get("trigger_id")

                # Parse button data to get request data
                if action_value.startswith("{") and action_value.endswith("}"):
                    # JSON format (newer restock buttons)
                    try:
                        request_data = json.loads(action_value)
                    except json.JSONDecodeError:
                        logger.error(
                            f"Failed to parse JSON action value: {action_value}"
                        )
                        request_data = {}
                else:
                    # Pipe-separated format (older buttons)
                    request_data = slack_service.parse_button_value(action_value)

                # Extract requestor info from parsed data
                requestor_name = {
                    "first": request_data.get("first", "Unknown"),
                    "last": request_data.get("last", "Unknown"),
                }
                requestor_email = request_data.get("email", "Unknown")

                # Get message info for updating
                thread_ts = payload.get("message", {}).get("ts")
                channel_id = payload.get("channel", {}).get("id")

                # Extract metadata from the original message
                message_metadata = payload.get("message", {}).get("metadata", {})
                original_channel = None
                original_mention = None

                if (
                    message_metadata
                    and message_metadata.get("event_type") == "refund_request"
                ):
                    event_payload = message_metadata.get("event_payload", {})
                    original_channel = event_payload.get("originalChannel")
                    original_mention = event_payload.get("originalMention")

                print(
                    f"📍 Extracted metadata - Channel: {original_channel}, Mention: {original_mention}"
                )

                # Note: Button values now contain all necessary preserved data

                logger.info(f"Button clicked: {action_id} with data: {request_data}")

                # Extract current message content for data preservation
                # Use blocks structure instead of just text field for complete data
                current_message_blocks = payload.get("message", {}).get("blocks", [])
                current_message_text = payload.get("message", {}).get(
                    "text", ""
                )  # Keep as fallback

                # Convert blocks back to text for parsing
                current_message_full_text = slack_service.extract_text_from_blocks(
                    current_message_blocks
                )

                # If blocks extraction fails, fall back to the simple text field
                if not current_message_full_text and current_message_text:
                    current_message_full_text = current_message_text
                    print(
                        "⚠️ Using fallback message text since blocks extraction failed"
                    )

                print("\n📨 === SLACK MESSAGE DEBUG ===")
                print(
                    f"📝 Extracted current_message_text length: {len(current_message_text)}"
                )
                print(f"📝 Extracted blocks count: {len(current_message_blocks)}")
                print(
                    f"📝 Extracted current_message_full_text length: {len(current_message_full_text)}"
                )
                print(
                    f"📝 Current message full text: {current_message_full_text[:500]}..."
                )
                print(f"📝 Blocks structure: {current_message_blocks}")
                print(f"🔘 Action ID: {action_id}")
                print("=== END SLACK MESSAGE DEBUG ===\n")

                # === STEP 1 HANDLERS: INITIAL DECISION (Cancel Order / Proceed Without Canceling) ===
                if action_id == "cancel_order":
                    return await slack_service.handle_cancel_order(
                        request_data,
                        channel_id,
                        requestor_name,
                        requestor_email,
                        thread_ts,
                        slack_user_id,
                        slack_user_name,
                        current_message_full_text,
                        trigger_id,
                    )

                elif action_id == "proceed_without_cancel":
                    print("\n🚀 === PROCEED WITHOUT CANCEL BUTTON CLICKED ===")
                    print("📦 Full JSON Request Data:")
                    print(f"   Request Data: {json.dumps(request_data, indent=2)}")
                    print(f"   Action ID: {action_id}")
                    print(f"   Channel ID: {channel_id}")
                    print(f"   Thread TS: {thread_ts}")
                    print(f"   Slack User: {slack_user_name}")
                    print(f"   User ID: {slack_user_id}")
                    print(f"   Trigger ID: {trigger_id}")
                    print("🚀 === END PROCEED WITHOUT CANCEL DEBUG ===\n")

                    result = await slack_service.handle_proceed_without_cancel(
                        request_data,
                        channel_id,
                        requestor_name,
                        requestor_email,
                        thread_ts,
                        slack_user_id,
                        slack_user_name,
                        current_message_full_text,
                        trigger_id,
                        original_channel,
                        original_mention,
                    )

                    print("\n🚀 === PROCEED WITHOUT CANCEL RESULT ===")
                    print(f"✅ Action: {action_id}")
                    print(f"📊 Result: {json.dumps(result, indent=2)}")
                    print("🚀 === END PROCEED RESULT ===\n")

                    return result

                elif action_id == "deny_refund_request_show_modal":
                    print("\n🚫 === DENY REQUEST MODAL ===")
                    print(f"🎯 Action ID: {action_id}")
                    print(f"📦 Request Data: {json.dumps(request_data, indent=2)}")
                    print(f"👤 User: {slack_user_name} (ID: {slack_user_id})")
                    print(f"🎯 Trigger ID: {trigger_id}")
                    print("🚫 === END DENY REQUEST MODAL DEBUG ===\n")

                    return await slack_service.handle_deny_refund_request_show_modal(
                        request_data=request_data,
                        channel_id=channel_id,
                        thread_ts=thread_ts,
                        slack_user_name=slack_user_name,
                        slack_user_id=slack_user_id,
                        trigger_id=trigger_id,
                        current_message_full_text=current_message_full_text,
                    )

                # === STEP 2 HANDLERS: REFUND DECISION (Process / Custom / No Refund) ===
                elif action_id == "process_refund":
                    print("\n🎯 === APPROVE REFUND BUTTON CLICKED (Step 5) ===")
                    print("📦 Full JSON Request Data:")
                    print(f"   Request Data: {json.dumps(request_data, indent=2)}")
                    print(f"   Channel ID: {channel_id}")
                    print(f"   Thread TS: {thread_ts}")
                    print(f"   Slack User: {slack_user_name}")
                    print(f"   User ID: {slack_user_id}")
                    print(f"   Trigger ID: {trigger_id}")
                    print(
                        f"   Current Message Text Preview: {current_message_full_text[:200]}..."
                    )
                    print("🎯 === END APPROVE REFUND DEBUG ===\n")

                    return await slack_service.handle_process_refund(
                        request_data=request_data,
                        channel_id=channel_id,
                        requestor_name=requestor_name,
                        requestor_email=requestor_email,
                        thread_ts=thread_ts,
                        slack_user_name=slack_user_name,
                        current_message_full_text=current_message_full_text,
                        slack_user_id=slack_user_id,
                        trigger_id=trigger_id,
                    )

                elif action_id == "custom_refund_amount":
                    print("\n💰 === CUSTOM REFUND AMOUNT BUTTON CLICKED ===")
                    print("📦 Full JSON Request Data:")
                    print(f"   Request Data: {json.dumps(request_data, indent=2)}")
                    print(f"   Action ID: {action_id}")
                    print(f"   Channel ID: {channel_id}")
                    print(f"   Thread TS: {thread_ts}")
                    print(f"   Slack User: {slack_user_name}")
                    print(f"   User ID: {slack_user_id}")
                    print(f"   Trigger ID: {trigger_id}")
                    print("💰 === END CUSTOM REFUND DEBUG ===\n")

                    result = await slack_service.handle_custom_refund_amount(
                        request_data=request_data,
                        channel_id=channel_id,
                        thread_ts=thread_ts,
                        requestor_name=requestor_name,
                        requestor_email=requestor_email,
                        slack_user_name=slack_user_name,
                        current_message_full_text=current_message_full_text,
                        slack_user_id=slack_user_id,
                        trigger_id=trigger_id,
                    )

                    print("\n💰 === CUSTOM REFUND AMOUNT RESULT ===")
                    print(f"✅ Action: {action_id}")
                    print(f"📊 Result: {json.dumps(result, indent=2)}")
                    print("💰 === END CUSTOM REFUND RESULT ===\n")

                    return result

                elif action_id == "no_refund":
                    print("\n🚫 === DENY REFUND BUTTON CLICKED (Step 5) ===")
                    print("📦 Full JSON Request Data:")
                    print(f"   Request Data: {json.dumps(request_data, indent=2)}")
                    print(f"   Channel ID: {channel_id}")
                    print(f"   Thread TS: {thread_ts}")
                    print(f"   Slack User: {slack_user_name}")
                    print(f"   User ID: {slack_user_id}")
                    print(f"   Trigger ID: {trigger_id}")
                    print(f"   Requestor Name: {requestor_name}")
                    print(f"   Requestor Email: {requestor_email}")
                    print("🚫 === END DENY REFUND DEBUG ===\n")

                    return await slack_service.handle_no_refund(
                        request_data,
                        channel_id,
                        requestor_name,
                        requestor_email,
                        thread_ts,
                        slack_user_name,
                        slack_user_id,
                        current_message_full_text,
                        trigger_id,
                    )

                # === EMAIL MISMATCH HANDLERS ===
                elif action_id == "edit_request_details":
                    print("\n✏️ === EDIT REQUEST DETAILS BUTTON CLICKED ===")
                    print("📦 Full JSON Request Data:")
                    print(f"   Request Data: {json.dumps(request_data, indent=2)}")
                    print(f"   Channel ID: {channel_id}")
                    print(f"   Thread TS: {thread_ts}")
                    print(f"   Slack User: {slack_user_name}")
                    print(f"   User ID: {slack_user_id}")
                    print(f"   Trigger ID: {trigger_id}")
                    print("✏️ === END EDIT REQUEST DETAILS DEBUG ===\n")

                    return await slack_service.handle_edit_request_details(
                        request_data=request_data,
                        channel_id=channel_id,
                        thread_ts=thread_ts,
                        slack_user_name=slack_user_name,
                        slack_user_id=slack_user_id,
                        trigger_id=trigger_id,
                        current_message_full_text=current_message_full_text,
                    )

                # === STEP 3 HANDLERS: RESTOCK INVENTORY (Restock / Do Not Restock) ===
                elif action_id and (
                    action_id.startswith("confirm_restock")
                    or action_id == "confirm_do_not_restock"
                ):
                    print("\n📦 === RESTOCK CONFIRMATION BUTTON CLICKED ===")
                    print("📦 Full JSON Request Data:")
                    print(f"   Request Data: {json.dumps(request_data, indent=2)}")
                    print(f"   Action ID: {action_id}")
                    print(f"   Channel ID: {channel_id}")
                    print(f"   Thread TS: {thread_ts}")
                    print(f"   Slack User: {slack_user_name}")
                    print(f"   User ID: {slack_user_id}")
                    print(f"   Trigger ID: {trigger_id}")
                    print("📦 === END RESTOCK CONFIRMATION DEBUG ===\n")

                    # Show confirmation modal for restock actions
                    return await slack_service.handle_restock_confirmation_request(
                        request_data,
                        action_id,
                        trigger_id,
                        channel_id,
                        thread_ts,
                        current_message_full_text,
                    )
                elif action_id and (
                    action_id.startswith("restock") or action_id == "do_not_restock"
                ):
                    print("\n📦 === RESTOCK ACTION BUTTON CLICKED ===")
                    print("📦 Full JSON Request Data:")
                    print(f"   Request Data: {json.dumps(request_data, indent=2)}")
                    print(f"   Action ID: {action_id}")
                    print(f"   Channel ID: {channel_id}")
                    print(f"   Thread TS: {thread_ts}")
                    print(f"   Slack User: {slack_user_name}")
                    print(f"   User ID: {slack_user_id}")
                    print(f"   Trigger ID: {trigger_id}")
                    print("📦 === END RESTOCK ACTION DEBUG ===\n")

                    # Handle confirmed restock actions (called from modal submission)
                    result = await slack_service.handle_restock_inventory(
                        request_data,
                        action_id,
                        channel_id,
                        thread_ts,
                        slack_user_name,
                        current_message_full_text,
                        trigger_id,
                    )

                    print("\n📦 === RESTOCK ACTION RESULT ===")
                    print(f"✅ Action: {action_id}")
                    print(f"📊 Result: {json.dumps(result, indent=2)}")
                    print("📦 === END RESTOCK RESULT ===\n")

                    return result
                else:
                    if not action_id:
                        raise HTTPException(
                            status_code=400, detail="Missing action_id in request"
                        )
                    logger.warning(f"Unknown action_id: {action_id}")
                    return {
                        "response_type": "ephemeral",
                        "text": f"Unknown action: {action_id}",
                    }

        # Return success response to Slack
        return {"text": "✅ Webhook received and logged successfully!"}

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        print(f"❌ JSON Decode Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    except HTTPException:
        # Re-raise HTTPExceptions as-is to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error handling Slack interaction: {e}")
        print(f"❌ General Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook")
async def handle_slack_webhook(request: Request):
    """
    Handle Slack webhook - supports both URL verification and button interactions
    This is a compatibility endpoint that delegates to the main interactions handler
    """
    try:
        print("\n🔍 === SLACK WEBHOOK ROUTER ===")
        # Check if this is a URL verification challenge (JSON body)
        content_type = request.headers.get("Content-Type", "")

        if "application/json" in content_type:
            # Handle URL verification challenge
            body = await request.json()
            if "challenge" in body:
                # Slack URL verification - echo back the challenge
                return {"challenge": body["challenge"]}

        # Otherwise, delegate to the main interactions handler
        # Reset request body for the interactions handler to process
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
        text = (form.get("text") or "").strip()
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
        headers = {"Authorization": f"Bearer {settings.active_slack_bot_token}"}
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
