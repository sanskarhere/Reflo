"""
Generates a synthetic batch (target: >=50 records, matches Track 4's own bar)
of failed subscription payments with realistic Razorpay-style error codes,
for driving the pipeline end-to-end before any real merchant data exists.
"""

def generate_batch(n: int = 50) -> list[dict]:
    raise NotImplementedError
