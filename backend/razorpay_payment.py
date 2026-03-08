"""
Razorpay Payment Gateway Integration Module for Vivido

This module handles:
- Creating payment orders
- Verifying payment signatures
- Updating transaction status
- Webhook handling
- Error handling for payment failures

Usage:
    import razorpay
    from backend.razorpay_payment import create_payment_order, verify_payment_signature, update_transaction_status
    
    # Create payment order
    order = create_payment_order(user_id=1, amount=5000, currency="INR")
    
    # Verify payment
    is_valid = verify_payment_signature(
        razorpay_order_id="order_xxx",
        razorpay_payment_id="pay_xxx", 
        razorpay_signature="signature"
    )
"""

import os
import hmac
import hashlib
import logging
import datetime
from typing import Optional, Dict, Any, Tuple

import razorpay
from razorpay import errors as razorpay_errors

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

# Razorpay API Keys - In production, use environment variables
# Get these from your Razorpay Dashboard: https://dashboard.razorpay.com/
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_YOUR_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "YOUR_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "YOUR_WEBHOOK_SECRET")

# Payment amount configuration (in paise - 100 paise = 1 INR)
# You can customize these amounts
PAYMENT_AMOUNTS = {
    "per_image": 1000,  # ₹10 per image
    "per_image_hd": 2000,  # ₹20 for HD quality
    "per_image_premium": 5000,  # ₹50 for premium
    "subscription_monthly": 50000,  # ₹500/month
    "subscription_yearly": 500000,  # ₹5000/year
}

# Default currency
DEFAULT_CURRENCY = "INR"

# Payment status constants
PAYMENT_STATUS_PENDING = "PENDING"
PAYMENT_STATUS_SUCCESS = "SUCCESS"
PAYMENT_STATUS_FAILED = "FAILED"

# Initialize Razorpay client
try:
    razorpay_client = razorpay.Client(
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )
    logger.info("Razorpay client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Razorpay client: {e}")
    razorpay_client = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_payment_amount(image_quality: str = "standard") -> int:
    """
    Get the payment amount based on image quality.
    
    Args:
        image_quality: Quality of the image (standard, hd, premium)
    
    Returns:
        Amount in paise
    """
    if image_quality == "hd":
        return PAYMENT_AMOUNTS["per_image_hd"]
    elif image_quality == "premium":
        return PAYMENT_AMOUNTS["per_image_premium"]
    else:
        return PAYMENT_AMOUNTS["per_image"]


def generate_receipt_id(user_id: int, image_id: Optional[int] = None) -> str:
    """
    Generate a unique receipt ID for the order.
    
    Args:
        user_id: The user's ID
        image_id: Optional image ID
    
    Returns:
        Unique receipt ID
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    if image_id:
        return f"vivido_{user_id}_{image_id}_{timestamp}"
    return f"vivido_{user_id}_{timestamp}"


def get_razorpay_client() -> Optional[razorpay.Client]:
    """
    Get the Razorpay client instance.
    
    Returns:
        Razorpay client or None if not initialized
    """
    return razorpay_client


# ============================================================
# CORE PAYMENT FUNCTIONS
# ============================================================

def create_payment_order(
    user_id: int,
    amount: int,
    currency: str = DEFAULT_CURRENCY,
    receipt: Optional[str] = None,
    image_quality: str = "standard",
    notes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a Razorpay payment order.
    
    Args:
        user_id: The user's ID
        amount: Amount in paise (e.g., 1000 = ₹10)
        currency: Currency code (default: INR)
        receipt: Optional receipt ID (generated if not provided)
        image_quality: Quality of the image for amount calculation
        notes: Optional additional notes
    
    Returns:
        Dictionary containing order details:
        {
            "success": True,
            "order_id": "order_xxx",
            "amount": 1000,
            "currency": "INR",
            "receipt": "receipt_xxx",
            "status": "created"
        }
    
    Raises:
        Exception: If payment creation fails
    """
    if not razorpay_client:
        logger.error("Razorpay client not initialized")
        return {
            "success": False,
            "error": "Payment system not configured. Please contact support."
        }
    
    try:
        # Calculate amount if not provided
        if amount is None or amount <= 0:
            amount = get_payment_amount(image_quality)
        
        # Generate receipt if not provided
        if not receipt:
            receipt = generate_receipt_id(user_id)
        
        # Prepare order data
        order_data = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,  # Auto-capture payment
            "notes": notes or {
                "user_id": str(user_id),
                "image_quality": image_quality,
                "platform": "Vivido"
            }
        }
        
        # Create order
        order = razorpay_client.order.create(data=order_data)
        
        logger.info(f"Payment order created: {order.get('id')} for user {user_id}")
        
        # Store order in database
        try:
            from backend.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO transactions 
                (user_id, gateway_transaction_id, amount, payment_status, payment_method)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, order.get('id'), amount, PAYMENT_STATUS_PENDING, "RAZORPAY"))
            
            conn.commit()
            conn.close()
            logger.info(f"Transaction record created for order {order.get('id')}")
            
        except Exception as db_error:
            logger.error(f"Failed to store transaction: {db_error}")
        
        return {
            "success": True,
            "order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "receipt": order.get("receipt"),
            "status": order.get("status"),
            "key_id": RAZORPAY_KEY_ID
        }
        
    except razorpay_errors.RazorpayError as e:
        logger.error(f"Razorpay error creating order: {e}")
        return {
            "success": False,
            "error": f"Payment initialization failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error creating payment order: {e}")
        return {
            "success": False,
            "error": f"Payment initialization failed: {str(e)}"
        }


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> Tuple[bool, Optional[str]]:
    """
    Verify the authenticity of a payment response.
    
    Args:
        razorpay_order_id: The order ID from Razorpay
        razorpay_payment_id: The payment ID from Razorpay
        razorpay_signature: The signature from Razorpay
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Generate signature using HMAC-SHA256
        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        if hmac.compare_digest(expected_signature, razorpay_signature):
            logger.info(f"Payment signature verified for {razorpay_payment_id}")
            return True, None
        else:
            logger.warning(f"Invalid payment signature for {razorpay_payment_id}")
            return False, "Invalid payment signature"
    
    except Exception as e:
        logger.error(f"Error verifying payment signature: {e}")
        return False, str(e)


def update_transaction_status(
    order_id: str,
    payment_id: Optional[str] = None,
    status: str = PAYMENT_STATUS_SUCCESS,
    payment_method: Optional[str] = None,
    error_message: Optional[str] = None
) -> bool:
    """
    Update the transaction status in the database.
    
    Args:
        order_id: The Razorpay order ID
        payment_id: The Razorpay payment ID
        status: Payment status (PENDING, SUCCESS, FAILED)
        payment_method: Payment method used
        error_message: Error message if failed
    
    Returns:
        True if update successful, False otherwise
    """
    try:
        from backend.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update transaction
        cursor.execute("""
            UPDATE transactions 
            SET payment_status = ?,
                gateway_transaction_id = COALESCE(?, gateway_transaction_id),
                payment_method = COALESCE(?, payment_method)
            WHERE gateway_transaction_id = ?
        """, (status, payment_id, payment_method, order_id))
        
        if cursor.rowcount == 0:
            # Try with receipt prefix
            cursor.execute("""
                UPDATE transactions 
                SET payment_status = ?,
                    gateway_transaction_id = COALESCE(?, gateway_transaction_id),
                    payment_method = COALESCE(?, payment_method)
                WHERE gateway_transaction_id = ? OR receipt LIKE ?
            """, (status, payment_id, payment_method, order_id, f"%{order_id}%"))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Transaction {order_id} updated to status: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating transaction status: {e}")
        return False


def process_successful_payment(
    order_id: str,
    payment_id: str,
    signature: str
) -> Dict[str, Any]:
    """
    Process a successful payment.
    
    Args:
        order_id: The Razorpay order ID
        payment_id: The Razorpay payment ID
        signature: The Razorpay signature
    
    Returns:
        Dictionary with processing result
    """
    # Verify signature
    is_valid, error = verify_payment_signature(order_id, payment_id, signature)
    
    if not is_valid:
        update_transaction_status(order_id, payment_id, PAYMENT_STATUS_FAILED, error_message=error)
        return {
            "success": False,
            "error": "Payment verification failed"
        }
    
    # Update transaction to success
    update_transaction_status(order_id, payment_id, PAYMENT_STATUS_SUCCESS, payment_method="CARD")
    
    # Get transaction details
    try:
        from backend.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, amount FROM transactions 
            WHERE gateway_transaction_id = ?
        """, (order_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_id, amount = result
            logger.info(f"Payment successful: Order {order_id}, User {user_id}, Amount {amount}")
            
            return {
                "success": True,
                "order_id": order_id,
                "payment_id": payment_id,
                "user_id": user_id,
                "amount": amount,
                "status": PAYMENT_STATUS_SUCCESS
            }
    
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
    
    return {
        "success": True,
        "order_id": order_id,
        "payment_id": payment_id,
        "status": PAYMENT_STATUS_SUCCESS
    }


def process_failed_payment(
    order_id: str,
    payment_id: Optional[str] = None,
    error: Optional[str] = None
) -> bool:
    """
    Process a failed payment.
    
    Args:
        order_id: The Razorpay order ID
        payment_id: The Razorpay payment ID (if available)
        error: Error message
    
    Returns:
        True if processed successfully
    """
    return update_transaction_status(
        order_id, 
        payment_id, 
        PAYMENT_STATUS_FAILED, 
        error_message=error
    )


# ============================================================
# WEBHOOK HANDLING
# ============================================================

def verify_webhook_signature(payload: str, signature: str) -> bool:
    """
    Verify the webhook signature from Razorpay.
    
    Args:
        payload: Raw request body
        signature: Signature from Razorpay header
    
    Returns:
        True if signature is valid
    """
    try:
        expected_signature = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


def handle_webhook_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a Razorpay webhook event.
    
    Args:
        event_data: The webhook event data
    
    Returns:
        Dictionary with processing result
    """
    event_type = event_data.get("event")
    payload = event_data.get("payload", {})
    
    logger.info(f"Processing webhook event: {event_type}")
    
    try:
        if event_type == "payment.captured":
            # Payment successful
            payment = payload.get("payment", {})
            order_id = payment.get("order_id")
            payment_id = payment.get("id")
            
            update_transaction_status(
                order_id, 
                payment_id, 
                PAYMENT_STATUS_SUCCESS,
                payment_method=payment.get("method", "UNKNOWN")
            )
            
            return {
                "success": True,
                "event": event_type,
                "status": "processed"
            }
        
        elif event_type == "payment.failed":
            # Payment failed
            payment = payload.get("payment", {})
            order_id = payment.get("order_id")
            payment_id = payment.get("id")
            error_description = payment.get("error_description", "Payment failed")
            
            update_transaction_status(
                order_id,
                payment_id,
                PAYMENT_STATUS_FAILED,
                error_message=error_description
            )
            
            return {
                "success": True,
                "event": event_type,
                "status": "processed"
            }
        
        elif event_type == "order.paid":
            # Order paid (alternative event)
            order = payload.get("order", {})
            order_id = order.get("id")
            
            update_transaction_status(order_id, status=PAYMENT_STATUS_SUCCESS)
            
            return {
                "success": True,
                "event": event_type,
                "status": "processed"
            }
        
        else:
            logger.info(f"Unhandled webhook event: {event_type}")
            return {
                "success": True,
                "event": event_type,
                "status": "ignored"
            }
    
    except Exception as e:
        logger.error(f"Error handling webhook event: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# PAYMENT UI HELPERS
# ============================================================

def get_payment_config_for_ui(user_id: int, image_quality: str = "standard") -> Dict[str, Any]:
    """
    Get payment configuration for the UI.
    
    Args:
        user_id: The user's ID
        image_quality: Quality of the image
    
    Returns:
        Dictionary with payment configuration
    """
    amount = get_payment_amount(image_quality)
    
    # Create order
    order_result = create_payment_order(
        user_id=user_id,
        amount=amount,
        image_quality=image_quality
    )
    
    if order_result.get("success"):
        return {
            "success": True,
            "key_id": RAZORPAY_KEY_ID,
            "order_id": order_result.get("order_id"),
            "amount": amount,
            "currency": DEFAULT_CURRENCY,
            "name": "Vivido",
            "description": f"Image Download - {image_quality.title()} Quality",
            "prefill": {
                "user_id": user_id
            }
        }
    else:
        return {
            "success": False,
            "error": order_result.get("error", "Failed to initialize payment")
        }


# ============================================================
# PAYMENT UTILITIES
# ============================================================

def get_transaction_history(user_id: int) -> list:
    """
    Get payment transaction history for a user.
    
    Args:
        user_id: The user's ID
    
    Returns:
        List of transactions
    """
    try:
        from backend.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT transaction_id, gateway_transaction_id, amount, 
                   payment_status, payment_method, transaction_date
            FROM transactions
            WHERE user_id = ?
            ORDER BY transaction_date DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "transaction_id": r[0],
                "order_id": r[1],
                "amount": r[2] / 100,  # Convert from paise to rupees
                "status": r[3],
                "method": r[4],
                "date": r[5]
            }
            for r in results
        ]
    
    except Exception as e:
        logger.error(f"Error getting transaction history: {e}")
        return []


def refund_payment(payment_id: str, amount: Optional[int] = None, reason: str = "") -> Dict[str, Any]:
    """
    Initiate a payment refund.
    
    Args:
        payment_id: The Razorpay payment ID
        amount: Amount to refund in paise (full amount if not specified)
        reason: Reason for refund
    
    Returns:
        Dictionary with refund result
    """
    if not razorpay_client:
        return {
            "success": False,
            "error": "Payment system not configured"
        }
    
    try:
        refund_data = {}
        if amount:
            refund_data["amount"] = amount
        if reason:
            refund_data["notes"] = {"reason": reason}
        
        refund = razorpay_client.payment.refund(payment_id, refund_data)
        
        logger.info(f"Refund initiated for payment {payment_id}: {refund.get('id')}")
        
        return {
            "success": True,
            "refund_id": refund.get("id"),
            "amount": refund.get("amount"),
            "status": refund.get("status")
        }
    
    except razorpay_errors.RazorpayError as e:
        logger.error(f"Razorpay error processing refund: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error processing refund: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# TEST MODE HELPERS
# ============================================================

def get_test_card_details() -> Dict[str, str]:
    """
    Get test card details for Razorpay test mode.
    
    Returns:
        Dictionary with test card information
    """
    return {
        "success": True,
        "test_card_number": "4111 1111 1111 1111",
        "test_expiry": "12/25",
        "test_cvv": "123",
        "test_otp": "123456",
        "note": "Use these test cards in Razorpay's test mode"
    }


# Configuration check function
def check_razorpay_configuration() -> Dict[str, Any]:
    """
    Check if Razorpay is properly configured.
    
    Returns:
        Dictionary with configuration status
    """
    is_configured = RAZORPAY_KEY_ID != "rzp_test_YOUR_KEY_ID" and RAZORPAY_KEY_SECRET != "YOUR_KEY_SECRET"
    
    return {
        "configured": is_configured,
        "key_id_set": RAZORPAY_KEY_ID != "rzp_test_YOUR_KEY_ID",
        "key_secret_set": RAZORPAY_KEY_SECRET != "YOUR_KEY_SECRET",
        "webhook_secret_set": RAZORPAY_WEBHOOK_SECRET != "YOUR_WEBHOOK_SECRET",
        "test_mode": "test" in RAZORPAY_KEY_ID.lower() if RAZORPAY_KEY_ID else True
    }
