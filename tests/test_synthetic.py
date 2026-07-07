from meridian.synthetic import (
    _EVENT_TYPES,
    generate_customers,
    generate_events,
    generate_order_items,
    generate_orders,
    generate_payments,
    generate_products,
    generate_reviews,
    generate_support_tickets,
    product_docs,
)


def test_generate_customers_is_deterministic() -> None:
    a = generate_customers(10)
    b = generate_customers(10)
    assert a.equals(b)
    assert a.height == 10
    assert a["customer_id"][0] == "C000001"


def test_generate_customers_has_segment() -> None:
    df = generate_customers(20)
    assert "segment" in df.columns
    valid = {"standard", "premium", "vip"}
    assert set(df["segment"].to_list()).issubset(valid)


def test_generate_products_is_deterministic() -> None:
    a = generate_products(10)
    b = generate_products(10)
    assert a.equals(b)
    assert a.height == 10
    assert a["product_id"][0] == "P000001"


def test_generate_products_cost_non_negative() -> None:
    df = generate_products(50)
    assert (df["price"] >= 0).all()
    assert (df["cost"] >= 0).all()


def test_generate_orders_is_deterministic() -> None:
    customers = generate_customers(20)
    a = generate_orders(customers, 50)
    b = generate_orders(customers, 50)
    assert a.equals(b)
    assert a.height == 50
    assert a["order_id"][0] == "ORD000001"


def test_generate_order_items_is_deterministic() -> None:
    customers = generate_customers(20)
    products = generate_products(10)
    orders = generate_orders(customers, 30)
    a = generate_order_items(orders, products)
    b = generate_order_items(orders, products)
    assert a.equals(b)


def test_generate_payments_is_deterministic() -> None:
    customers = generate_customers(20)
    orders = generate_orders(customers, 30)
    a = generate_payments(orders)
    b = generate_payments(orders)
    assert a.equals(b)
    assert a.height == orders.height


def test_referential_integrity() -> None:
    customers = generate_customers(100)
    products = generate_products(50)
    orders = generate_orders(customers, 200)
    items = generate_order_items(orders, products)
    payments = generate_payments(orders)

    customer_ids = set(customers["customer_id"].to_list())
    order_ids = set(orders["order_id"].to_list())
    product_ids = set(products["product_id"].to_list())

    # Every FK must resolve
    assert set(orders["customer_id"].to_list()).issubset(customer_ids)
    assert set(items["order_id"].to_list()).issubset(order_ids)
    assert set(items["product_id"].to_list()).issubset(product_ids)
    assert set(payments["order_id"].to_list()).issubset(order_ids)


def test_non_negative_invariants() -> None:
    customers = generate_customers(50)
    products = generate_products(20)
    orders = generate_orders(customers, 100)
    items = generate_order_items(orders, products)
    payments = generate_payments(orders)

    assert (items["qty"] >= 1).all()
    assert (items["unit_price"] >= 0).all()
    assert (payments["amount"] >= 0).all()


def test_payments_one_per_order() -> None:
    customers = generate_customers(10)
    orders = generate_orders(customers, 20)
    payments = generate_payments(orders)
    assert payments.height == orders.height
    assert payments["order_id"].n_unique() == orders.height


# ── Clickstream events (Project 2 — streaming) ────────────────────────────────


def _events_fixture(n_sessions: int = 40, seed: int = 42):
    customers = generate_customers(50)
    products = generate_products(30)
    return generate_events(customers, products, n_sessions, seed=seed)


def test_generate_events_is_deterministic() -> None:
    a = _events_fixture()
    b = _events_fixture()
    assert a.equals(b)
    assert a["event_id"][0] == "E000001"


def test_generate_events_valid_event_types() -> None:
    events = _events_fixture()
    assert set(events["event_type"].to_list()).issubset(set(_EVENT_TYPES))


def test_generate_events_session_coherence() -> None:
    events = _events_fixture()
    # Every session belongs to exactly one customer, starts with page_view, and
    # has strictly increasing timestamps.
    for (session_id,), grp in events.group_by(["session_id"]):
        assert grp["customer_id"].n_unique() == 1, f"{session_id} spans multiple customers"
        assert grp["event_type"].to_list()[0] == "page_view"
        ts = grp["ts"].to_list()
        assert ts == sorted(ts) and len(ts) == len(set(ts)), f"{session_id} ts not monotonic"


def test_generate_events_purchase_follows_checkout() -> None:
    events = _events_fixture()
    for (session_id,), grp in events.group_by(["session_id"]):
        types = grp["event_type"].to_list()
        if "purchase" in types:
            assert "checkout_start" in types, f"{session_id} purchased without checkout_start"
            assert types.index("checkout_start") < types.index("purchase")


def test_generate_events_product_id_scoping() -> None:
    events = _events_fixture()
    product_scoped = {"product_view", "add_to_cart", "remove_from_cart", "purchase"}
    for row in events.iter_rows(named=True):
        if row["event_type"] in product_scoped:
            assert row["product_id"] is not None
        else:
            assert row["product_id"] is None


# ── Text corpus (Project 3 — RAG) ─────────────────────────────────────────────


def test_product_docs_shape() -> None:
    docs = product_docs()
    assert len(docs) >= 6
    ids = [d["doc_id"] for d in docs]
    assert len(ids) == len(set(ids)), "doc_ids must be unique"
    for doc in docs:
        assert set(doc) == {"doc_id", "title", "category", "body"}
        assert doc["body"].strip().startswith("#"), "body should be markdown"
        assert len(doc["body"]) > 100


def test_product_docs_is_immutable_snapshot() -> None:
    a = product_docs()
    a[0]["title"] = "mutated"
    b = product_docs()
    assert b[0]["title"] != "mutated", "callers must not mutate the module corpus"


def test_generate_support_tickets_is_deterministic() -> None:
    customers = generate_customers(50)
    orders = generate_orders(customers, 100)
    a = generate_support_tickets(customers, orders, 40)
    b = generate_support_tickets(customers, orders, 40)
    assert a.equals(b)
    assert a.height == 40
    assert a["ticket_id"][0] == "TCK000001"


def test_support_tickets_referential_integrity() -> None:
    customers = generate_customers(50)
    orders = generate_orders(customers, 100)
    tickets = generate_support_tickets(customers, orders, 60)
    order_map = dict(
        zip(orders["order_id"].to_list(), orders["customer_id"].to_list(), strict=True)
    )
    valid_status = {"open", "pending", "resolved", "closed"}
    for row in tickets.iter_rows(named=True):
        assert row["order_id"] in order_map
        # the ticket's customer matches the order it references
        assert row["customer_id"] == order_map[row["order_id"]]
        assert row["status"] in valid_status
        # the referenced order appears in the ticket text (some templates are
        # account-scoped and only mention it in the body)
        mentions_order = row["order_id"] in row["subject"] or row["order_id"] in row["body"]
        assert mentions_order or "account" in row["subject"].lower()


def test_generate_reviews_is_deterministic() -> None:
    customers = generate_customers(50)
    products = generate_products(30)
    a = generate_reviews(customers, products, 40)
    b = generate_reviews(customers, products, 40)
    assert a.equals(b)
    assert a.height == 40
    assert a["review_id"][0] == "REV000001"


def test_reviews_referential_integrity_and_rating_range() -> None:
    customers = generate_customers(50)
    products = generate_products(30)
    reviews = generate_reviews(customers, products, 80)
    product_ids = set(products["product_id"].to_list())
    customer_ids = set(customers["customer_id"].to_list())
    assert set(reviews["product_id"].to_list()).issubset(product_ids)
    assert set(reviews["customer_id"].to_list()).issubset(customer_ids)
    assert reviews["rating"].min() >= 1
    assert reviews["rating"].max() <= 5
    assert (reviews["body"].str.len_chars() > 0).all()
