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
