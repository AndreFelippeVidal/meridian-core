"""Synthetic data for the Meridian marketplace.

The single source of truth for the fictional domain. Every project imports from here
so customer ids, product skus, and event shapes line up across the whole platform.
"""

from __future__ import annotations

import polars as pl
from faker import Faker


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
        }
        for idx in range(1, n + 1)
    ]
    return pl.DataFrame(rows)
