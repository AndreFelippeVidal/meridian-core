from meridian.synthetic import (
    generate_customers,
    generate_order_items,
    generate_orders,
    generate_payments,
    generate_products,
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
