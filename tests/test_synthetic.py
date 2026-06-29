from meridian.synthetic import generate_customers


def test_generate_customers_is_deterministic() -> None:
    a = generate_customers(10)
    b = generate_customers(10)
    assert a.equals(b)
    assert a.height == 10
    assert a["customer_id"][0] == "C000001"
