from decimal import Decimal

from app.solar.consumption import panels_from_bill, seed_panels


def test_panels_from_bill_medium():
    est = panels_from_bill(Decimal("350"))
    assert est is not None
    assert est.panels == 7
    assert est.kwp.quantize(Decimal("0.01")) == Decimal("3.64")


def test_panels_from_bill_large():
    est = panels_from_bill(Decimal("1200"))
    assert est is not None
    assert est.kwp.quantize(Decimal("0.01")) >= Decimal("10")


def test_panels_from_bill_none_or_zero():
    assert panels_from_bill(None) is None
    assert panels_from_bill(Decimal("0")) is None


def test_seed_panels_is_deterministic_and_in_range():
    a = seed_panels(Decimal("-5.79"), Decimal("-35.21"))
    b = seed_panels(Decimal("-5.79"), Decimal("-35.21"))
    assert a == b
    assert 6 <= a <= 12
