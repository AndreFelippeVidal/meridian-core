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
