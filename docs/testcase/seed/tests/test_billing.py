from billing import price_after_discount


def test_discount():
    assert price_after_discount(100, 0.25) == 75
