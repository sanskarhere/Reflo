"""Central config — loaded once, imported everywhere. No secrets hardcoded."""
import os
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recovery.db")

MAX_RETRY_ATTEMPTS = 3
COOLDOWN_HOURS = 12
HIGH_VALUE_THRESHOLD_PAISE = 5_000_000  # ₹50,000, Razorpay amounts are in paise
