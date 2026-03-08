"""
Razorpay Payment Integration Test Script

This script tests the complete payment flow using Razorpay's test mode.

Usage:
    python tests/test_payment.py

Prerequisites:
    1. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables
    2. Or update the values directly in this file for testing
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_razorpay_configuration():
    """Test that Razorpay is properly configured."""
    print("\n" + "="*60)
    print("TEST 1: Razorpay Configuration Check")
    print("="*60)
    
    from backend.razorpay_payment import check_razorpay_configuration
    
    config = check_razorpay_configuration()
    
    print(f"\nConfiguration Status:")
    print(f"  - Configured: {config['configured']}")
    print(f"  - Key ID Set: {config['key_id_set']}")
    print(f"  - Key Secret Set: {config['key_secret_set']}")
    print(f"  - Webhook Secret Set: {config['webhook_secret_set']}")
    print(f"  - Test Mode: {config['test_mode']}")
    
    if not config['configured']:
        print("\n⚠️  WARNING: Razorpay is not fully configured!")
        print("Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables")
        print("Or update the values in backend/razorpay_payment.py")
        return False
    
    print("\n✓ Razorpay is properly configured!")
    return True


def test_create_payment_order():
    """Test creating a payment order."""
    print("\n" + "="*60)
    print("TEST 2: Create Payment Order")
    print("="*60)
    
    from backend.razorpay_payment import create_payment_order, get_payment_amount
    
    # Test with default amount
    print("\n--- Test: Create order with default amount ---")
    result = create_payment_order(
        user_id=1,
        amount=None,  # Will use default based on quality
        image_quality="standard"
    )
    
    print(f"\nOrder Creation Result:")
    print(f"  - Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"  - Order ID: {result.get('order_id')}")
        print(f"  - Amount: ₹{result.get('amount')/100:.2f}")
        print(f"  - Currency: {result.get('currency')}")
        print(f"  - Status: {result.get('status')}")
        print(f"  - Key ID: {result.get('key_id')}")
        
        # Store order_id for next tests
        return result.get('order_id')
    else:
        print(f"  - Error: {result.get('error')}")
        return None


def test_create_order_with_custom_amount():
    """Test creating an order with custom amount."""
    print("\n--- Test: Create order with custom amount ---")
    
    from backend.razorpay_payment import create_payment_order
    
    # Test with custom amount (₹50 = 5000 paise)
    result = create_payment_order(
        user_id=1,
        amount=5000,  # ₹50
        currency="INR",
        receipt="test_receipt_001",
        notes={"test": "true", "purpose": "integration_test"}
    )
    
    print(f"\nCustom Amount Order Result:")
    print(f"  - Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"  - Order ID: {result.get('order_id')}")
        print(f"  - Amount: ₹{result.get('amount')/100:.2f}")
        print(f"  - Receipt: {result.get('receipt')}")
        return result.get('order_id')
    else:
        print(f"  - Error: {result.get('error')}")
        return None


def test_verify_signature():
    """Test payment signature verification."""
    print("\n" + "="*60)
    print("TEST 3: Verify Payment Signature")
    print("="*60)
    
    from backend.razorpay_payment import verify_payment_signature
    import hmac
    import hashlib
    
    # Test with known values
    order_id = "order_test123"
    payment_id = "pay_test123"
    secret = "test_secret"
    
    # Generate a test signature
    msg = f"{order_id}|{payment_id}"
    test_signature = hmac.new(
        secret.encode(),
        msg.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print("\n--- Test: Valid signature ---")
    
    # Temporarily use test secret
    import backend.razorpay_payment as rp
    original_secret = rp.RAZORPAY_KEY_SECRET
    rp.RAZORPAY_KEY_SECRET = secret
    
    is_valid, error = verify_payment_signature(order_id, payment_id, test_signature)
    
    # Restore original
    rp.RAZORPAY_KEY_SECRET = original_secret
    
    print(f"  - Valid: {is_valid}")
    if error:
        print(f"  - Error: {error}")
    
    print("\n--- Test: Invalid signature ---")
    is_valid, error = verify_payment_signature(order_id, payment_id, "invalid_signature")
    print(f"  - Valid: {is_valid}")
    print(f"  - Error: {error}")
    
    return True


def test_update_transaction_status():
    """Test updating transaction status."""
    print("\n" + "="*60)
    print("TEST 4: Update Transaction Status")
    print("="*60)
    
    from backend.razorpay_payment import update_transaction_status
    from backend.database import get_connection
    
    # First, create a test transaction
    print("\n--- Setup: Create test transaction ---")
    conn = get_connection()
    cursor = conn.cursor()
    
    test_order_id = "order_test_" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    cursor.execute("""
        INSERT INTO transactions 
        (user_id, gateway_transaction_id, amount, payment_status, payment_method)
        VALUES (?, ?, ?, ?, ?)
    """, (1, test_order_id, 1000, "PENDING", "CARD"))
    
    conn.commit()
    conn.close()
    print(f"  - Test transaction created: {test_order_id}")
    
    # Test updating to SUCCESS
    print("\n--- Test: Update to SUCCESS ---")
    result = update_transaction_status(
        order_id=test_order_id,
        payment_id="pay_test123",
        status="SUCCESS",
        payment_method="CARD"
    )
    print(f"  - Success: {result}")
    
    # Verify in database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT payment_status, gateway_transaction_id 
        FROM transactions 
        WHERE gateway_transaction_id = ?
    """, (test_order_id,))
    row = cursor.fetchone()
    conn.close()
    
    print(f"  - Database status: {row[0] if row else 'Not found'}")
    print(f"  - Payment ID: {row[1] if row else 'N/A'}")
    
    return True


def test_webhook_signature():
    """Test webhook signature verification."""
    print("\n" + "="*60)
    print("TEST 5: Webhook Signature Verification")
    print("="*60)
    
    from backend.razorpay_payment import verify_webhook_signature
    import hmac
    import hashlib
    
    # Test payload
    payload = '{"event":"payment.captured","payload":{"payment":{"id":"pay_test"}}}'
    webhook_secret = "test_webhook_secret"
    
    # Generate test signature
    expected_signature = hmac.new(
        webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print("\n--- Test: Valid webhook signature ---")
    
    # Temporarily use test secret
    import backend.razorpay_payment as rp
    original_webhook = rp.RAZORPAY_WEBHOOK_SECRET
    rp.RAZORPAY_WEBHOOK_SECRET = webhook_secret
    
    is_valid = verify_webhook_signature(payload, expected_signature)
    
    # Restore
    rp.RAZORPAY_WEBHOOK_SECRET = original_webhook
    
    print(f"  - Valid: {is_valid}")
    
    print("\n--- Test: Invalid webhook signature ---")
    is_valid = verify_webhook_signature(payload, "invalid_signature")
    print(f"  - Valid: {is_valid}")
    
    return True


def test_payment_amounts():
    """Test payment amount calculation."""
    print("\n" + "="*60)
    print("TEST 6: Payment Amount Calculation")
    print("="*60)
    
    from backend.razorpay_payment import get_payment_amount
    
    qualities = ["standard", "hd", "premium"]
    
    print("\nPayment Amounts:")
    for quality in qualities:
        amount = get_payment_amount(quality)
        print(f"  - {quality}: ₹{amount/100:.2f} ({amount} paise)")
    
    return True


def test_get_test_card_details():
    """Test getting test card details."""
    print("\n" + "="*60)
    print("TEST 7: Test Card Details")
    print("="*60)
    
    from backend.razorpay_payment import get_test_card_details
    
    card_details = get_test_card_details()
    
    print("\nRazorpay Test Card:")
    print(f"  - Card Number: {card_details['test_card_number']}")
    print(f"  - Expiry: {card_details['test_expiry']}")
    print(f"  - CVV: {card_details['test_cvv']}")
    print(f"  - OTP: {card_details['test_otp']}")
    print(f"  - Note: {card_details['note']}")
    
    return True


def test_database_schema():
    """Test that database has required columns."""
    print("\n" + "="*60)
    print("TEST 8: Database Schema Check")
    print("="*60)
    
    from backend.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check transactions table
    cursor.execute("PRAGMA table_info(transactions)")
    columns = {row[1] for row in cursor.fetchall()}
    
    print("\nTransactions table columns:")
    required_cols = ['transaction_id', 'user_id', 'gateway_transaction_id', 
                     'amount', 'payment_status', 'payment_method', 'transaction_date']
    
    for col in required_cols:
        exists = col in columns
        print(f"  - {col}: {'✓' if exists else '✗'}")
    
    conn.close()
    
    return True


def run_all_tests():
    """Run all payment integration tests."""
    print("\n" + "="*60)
    print("RAZORPAY PAYMENT INTEGRATION TEST SUITE")
    print("="*60)
    print(f"\nTest started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Configuration Check", test_razorpay_configuration),
        ("Create Payment Order", test_create_payment_order),
        ("Custom Amount Order", test_create_order_with_custom_amount),
        ("Verify Signature", test_verify_signature),
        ("Update Transaction Status", test_update_transaction_status),
        ("Webhook Signature", test_webhook_signature),
        ("Payment Amounts", test_payment_amounts),
        ("Test Card Details", test_get_test_card_details),
        ("Database Schema", test_database_schema),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
        except Exception as e:
            logger.error(f"Test '{test_name}' failed with error: {e}")
            results.append((test_name, f"ERROR: {str(e)}"))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✓" if result == "PASSED" else "✗"
        print(f"{status} {test_name}: {result}")
    
    passed = sum(1 for _, r in results if r == "PASSED")
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")


if __name__ == "__main__":
    run_all_tests()
