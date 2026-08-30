"""Thin wrapper around the Razorpay test-mode SDK — retry, payment link creation, notify."""
import razorpay
from app.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def retry_subscription_charge(subscription_id: str):
    raise NotImplementedError

def create_payment_link(amount_paise: int, customer_id: str):
    raise NotImplementedError
