"""Unrounded high-precision reference, reusing the original funded ledger."""
from bonding_lab.engine import Curve, Parameters


def reference_book(n=10, fee="0"):
    book=Curve(Parameters(p0=".01",k=".0001",coupling="0",fee_rate=fee))
    for i in range(n):book.create_token(f"N{i}")
    return book
