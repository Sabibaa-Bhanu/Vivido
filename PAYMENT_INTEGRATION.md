# Razorpay Payment Integration - API Documentation

## Overview

This document describes the Razorpay payment gateway integration for Vivido image processing application.

## Table of Contents

1. [Payment Flow](#payment-flow)
2. [API Functions](#api-functions)
3. [Configuration](#configuration)
4. [Testing](#testing)
5. [Webhook Handling](#webhook-handling)
6. [Error Handling](#error-handling)

---

## Payment Flow

### Complete Payment Process

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │     │   Backend   │     │  Razorpay  │     │  Database   │
│  selects    │────▶│  creates    │────▶│   Checkout │     │   stores    │
│  image      │     │   order     │     │   UI       │     │  details    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                │                    
                                                ▼                    
                                        ┌─────────────┐     
                                        │  Payment    │     
                                        │  Success    │     
                                        └─────────────┘     
                                                │                    
                                                ▼                    
                                        ┌─────────────┐     ┌─────────────┐
                                        │  Verify     │────▶│  Update     │
                                        │  signature  │     │  status     │
                                        └─────────────┘     └─────────────┘
```

### Step-by-Step Process

1. **User Action**: User selects an image and quality option, clicks "Download"
2. **Create Order**: Backend calls `create_payment_order()` to generate Razorpay order
3. **Payment UI**: Frontend displays Razorpay Checkout with order details
4. **User Payment**: User enters card details and completes payment
5. **Verification**: Backend verifies payment signature using `verify_payment_signature()`
6. **Update Status**: Database is updated with payment status using `update_transaction_status()`
7. **Download**: User can download the image after successful payment

---

## API Functions

### 1. create_payment_order()

Creates a new Razorpay payment order.

**Function Signature:**
```python
def create_payment_order(
    user_id: int,
    amount: int = None,
    currency: str = "INR",
    receipt: str = None,
    image_quality: str = "standard",
    notes: dict = None
) -> dict
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | int | Yes | User's ID |
| amount | int | No | Amount in paise (auto-calculated if None) |
| currency | str | No | Currency code (default: INR) |
| receipt | str | No | Receipt ID (auto-generated if None) |
| image_quality | str | No | Image quality (standard/hd/premium) |
| notes | dict | No | Additional notes |

**Returns:**
```json
{
    "success": true,
    "order_id": "order_xxx",
    "amount": 1000,
    "currency": "INR",
    "receipt": "receipt_xxx",
    "status": "created",
    "key_id": "rzp_test_xxx"
}
```

**Example:**
```python
from backend.razorpay_payment import create_payment_order

result = create_payment_order(
    user_id=1,
    image_quality="hd"
)

if result["success"]:
    order_id = result["order_id"]
    # Pass to frontend for Razorpay Checkout
```

---

### 2. verify_payment_signature()

Verifies the authenticity of payment response.

**Function Signature:**
```python
def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> tuple
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| razorpay_order_id | str | Yes | Order ID from Razorpay |
| razorpay_payment_id | str | Yes | Payment ID from Razorpay |
| razorpay_signature | str | Yes | Signature from Razorpay |

**Returns:**
```python
(True, None)  # Valid signature
(False, "error message")  # Invalid signature
```

**Example:**
```python
from backend.razorpay_payment import verify_payment_signature

is_valid, error = verify_payment_signature(
    razorpay_order_id="order_xxx",
    razorpay_payment_id="pay_xxx",
    razorpay_signature="signature_from_razorpay"
)

if not is_valid:
    # Handle invalid payment
    print(f"Payment verification failed: {error}")
```

---

### 3. update_transaction_status()

Updates transaction status in the database.

**Function Signature:**
```python
def update_transaction_status(
    order_id: str,
    payment_id: str = None,
    status: str = "SUCCESS",
    payment_method: str = None,
    error_message: str = None
) -> bool
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| order_id | str | Yes | Razorpay order ID |
| payment_id | str | No | Razorpay payment ID |
| status | str | No | Status (PENDING/SUCCESS/FAILED) |
| payment_method | str | No | Payment method used |
| error_message | str | No | Error message if failed |

**Returns:**
```python
True  # Success
False  # Failure
```

---

### 4. process_successful_payment()

Processes a successful payment end-to-end.

**Function Signature:**
```python
def process_successful_payment(
    order_id: str,
    payment_id: str,
    signature: str
) -> dict
```

**Returns:**
```json
{
    "success": true,
    "order_id": "order_xxx",
    "payment_id": "pay_xxx",
    "user_id": 1,
    "amount": 1000,
    "status": "SUCCESS"
}
```

---

### 5. handle_webhook_event()

Handles Razorpay webhook events.

**Function Signature:**
```python
def handle_webhook_event(event_data: dict) -> dict
```

**Supported Events:**
- `payment.captured` - Payment successful
- `payment.failed` - Payment failed
- `order.paid` - Order paid

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Razorpay Keys (get from https://dashboard.razorpay.com/)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxxxxxxx
```

### Payment Amounts

Configure in `backend/razorpay_payment.py`:

```python
PAYMENT_AMOUNTS = {
    "per_image": 1000,        # ₹10
    "per_image_hd": 2000,    # ₹20
    "per_image_premium": 5000, # ₹50
}
```

---

## Testing

### Test Card Numbers

Use these cards in Razorpay test mode:

| Card Number | Expiry | CVV | OTP | Result |
|-------------|--------|-----|-----|--------|
| 4111 1111 1111 1111 | 12/25 | 123 | 123456 | Success |
| 4111 1111 1111 1110 | Any | Any | Any | Failure |

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run payment tests
python tests/test_payment.py
```

### Test Coverage

1. ✓ Configuration check
2. ✓ Create payment order
3. ✓ Custom amount order
4. ✓ Signature verification
5. ✓ Transaction status update
6. ✓ Webhook signature
7. ✓ Payment amounts
8. ✓ Test card details
9. ✓ Database schema

---

## Webhook Handling

### Setting Up Webhooks

1. Go to Razorpay Dashboard → Settings → Webhooks
2. Add new webhook with your endpoint URL
3. Select events: `payment.captured`, `payment.failed`, `order.paid`
4. Generate and save webhook secret

### Webhook Endpoint Example

```python
from flask import Flask, request, jsonify
from backend.razorpay_payment import handle_webhook_event, verify_webhook_signature

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def razorpay_webhook():
    # Get signature from header
    signature = request.headers.get('X-Razorpay-Signature')
    
    # Verify webhook signature
    if not verify_webhook_signature(request.data.decode(), signature):
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Process webhook event
    event_data = request.get_json()
    result = handle_webhook_event(event_data)
    
    return jsonify(result), 200
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `RAZORPAY_ERROR` | Invalid API keys | Check KEY_ID and KEY_SECRET |
| `NETWORK_ERROR` | Network issue | Retry the request |
| `SIGNATURE_ERROR` | Invalid signature | Verify signature calculation |
| `ORDER_NOT_FOUND` | Wrong order ID | Check order ID in database |

### Error Handling Example

```python
from backend.razorpay_payment import create_payment_order
from razorpay import errors as razorpay_errors

try:
    result = create_payment_order(user_id=1, amount=1000)
    
    if not result["success"]:
        # Handle payment initialization failure
        error_message = result["error"]
        # Show error to user or log
        
except razorpay_errors.RazorpayError as e:
    # Handle Razorpay-specific errors
    print(f"Razorpay error: {e}")
    
except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected error: {e}")
```

---

## Database Schema

### Transactions Table

```sql
CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    gateway_transaction_id TEXT UNIQUE,
    amount REAL NOT NULL,
    payment_status TEXT NOT NULL
        CHECK(payment_status IN ('PENDING','SUCCESS','FAILED')),
    payment_method TEXT NOT NULL
        CHECK(payment_method IN ('UPI','DEBIT_CARD','CREDIT_CARD','NETBANKING','WALLET')),
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

---

## Security Best Practices

1. **Never expose API secret** in frontend code
2. **Verify signatures** on server side
3. **Use webhooks** for reliable payment confirmation
4. **Log all transactions** for auditing
5. **Implement idempotency** for retry handling

---

## Support

For Razorpay integration support:
- Email: support@razorpay.com
- Documentation: https://razorpay.com/docs/
- Dashboard: https://dashboard.razorpay.com/
