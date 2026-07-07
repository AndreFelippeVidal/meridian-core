"""Synthetic data for the Meridian marketplace.

The single source of truth for the fictional domain. Every project imports from here
so customer ids, product skus, and event shapes line up across the whole platform.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
from faker import Faker

# Fixed anchor so ordered_at / ts are reproducible regardless of run date.
_ANCHOR = datetime(2025, 6, 30)

_CATEGORIES = [
    "Electronics",
    "Clothing",
    "Home & Garden",
    "Books",
    "Sports",
    "Beauty",
    "Toys",
    "Food & Drink",
]
_ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]
_ORDER_CHANNELS = ["web", "mobile", "api"]
_PAYMENT_METHODS = ["card", "bank_transfer", "wallet", "crypto"]
_PAYMENT_STATUSES = ["pending", "completed", "failed", "refunded"]
_SEGMENTS = ["standard", "premium", "vip"]

# Clickstream funnel (Project 2 — streaming). A session walks this funnel; not
# every session reaches purchase. product_id is set only for product-scoped events.
_EVENT_TYPES = [
    "page_view",
    "product_view",
    "add_to_cart",
    "remove_from_cart",
    "checkout_start",
    "purchase",
]
_PRODUCT_SCOPED_EVENTS = {"product_view", "add_to_cart", "remove_from_cart", "purchase"}


def generate_customers(n: int, seed: int = 42) -> pl.DataFrame:
    """Return a deterministic DataFrame of n Meridian customers."""
    fake = Faker()
    Faker.seed(seed)
    rows = [
        {
            "customer_id": f"C{idx:06d}",
            "name": fake.name(),
            "email": fake.email(),
            "country": fake.country_code(),
            "signup_date": fake.date_between("-3y", "today").isoformat(),
            "segment": fake.random.choice(_SEGMENTS),
        }
        for idx in range(1, n + 1)
    ]
    return pl.DataFrame(rows)


def generate_products(n: int, seed: int = 42) -> pl.DataFrame:
    """Return a deterministic DataFrame of n Meridian products."""
    fake = Faker()
    Faker.seed(seed)
    rows = []
    for idx in range(1, n + 1):
        price = round(fake.random.uniform(10.0, 999.99), 2)
        cost = round(price * fake.random.uniform(0.25, 0.65), 2)
        rows.append(
            {
                "product_id": f"P{idx:06d}",
                "title": fake.catch_phrase(),
                "category": fake.random.choice(_CATEGORIES),
                "price": price,
                "cost": cost,
                "supplier_id": f"S{fake.random.randint(1, 50):06d}",
            }
        )
    return pl.DataFrame(rows)


def generate_orders(customers_df: pl.DataFrame, n: int, seed: int = 42) -> pl.DataFrame:
    """Return a deterministic DataFrame of n orders; each references a customer."""
    fake = Faker()
    Faker.seed(seed)
    customer_ids = customers_df["customer_id"].to_list()
    rows = []
    for idx in range(1, n + 1):
        ordered_at = _ANCHOR - timedelta(
            days=fake.random.randint(0, 730),
            hours=fake.random.randint(0, 23),
            minutes=fake.random.randint(0, 59),
        )
        rows.append(
            {
                "order_id": f"ORD{idx:06d}",
                "customer_id": fake.random.choice(customer_ids),
                "ordered_at": ordered_at,
                "status": fake.random.choice(_ORDER_STATUSES),
                "channel": fake.random.choice(_ORDER_CHANNELS),
            }
        )
    return pl.DataFrame(rows)


def generate_order_items(
    orders_df: pl.DataFrame,
    products_df: pl.DataFrame,
    seed: int = 42,
) -> pl.DataFrame:
    """Return order items; each order gets 1–4 line items referencing products."""
    fake = Faker()
    Faker.seed(seed)
    order_ids = orders_df["order_id"].to_list()
    price_by_id: dict[str, float] = dict(
        zip(
            products_df["product_id"].to_list(),
            products_df["price"].to_list(),
            strict=True,
        )
    )
    product_ids = list(price_by_id.keys())
    rows = []
    item_idx = 1
    for order_id in order_ids:
        for _ in range(fake.random.randint(1, 4)):
            prod_id = fake.random.choice(product_ids)
            rows.append(
                {
                    "order_item_id": f"OI{item_idx:06d}",
                    "order_id": order_id,
                    "product_id": prod_id,
                    "qty": fake.random.randint(1, 5),
                    "unit_price": price_by_id[prod_id],
                }
            )
            item_idx += 1
    return pl.DataFrame(rows)


def generate_events(
    customers_df: pl.DataFrame,
    products_df: pl.DataFrame,
    n_sessions: int,
    seed: int = 42,
) -> pl.DataFrame:
    """Return a deterministic, session-coherent clickstream.

    Each session belongs to one customer and walks a plausible funnel
    (page_view → product_view(s) → cart → checkout → purchase), with
    monotonically increasing ``ts`` and one row per event. Not every session
    reaches purchase, and ``purchase`` only ever follows a ``checkout_start``
    in the same session. ``product_id`` is populated only for product-scoped
    events. Real-time pacing is the producer's job; this stays deterministic.
    """
    fake = Faker()
    Faker.seed(seed)
    customer_ids = customers_df["customer_id"].to_list()
    product_ids = products_df["product_id"].to_list()

    rows = []
    event_idx = 1
    for session_num in range(1, n_sessions + 1):
        session_id = f"SESS{session_num:06d}"
        customer_id = fake.random.choice(customer_ids)

        # Build the coherent event sequence as (event_type, product_id) pairs.
        seq: list[tuple[str, str | None]] = [("page_view", None)]
        viewed = [fake.random.choice(product_ids) for _ in range(fake.random.randint(1, 4))]
        for prod_id in viewed:
            seq.append(("product_view", prod_id))

        carted: list[str] = []
        for prod_id in viewed:
            if fake.random.random() < 0.5:
                seq.append(("add_to_cart", prod_id))
                carted.append(prod_id)

        if carted and fake.random.random() < 0.3:
            dropped = fake.random.choice(carted)
            seq.append(("remove_from_cart", dropped))
            carted.remove(dropped)

        if carted and fake.random.random() < 0.6:
            seq.append(("checkout_start", None))
            if fake.random.random() < 0.7:
                for prod_id in carted:
                    seq.append(("purchase", prod_id))

        # Assign monotonically increasing timestamps within the session.
        ts = _ANCHOR - timedelta(
            days=fake.random.randint(0, 7),
            hours=fake.random.randint(0, 23),
            minutes=fake.random.randint(0, 59),
        )
        for event_type, prod_id in seq:
            ts = ts + timedelta(seconds=fake.random.randint(5, 120))
            rows.append(
                {
                    "event_id": f"E{event_idx:06d}",
                    "customer_id": customer_id,
                    "session_id": session_id,
                    "event_type": event_type,
                    "product_id": prod_id,
                    "ts": ts,
                }
            )
            event_idx += 1

    return pl.DataFrame(rows)


def generate_payments(orders_df: pl.DataFrame, seed: int = 42) -> pl.DataFrame:
    """Return one payment per order; ts is slightly after ordered_at."""
    fake = Faker()
    Faker.seed(seed)
    rows = []
    for idx, row in enumerate(orders_df.iter_rows(named=True), 1):
        ordered_at: datetime = row["ordered_at"]
        ts = ordered_at + timedelta(minutes=fake.random.randint(1, 1440))
        rows.append(
            {
                "payment_id": f"PAY{idx:06d}",
                "order_id": row["order_id"],
                "amount": round(fake.random.uniform(5.0, 9_999.99), 2),
                "method": fake.random.choice(_PAYMENT_METHODS),
                "status": fake.random.choice(_PAYMENT_STATUSES),
                "ts": ts,
            }
        )
    return pl.DataFrame(rows)


# ── Text corpus (Project 3 — RAG) ─────────────────────────────────────────────
# The authoritative Meridian support corpus: hand-authored policy/FAQ docs that
# answers must ground in, plus templated support tickets and product reviews.
# Kept deterministic and coherent so retrieval quality is meaningful in evals.

_TICKET_STATUSES = ["open", "pending", "resolved", "closed"]

# Authoritative policy corpus. Each doc carries concrete, checkable facts (days,
# windows, fees) so golden eval questions have unambiguous ground truth.
_PRODUCT_DOCS: list[dict[str, str]] = [
    {
        "doc_id": "DOC001",
        "title": "Shipping & Delivery Policy",
        "category": "shipping",
        "body": """# Shipping & Delivery Policy

Meridian ships to over 40 countries. Delivery times and costs depend on the
method you choose at checkout.

## Delivery options
- **Standard shipping** — 5–7 business days. Free on orders over $50, otherwise
  a flat $4.99.
- **Express shipping** — 2–3 business days for a flat $14.99.
- **Next-day shipping** — order before 2 PM local time for delivery the next
  business day for $24.99. Available in select metro areas only.

## Processing time
Orders are processed within 1 business day. Orders placed on weekends or public
holidays begin processing the next business day.

## International orders
International standard delivery takes 10–20 business days. Import duties and
taxes are the responsibility of the recipient and are not included in the
Meridian shipping fee.

## Tracking
A tracking number is emailed once your order ships. See the Order Tracking guide
for how to follow your parcel.""",
    },
    {
        "doc_id": "DOC002",
        "title": "Returns & Refunds Policy",
        "category": "returns",
        "body": """# Returns & Refunds Policy

We want you to be happy with your purchase. Most items can be returned within
**30 days of delivery** for a full refund.

## Eligibility
- Items must be unused, in their original packaging, and with tags attached.
- Final-sale, personalized, and perishable items cannot be returned.
- Opened software, hygiene, and intimate-apparel items are non-returnable once
  the seal is broken.

## How to start a return
1. Go to **My Orders**, select the order, and choose *Return item*.
2. Print the prepaid return label (domestic returns are free).
3. Drop the parcel at any partner carrier location.

## Refund timing
Once we receive and inspect the item, refunds are issued to the original payment
method within **5–10 business days**. Original express-shipping fees are
non-refundable.

## Exchanges
We do not process direct exchanges. Return the original item for a refund and
place a new order for the replacement.""",
    },
    {
        "doc_id": "DOC003",
        "title": "Warranty Policy",
        "category": "warranty",
        "body": """# Warranty Policy

Meridian products are covered by a **12-month limited warranty** from the date of
delivery against manufacturing defects.

## What is covered
- Faults in materials or workmanship under normal use.
- Electronics failures not caused by accidental or liquid damage.

## What is not covered
- Accidental damage, misuse, or unauthorized repairs.
- Normal wear and tear and cosmetic damage that does not affect function.
- Consumable parts such as batteries after 6 months.

## Making a warranty claim
Contact support with your order number and a description (photos help). If the
claim is approved we will repair or replace the item, or issue a refund if a
replacement is unavailable. Warranty claims do not extend the original warranty
period.""",
    },
    {
        "doc_id": "DOC004",
        "title": "Payments & Billing",
        "category": "payments",
        "body": """# Payments & Billing

## Accepted methods
We accept major credit and debit cards, bank transfer, Meridian Wallet, and
select cryptocurrencies. All payments are processed over an encrypted connection.

## When you are charged
Your card is authorized at checkout and charged when the order ships. For
pre-orders, you are charged when the item becomes available.

## Failed payments
If a payment fails, the order is held for **48 hours** so you can update your
details before it is automatically cancelled. Common causes are insufficient
funds, an expired card, or a bank fraud hold.

## Refunds
Refunds are always returned to the original payment method. Wallet refunds are
instant; card refunds take 5–10 business days to appear on your statement.

## Invoices
A VAT invoice is available under **My Orders → Invoice** for every completed
order.""",
    },
    {
        "doc_id": "DOC005",
        "title": "Account & Security",
        "category": "account",
        "body": """# Account & Security

## Signing in
Sign in with your email and password at meridian.example/login. If you have
forgotten your password, use *Forgot password* to receive a reset link valid for
60 minutes.

## Locked accounts
After 5 failed sign-in attempts your account is temporarily locked for 30
minutes to protect it. You can reset your password to regain access immediately.

## Two-factor authentication
We strongly recommend enabling 2FA under **Settings → Security**. You can use an
authenticator app or SMS codes.

## Updating details
Change your email, shipping addresses, and marketing preferences under
**Settings → Profile**. Changing your account email requires confirming a link
sent to the new address.

## Closing your account
Request account deletion under **Settings → Privacy**. Deletion is permanent and
removes your order history after any open orders are fulfilled.""",
    },
    {
        "doc_id": "DOC006",
        "title": "Order Tracking",
        "category": "shipping",
        "body": """# Order Tracking

## Finding your tracking number
Once an order ships, a tracking number is emailed to you and shown under
**My Orders**. Tracking can take up to 24 hours to show its first movement after
the label is created.

## Order statuses
- **Pending** — payment confirmed, not yet processed.
- **Processing** — being picked and packed.
- **Shipped** — handed to the carrier; tracking is active.
- **Delivered** — marked delivered by the carrier.

## My tracking hasn't updated
Carriers occasionally delay scans. If tracking has not updated for **5 business
days**, contact support and we will open an investigation with the carrier.

## Marked delivered but not received
Check with neighbours and around your property first. If it does not turn up
within 48 hours, contact support to file a claim.""",
    },
    {
        "doc_id": "DOC007",
        "title": "Cancellations & Changes",
        "category": "orders",
        "body": """# Cancellations & Changes

## Cancelling an order
You can cancel an order for a full refund while it is still **Pending** or
**Processing**, under **My Orders → Cancel**. Once an order is **Shipped** it can
no longer be cancelled — you may return it instead under the Returns policy.

## Changing an order
Shipping address and delivery method can be changed only while the order is
**Pending**. We cannot add or remove items from an existing order; cancel and
re-order instead.

## Out-of-stock items
If an item sells out after you order, we cancel just that line and refund it
automatically, shipping the rest of your order.""",
    },
    {
        "doc_id": "DOC008",
        "title": "Frequently Asked Questions",
        "category": "faq",
        "body": """# Frequently Asked Questions

**Do you ship internationally?** Yes, to over 40 countries. International
delivery takes 10–20 business days and duties may apply.

**How long do refunds take?** 5–10 business days to the original payment method
after we receive the returned item.

**Can I change my shipping address after ordering?** Only while the order is
still Pending.

**Is my payment information secure?** Yes. We never store full card numbers;
payments are handled by a PCI-compliant processor.

**How do I contact a human?** Use the *Contact support* button in the help
centre; we reply within 1 business day.

**Do you offer gift wrapping?** Yes, for $3.99 per item, selectable at
checkout.""",
    },
]

# Templated ticket bodies keyed by intent. Each references a real order and
# customer; {order_id} is substituted so tickets stay coherent with the domain.
_TICKET_TEMPLATES: list[tuple[str, str]] = [
    (
        "Where is my order {order_id}?",
        "I placed order {order_id} over a week ago and it still hasn't arrived. "
        "The tracking hasn't updated in days. Can you tell me where it is?",
    ),
    (
        "Refund not received for {order_id}",
        "I returned an item from order {order_id} two weeks ago but I still "
        "haven't seen the refund on my card. Please check the status.",
    ),
    (
        "Damaged item in order {order_id}",
        "The item from order {order_id} arrived with a cracked casing. It looks "
        "like it happened in transit. How do I get a replacement under warranty?",
    ),
    (
        "Payment failed for {order_id}",
        "I tried to pay for order {order_id} but the payment keeps failing even "
        "though my card has funds. What should I do before it gets cancelled?",
    ),
    (
        "Can't log into my account",
        "I've tried signing in several times for order {order_id} and now my "
        "account seems locked. How long until I can get back in?",
    ),
    (
        "How do I return an item from {order_id}?",
        "One of the products in order {order_id} isn't what I expected. It's "
        "unused and still boxed. What's the process and window for returning it?",
    ),
    (
        "Cancel order {order_id}",
        "I need to cancel order {order_id} — I ordered the wrong size. It hasn't "
        "shipped yet. Can you cancel it and refund me?",
    ),
    (
        "Change shipping address for {order_id}",
        "I just realised the address on order {order_id} is wrong. It still says "
        "pending. Can you update it before it ships?",
    ),
]

# Templated review bodies keyed by star rating for coherent sentiment.
_REVIEW_TEMPLATES: dict[int, list[str]] = {
    5: [
        "Absolutely love this. Exactly as described and arrived quickly. Would buy again.",
        "Outstanding quality for the price. It has exceeded my expectations completely.",
        "Five stars — works perfectly and the build feels premium. Highly recommend.",
    ],
    4: [
        "Really good overall. Minor niggles but I'm happy with the purchase.",
        "Solid product and fast shipping. Docking a star for the flimsy packaging.",
        "Does what it promises. Not perfect, but great value for the money.",
    ],
    3: [
        "It's okay. Nothing special and nothing terrible — it does the job.",
        "Average. Works fine but I expected a bit more for the price.",
        "Middle of the road. Fine for casual use, wouldn't rely on it heavily.",
    ],
    2: [
        "Disappointed. It felt cheaper than expected and stopped working well after a week.",
        "Not great. Arrived slowly and the quality isn't what the photos suggested.",
        "Below expectations. It functions, but I wouldn't buy it again.",
    ],
    1: [
        "Terrible. Broke almost immediately and support was slow to respond.",
        "Do not buy. Poor quality and nothing like the description.",
        "One star — arrived faulty and getting a refund was a hassle.",
    ],
}


def product_docs() -> list[dict[str, str]]:
    """Return the authoritative Meridian policy/FAQ corpus (RAG ground truth).

    Each doc has ``doc_id``, ``title``, ``category`` and a markdown ``body``.
    Hand-authored and stable so retrieved answers can be graded against known
    facts. Returns copies so callers can't mutate the module-level corpus.
    """
    return [dict(doc) for doc in _PRODUCT_DOCS]


def generate_support_tickets(
    customers_df: pl.DataFrame,
    orders_df: pl.DataFrame,
    n: int,
    seed: int = 42,
) -> pl.DataFrame:
    """Return n deterministic, coherent support tickets referencing real orders.

    Each ticket picks a real order (and its customer) and a templated intent, so
    ``customer_id``/``order_id`` always resolve against the domain.
    """
    fake = Faker()
    Faker.seed(seed)
    order_rows = list(orders_df.select(["order_id", "customer_id"]).iter_rows(named=True))
    rows = []
    for idx in range(1, n + 1):
        order = fake.random.choice(order_rows)
        subject, body = fake.random.choice(_TICKET_TEMPLATES)
        created_at = _ANCHOR - timedelta(
            days=fake.random.randint(0, 90),
            hours=fake.random.randint(0, 23),
            minutes=fake.random.randint(0, 59),
        )
        rows.append(
            {
                "ticket_id": f"TCK{idx:06d}",
                "customer_id": order["customer_id"],
                "order_id": order["order_id"],
                "subject": subject.format(order_id=order["order_id"]),
                "body": body.format(order_id=order["order_id"]),
                "status": fake.random.choice(_TICKET_STATUSES),
                "created_at": created_at,
            }
        )
    return pl.DataFrame(rows)


def generate_reviews(
    customers_df: pl.DataFrame,
    products_df: pl.DataFrame,
    n: int,
    seed: int = 42,
) -> pl.DataFrame:
    """Return n deterministic product reviews referencing real products.

    Sentiment matches the star ``rating`` (1–5) so review text is coherent for
    retrieval and downstream sentiment use.
    """
    fake = Faker()
    Faker.seed(seed)
    customer_ids = customers_df["customer_id"].to_list()
    product_ids = products_df["product_id"].to_list()
    rows = []
    for idx in range(1, n + 1):
        rating = fake.random.randint(1, 5)
        created_at = _ANCHOR - timedelta(
            days=fake.random.randint(0, 365),
            hours=fake.random.randint(0, 23),
        )
        rows.append(
            {
                "review_id": f"REV{idx:06d}",
                "customer_id": fake.random.choice(customer_ids),
                "product_id": fake.random.choice(product_ids),
                "rating": rating,
                "body": fake.random.choice(_REVIEW_TEMPLATES[rating]),
                "created_at": created_at,
            }
        )
    return pl.DataFrame(rows)
