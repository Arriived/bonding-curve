"""First-buy quote: the program's buy path, in exact integer arithmetic.

Ports, line for line:
  - programs/doors_v1/src/math.rs: `reserve`, `inverse`, `ratio`, `buy_amounts`;
  - trading.rs `settle_pending` (a buy first retires the pending backlog, capped at the trigger) and
    `execute_trade`'s buy branch (capped net input, then `advance`).

The service uses it to default `Launch.min_tokens_out` for a first buy: the quote at the decision's
snapshot, less `max_slippage_bps`. The program enforces that minimum at execution, so a price that
moved further than the tolerance between decision and landing fails the launch atomically instead of
filling at any price (SECURITY_REVIEW.md M-4).
"""
U = 1_000_000_000_000_000  # math.rs U: one billion tokens in base units

DEFAULT_MAX_SLIPPAGE_BPS = 200     # DESIGN.md §3: "the frontend default should be <= 2-3% slippage"
MAX_SLIPPAGE_BPS = 5_000


def reserve(vs, vt, q):
    if not (q <= U and vt > q):
        raise ValueError("quote outside the curve")
    return vs * q // (vt - q)


def inverse(vs, vt, r):
    q = vt - (vs * vt) // (r + vs + 1) - 1
    if not 0 <= q <= U:
        raise ValueError("quote outside the curve")
    return q


def ratio(n, bps, ceil):
    return (n * bps + (9999 if ceil else 0)) // 10000


def buy_amounts(gross, bps, available):
    net = gross * 10000 // (10000 + bps)
    if net > available:
        return available, ratio(available, bps, True)
    return net, gross - net


def first_buy_tokens(curve, gross):
    """Tokens a buy of `gross` lamports (fee included) receives against `curve`, or None if the program
    would reject it (status != 0, cap reached by settlement, zero tokens).

    `curve` holds v_sol_lamports, v_tok, supply, graduation_trigger_lamports, fee_bps, reserve, sold,
    pending_reserve_sol and status, as decoded from a Room (or a new room's Config snapshot)."""
    vs, vt, trigger = curve["v_sol_lamports"], curve["v_tok"], curve["graduation_trigger_lamports"]
    if curve["status"] != 0 or gross <= 0:
        return None
    sold, res = curve["sold"], curve["reserve"]
    settle = min(curve["pending_reserve_sol"], trigger - res)
    if settle > 0:                                   # settle_pending
        sold = inverse(vs, vt, reserve(vs, vt, sold) + settle)
        res += settle
        if res == trigger:
            return None                              # PhaseTwo: the buy would be rejected
    n, _ = buy_amounts(gross, curve["fee_bps"], trigger - res)
    if n == 0:
        return None
    q = inverse(vs, vt, reserve(vs, vt, sold) + n)
    tokens = q - sold
    if tokens <= 0 or tokens > curve["supply"] - sold:
        return None
    return tokens


def new_room_curve(config):
    return {"v_sol_lamports": config["v_sol_lamports"], "v_tok": config["v_tok"], "supply": config["supply"],
            "graduation_trigger_lamports": config["graduation_trigger_lamports"], "fee_bps": config["fee_bps"],
            "reserve": 0, "sold": 0, "pending_reserve_sol": 0, "status": 0}


def min_out(tokens, slippage_bps):
    return max(1, tokens * (10000 - slippage_bps) // 10000)
