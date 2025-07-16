from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import logging
from services.orders import OrdersService
from services.slack import SlackService
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])

orders_service = OrdersService()
slack_service = SlackService()

class SlackNotificationRequest(BaseModel):
    requestor_name: Dict[str, str]  # {"first": "John", "last": "Doe"}
    requestor_email: str
    refund_type: str  # "refund" or "credit"
    notes: str
    order_data: Optional[Dict[str, Any]] = None
    sheet_link: Optional[str] = None  # Google Sheets link to the specific row

@router.get("/{order_number}")
async def get_order(
    order_number: str,
    email: Optional[str] = Query(None, description="Email to search by if order number fails")
) -> Dict[str, Any]:
    """
    Get order details by order number (or email as fallback)
    Based on fetchShopifyOrderDetails from the Google Apps Script
    """
    try:
        result = orders_service.get_enhanced_order_details(order_name=order_number, email=email)
        
        if not result["success"]:
            raise HTTPException(status_code=406, detail=result["message"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order {order_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching order: {str(e)}")

@router.delete("/{order_number}")
async def cancel_order(
    order_number: str,
    refund_type: Optional[str] = Query("refund", description="Type of refund: 'refund' or 'credit'"),
    refund_amount: Optional[float] = Query(None, description="Custom refund amount (optional)"),
    restock_inventory: Optional[bool] = Query(True, description="Whether to restock inventory"),
    email: Optional[str] = Query(None, description="Email to search by if order number fails")
) -> Dict[str, Any]:
    """
    Cancel an order and process refund/credit
    Based on the refund processing logic from the Google Apps Script
    """
    try:
        # # First, get the order details
        # order_result = orders_service.fetch_order_details(order_name=order_number)
        
        # # If order not found by number and email provided, try by email
        # if not order_result["success"] and email:
        #     logger.info(f"Order {order_number} not found, trying by email: {email}")
        #     order_result = orders_service.fetch_order_details(email=email)
        
        # if not order_result["success"]:
        #     raise HTTPException(status_code=404, detail=order_result["message"])
        
        # order_data = order_result["data"]
        # order_id = order_data["orderId"]
        
        # # Calculate refund amount if not provided
        # if refund_amount is None:
        #     refund_calculation = orders_service.calculate_refund_due(order_data, refund_type)
        #     if not refund_calculation["success"]:
        #         raise HTTPException(status_code=400, detail=refund_calculation["message"])
        #     refund_amount = refund_calculation["refund_amount"]
        
        # # Step 1: Cancel the order
        # cancel_result = orders_service.cancel_order(order_id)
        # if not cancel_result["success"]:
        #     raise HTTPException(status_code=400, detail=f"Failed to cancel order: {cancel_result['message']}")
        
        # # Step 2: Process refund or credit
        # if refund_amount and refund_amount > 0:
        #     if refund_type == "credit":
        #         refund_result = orders_service.create_store_credit(order_id, refund_amount)
        #     else:
        #         refund_result = orders_service.create_refund(order_id, refund_amount)
            
        #     if not refund_result["success"]:
        #         logger.error(f"Refund/credit failed but order was canceled: {refund_result['message']}")
        #         # Don't fail the entire request since order was canceled
        # else:
        #     refund_result = {"success": True, "message": "No refund amount due"}
        
        # # Step 3: Restock inventory if requested
        # restock_results = []
        # if restock_inventory and order_data.get("product", {}).get("variants"):
        #     # Find the first variant with inventory item ID (usually the purchased variant)
        #     for variant in order_data["product"]["variants"]:
        #         if variant.get("inventoryItemId"):
        #             restock_result = orders_service.restock_inventory(variant["inventoryItemId"])
        #             restock_results.append({
        #                 "variant": variant["variantName"],
        #                 "result": restock_result
        #             })
        #             break  # Only restock the first/main variant
        
        # # Send Slack notification
        # try:
        #     slack_result = orders_service.slack_service.send_refund_notification(
        #         order_data={"order": order_data, "refund_calculation": refund_calculation, "inventory_summary": inventory_summary},
        #         refund_data={
        #             "refund_type": refund_type,
        #             "refund_amount": refund_amount,
        #             "refund_result": refund_result
        #         },
        #         user_name="API User"
        #     )
        #     logger.info(f"Slack notification result: {slack_result}")
        # except Exception as e:
        #     logger.error(f"Failed to send Slack notification: {str(e)}")
        #     # Don't fail the entire request for Slack errors
        
        # # Prepare response
        # response = {
        #     "success": True,
        #     "message": f"Order {order_number} has been canceled successfully",
        #     "data": {
        #         "order_id": order_id,
        #         "order_number": order_number,
        #         "cancellation": cancel_result["data"],
        #         "refund_amount": refund_amount,
        #         "refund_type": refund_type,
        #         "refund_result": refund_result,
        #         "restock_results": restock_results,
        #         "customer": order_data.get("customer", {}),
        #         "product": {
        #             "title": order_data["product"]["title"],
        #             "product_id": order_data["product"]["productId"]
        #         }
        #     }
        # }

        print(f"order_number: \n {json.dumps(order_number, indent=2)} \n\n")
        print(f"refund_type: \n {json.dumps(refund_type, indent=2)} \n\n")
        print(f"refund_amount: \n {json.dumps(refund_amount, indent=2)} \n\n")
        print(f"restock_inventory: \n {json.dumps(restock_inventory, indent=2)} \n\n")
        print(f"email: \n {json.dumps(email, indent=2)} \n\n")

        response = {
            "success": True,
            "message": f"Order {order_number} has been canceled successfully",
            "data": {
                # "order_id": order_id,
                "order_number": order_number,
                # "cancellation": cancel_result["data"],
                "refund_amount": refund_amount,
                "refund_type": refund_type,
                # "refund_result": refund_result,
                # "restock_results": restock_results,
                # "customer": order_data.get("customer", {}),
                "product": {
                    # "title": order_data["product"]["title"],
                    # "product_id": order_data["product"]["productId"]
                }
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling order {order_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error canceling order: {str(e)}")

@router.post("/{order_number}/refund")
async def create_refund(
    order_number: str,
    refund_type: str = Query("refund", description="Type of refund: 'refund' or 'credit'"),
    refund_amount: Optional[float] = Query(None, description="Custom refund amount (optional)"),
    email: Optional[str] = Query(None, description="Email to search by if order number fails")
) -> Dict[str, Any]:
    """
    Create a refund or store credit for an order without canceling it
    """
    try:
        # Get the order details
        order_result = orders_service.fetch_order_details(order_name=order_number)
        
        if not order_result["success"] and email:
            order_result = orders_service.fetch_order_details(email=email)
        
        if not order_result["success"]:
            raise HTTPException(status_code=404, detail=order_result["message"])
        
        order_data = order_result["data"]
        order_id = order_data["orderId"]
        
        # Calculate refund amount if not provided
        if refund_amount is None:
            refund_calculation = orders_service.calculate_refund_due(order_data, refund_type)
            if not refund_calculation["success"]:
                raise HTTPException(status_code=400, detail=refund_calculation["message"])
            refund_amount = refund_calculation["refund_amount"]
        
        # Process refund or credit
        if refund_amount and refund_amount > 0:
            if refund_type == "credit":
                refund_result = orders_service.create_store_credit(order_id, refund_amount)
            else:
                refund_result = orders_service.create_refund(order_id, refund_amount)
            
            if not refund_result["success"]:
                raise HTTPException(status_code=400, detail=f"Failed to create {refund_type}: {refund_result['message']}")
        else:
            raise HTTPException(status_code=400, detail="No refund amount calculated")
        
        return {
            "success": True,
            "message": f"{refund_type.title()} created successfully",
            "data": {
                "order_id": order_id,
                "order_number": order_number,
                "refund_amount": refund_amount,
                "refund_type": refund_type,
                "refund_result": refund_result,
                "customer": order_data.get("customer", {})
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating refund for order {order_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating refund: {str(e)}")

@router.get("/{order_number}/validate-email")
async def validate_order_email(
    order_number: str,
    email: str = Query(..., description="Email to validate against the order's customer email")
) -> Dict[str, Any]:
    """
    Validate if the provided email matches the order's customer email
    Used for form validation and security checks
    """
    try:
        # Fetch order details by order number
        result = orders_service.fetch_order_details(order_name=order_number)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        order_data = result["data"]
        print(f"order_data: \n {json.dumps(order_data, indent=2)} \n\n")
        order_customer_email = order_data.get("customer", {}).get("email", "").lower().strip()
        provided_email = email.lower().strip()
        
        # Check if emails match
        email_matches = order_customer_email == provided_email
        
        logger.info(f"Email validation for order {order_number}: {email_matches}")
        logger.info(f"Order email: {order_customer_email}, Provided email: {provided_email}")
        
        return {
            "success": True,
            "data": {
                "order_number": order_number,
                "email_matches": email_matches,
                "order_customer_email": order_customer_email,
                "provided_email": provided_email,
                "order_name": order_data.get("orderName", ""),
                "customer_name": f"{order_data.get('customer', {}).get('firstName', '')} {order_data.get('customer', {}).get('lastName', '')}".strip()
            },
            "message": f"Email {'matches' if email_matches else 'does not match'} order customer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating email for order {order_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating email: {str(e)}")

@router.post("/{order_number}/restock")
async def restock_order_inventory(
    order_number: str,
    variant_name: Optional[str] = Query(None, description="Specific variant to restock"),
    email: Optional[str] = Query(None, description="Email to search by if order number fails")
) -> Dict[str, Any]:
    """
    Restock inventory for an order's product variants
    """
    try:
        # Get the order details
        order_result = orders_service.fetch_order_details(order_name=order_number)
        
        if not order_result["success"] and email:
            order_result = orders_service.fetch_order_details(email=email)
        
        if not order_result["success"]:
            raise HTTPException(status_code=404, detail=order_result["message"])
        
        order_data = order_result["data"]
        variants = order_data.get("product", {}).get("variants", [])
        
        if not variants:
            raise HTTPException(status_code=400, detail="No variants found for this order")
        
        restock_results = []
        
        if variant_name:
            # Restock specific variant
            target_variant = next((v for v in variants if variant_name.lower() in v["variantName"].lower()), None)
            if not target_variant:
                raise HTTPException(status_code=404, detail=f"Variant '{variant_name}' not found")
            
            # Note: restock_inventory expects order_id, not inventory_item_id
            # For now, we'll use the order_id from the order_data
            order_id = order_data.get("id", "")
            if order_id:
                restock_result = orders_service.restock_order_inventory(order_id)
                restock_results.append({
                    "variant": target_variant["variantName"],
                    "inventory_item_id": target_variant.get("inventoryItemId", ""),
                    "result": restock_result
                })
            else:
                raise HTTPException(status_code=400, detail="Order ID not found for restocking")
        else:
            # Restock all variants - use the order_id to restock all line items
            order_id = order_data.get("id", "")
            if order_id:
                restock_result = orders_service.restock_order_inventory(order_id)
                restock_results.append({
                    "variant": "All variants",
                    "order_id": order_id,
                    "result": restock_result
                })
            else:
                raise HTTPException(status_code=400, detail="Order ID not found for restocking")
        
        if not restock_results:
            raise HTTPException(status_code=400, detail="No variants with inventory items found to restock")
        
        return {
            "success": True,
            "message": "Inventory restocking completed",
            "data": {
                "order_number": order_number,
                "restock_results": restock_results
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restocking inventory for order {order_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error restocking inventory: {str(e)}")

@router.post("/{order_number}/slack-notification")
async def send_slack_notification(
    order_number: str,
    request: SlackNotificationRequest
) -> Dict[str, Any]:
    """
    Send a refund request notification to Slack without processing the refund
    This is used by the Google Apps Script form submission to send notifications only
    """
    try:
        logger.info(f"Sending Slack notification for order {order_number}")
        
        # If order_data is provided, use it; otherwise fetch from Shopify
        if request.order_data:
            order_data = request.order_data
        else:
            # Fetch order details from Shopify
            order_result = orders_service.fetch_order_details(order_name=order_number)
            if not order_result["success"]:
                raise HTTPException(status_code=404, detail=order_result["message"])
            order_data = order_result["data"]
        
        # Send notification to Slack
        # First calculate refund information
        refund_calculation = orders_service.calculate_refund_due(order_data, request.refund_type)
        
        # Prepare requestor info
        requestor_info = {
            "name": request.requestor_name,
            "email": request.requestor_email,
            "refund_type": request.refund_type,
            "notes": request.notes
        }
        
        slack_result = slack_service.send_refund_request_notification(
            order_data={"order": order_data},
            refund_calculation=refund_calculation,
            requestor_info=requestor_info,
            sheet_link=request.sheet_link
        )
        
        if not slack_result["success"]:
            error_message = slack_result.get('error', slack_result.get('message', 'Unknown error'))
            raise HTTPException(status_code=500, detail=f"Failed to send Slack notification: {error_message}")
        
        return {
            "success": True,
            "message": "Slack notification sent successfully",
            "data": {
                "order_number": order_number,
                "requestor_email": request.requestor_email,
                "refund_type": request.refund_type,
                "slack_result": slack_result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending Slack notification for order {order_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending Slack notification: {str(e)}") 