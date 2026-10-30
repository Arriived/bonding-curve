"""Exact pending-order attacks with explicit cash, fee and ordering constraints."""
from decimal import Decimal
from .engine import Curve, Parameters, RejectedTrade, decimal, precise


@precise
def frontrun(*, coupling="0.25", fee="0", amount_a="1000", amount_b="500",
             initial_supply="1000", capital="10000", slippage="1", competitors=1,
             ordering="lifo", gas_per_tx="0", p0="0.01", k="0.0001"):
    if type(competitors) is not int or not 1 <= competitors <= 100:
        raise ValueError("Competitors must be between 1 and 100")
    if ordering not in ("lifo", "fifo", "victim_first"):
        raise ValueError("Unknown ordering")
    c = Curve(Parameters(p0=p0, k=k, coupling=coupling, fee_rate=fee))
    c.create_token("A")
    c.create_token("B")
    c.create_wallet("seed", "1e18")
    q = decimal(initial_supply)
    for i in range(2):
        if q:
            c.execute("seed", i, q, "buy")
    c.create_wallet("victim", "1e18")
    c.create_wallet("network", 0)
    for a in range(competitors):
        c.create_wallet(f"attacker{a}", capital)
    da, db = decimal(amount_a), decimal(amount_b)
    base_gross, base_fee = c.quote(0, da, "buy")
    limit = (base_gross+base_fee)*(1+decimal(slippage))
    # Slippage thresholds are ledger decimals, rather than input quantities.
    # Round down at 18 places; exact formula tests use integer/fixed inputs.
    limit = limit.quantize(Decimal("1e-18"))
    logs = []
    victim_filled = False
    acquired = []

    def victim():
        nonlocal victim_filled
        try:
            tx = c.execute("victim", 0, da, "buy", max_payment=limit)
            victim_filled = True
            logs.append({"actor": "victim", "side": "buy", "gross": float(tx.gross)})
        except RejectedTrade as exc:
            logs.append({"actor": "victim", "side": "rejected", "reason": str(exc)})

    if ordering == "victim_first":
        victim()
    for a in range(competitors):
        name = f"attacker{a}"
        try:
            cost, cost_fee = c.quote(1, db, "buy")
            if cost+cost_fee+2*decimal(gas_per_tx) > c.wallets[name].cash:
                raise RejectedTrade("Insufficient capital for purchase and both network charges")
            tx = c.execute(name, 1, db, "buy")
            acquired.append(name)
            logs.append({"actor": name, "side": "buy", "gross": float(tx.gross)})
        except RejectedTrade as exc:
            logs.append({"actor": name, "side": "rejected", "reason": str(exc)})
    if ordering != "victim_first":
        victim()
    exit_order = list(reversed(acquired)) if ordering == "lifo" else acquired
    for name in exit_order:
        tx = c.execute(name, 1, db, "sell")
        logs.append({"actor": name, "side": "sell", "gross": float(tx.gross)})
    profits = [c.wallets[f"attacker{a}"].cash-decimal(capital) for a in range(competitors)]
    network_costs = [2*decimal(gas_per_tx) if f"attacker{a}" in acquired else Decimal(0) for a in range(competitors)]
    for a, expense in enumerate(network_costs):
        if expense:
            c.transfer_cash(f"attacker{a}", "network", expense)
    c.assert_invariants()
    expected = c.params.k*c.params.coupling*da*db
    return dict(coupling=float(c.params.coupling), fee=float(c.params.fee_rate),
                victim_filled=victim_filled, attackers_funded=len(acquired), competitors=competitors,
                ordering=ordering, gross_formula=float(expected),
                ledger_profit=float(sum(profits)), network_cost=float(sum(network_costs)),
                net_profit=float(sum(profits)-sum(network_costs)),
                individual_profits=[float(p-g) for p, g in zip(profits, network_costs)],
                reserve_shortfall=float(max(Decimal(0), c.required_reserve-c.reserve)),
                logs=logs)


@precise
def bundle(sequence=(0, 0, 0, 0), exit_order="reverse", coupling="0.25", fee="0", victim_quantity=1000):
    """Four separately funded wallets coordinate; no privileged creator minting."""
    c = Curve(Parameters(coupling=coupling, fee_rate=fee))
    c.create_token("A")
    c.create_token("B")
    c.create_wallet("victim", "1e9")
    total_cost = Decimal(0)
    for j, token in enumerate(sequence):
        c.create_wallet(str(j), "1e6")
        tx = c.execute(str(j), int(token), 250, "buy")
        total_cost += -tx.cash_change
    if victim_quantity:
        c.execute("victim", 0, victim_quantity, "buy")
    order = list(range(len(sequence)))
    if exit_order == "reverse":
        order.reverse()
    elif exit_order != "forward":
        raise ValueError("Unknown exit order")
    for j in order:
        c.execute(str(j), int(sequence[j]), 250, "sell")
    c.assert_invariants()
    profits = [c.wallets[str(j)].cash-Decimal("1e6") for j in range(len(sequence))]
    return dict(coupling=float(c.params.coupling), fee=float(c.params.fee_rate),
                sequence="".join(str(i) for i in sequence), exit_order=exit_order,
                victim_quantity=victim_quantity, acquisition_cost=float(total_cost),
                profit=float(sum(profits)), min_wallet_profit=float(min(profits)),
                max_wallet_profit=float(max(profits)), reserve_shortfall=0.)
