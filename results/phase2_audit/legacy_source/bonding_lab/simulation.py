"""Deterministic, matched-shock market simulations and replayable results."""
from dataclasses import asdict, dataclass, replace
import io
import json
import zipfile
import numpy as np
import pandas as pd

from .agents import agent_kinds, intention, make_tape
from .fast import FastBook

SCENARIOS = ("baseline", "popular", "crash", "bundled", "frontrun", "bank_run")


@dataclass(frozen=True)
class Config:
    tokens: int = 10
    coupling: float = .25
    initial_supply: float = 1000
    initial_supplies: tuple[float, ...] | None = None
    reserve_capital: float = 0
    p0: float = .01
    k: float = .0001
    traders: int = 100
    retail_fraction: float = .6
    whale_fraction: float = .1
    trader_cash: float = 1000
    trade_size: float = 20
    buy_pressure: float = .55
    volatility: float = .8
    events: int = 2000
    fee: float = .003
    seed: int = 42
    scenario: str = "baseline"
    sample_every: int = 10
    attack_capital: float = 500
    slippage_tolerance: float = .02
    competitors: int = 1

    def __post_init__(self):
        for name, val in asdict(self).items():
            if isinstance(val, (int, float)) and (not np.isfinite(val) or val < 0 or val > 1e18):
                raise ValueError(f"Invalid {name}")
        for name in ("tokens", "traders", "events", "sample_every", "competitors", "seed"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer")
        if not 1 <= self.tokens <= 10000 or not 1 <= self.traders <= 10000:
            raise ValueError("Token and trader counts must be between 1 and 10,000")
        if self.events < 1 or self.sample_every < 1 or self.competitors < 1:
            raise ValueError("Positive events, sampling interval and competitors required")
        if self.p0 < 1e-18 or self.fee >= 1 or self.coupling > 1 or self.buy_pressure > 1:
            raise ValueError("Invalid curve parameters or pressure")
        if self.retail_fraction+self.whale_fraction > 1 or self.volatility > 5:
            raise ValueError("Agent fractions must sum to <=1; volatility must be <=5")
        if self.scenario not in SCENARIOS:
            raise ValueError("Unknown scenario")
        if self.initial_supplies is not None:
            object.__setattr__(self, "initial_supplies", tuple(float(v) for v in self.initial_supplies))
            if len(self.initial_supplies) != self.tokens or not all(np.isfinite(v) and 0 <= v <= 1e18 for v in self.initial_supplies):
                raise ValueError("Supply vector must contain one nonnegative finite quantity per token")


@dataclass
class Result:
    config: Config
    history: pd.DataFrame
    prices: pd.DataFrame
    trades: pd.DataFrame
    wallets: pd.DataFrame
    metrics: dict

    def export_zip(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("config.json", json.dumps(asdict(self.config), indent=2))
            z.writestr("metrics.json", json.dumps(self.metrics, indent=2))
            for name in ("history", "prices", "trades", "wallets"):
                z.writestr(name+".csv", getattr(self, name).to_csv(index=False))
        return data.getvalue()


def initial_required(c):
    q = np.array(c.initial_supplies if c.initial_supplies is not None else [c.initial_supply]*c.tokens)
    return float(c.p0*q.sum()+c.k/2*((1-c.coupling)*np.square(q).sum()+c.coupling*q.sum()**2))


def equal_capital_supply(capital, c):
    b = c.p0*c.tokens
    a = c.k/2*c.tokens*(1+c.coupling*(c.tokens-1))
    return capital/b if a == 0 else 2*capital/(b+np.sqrt(b*b+4*a*capital))


def run(config, *, record=True, tape=None):
    c = config
    tape = tape or make_tape(c)
    kinds = agent_kinds(c.traders, c.retail_fraction, c.whale_fraction)
    # Additional attacker wallets are capitalized and included in conservation.
    attackers = c.competitors if c.scenario == "frontrun" and c.tokens > 1 else 0
    book = FastBook(c.tokens, c.traders, c.p0, c.k, c.coupling, c.fee,
                    c.trader_cash, c.initial_supplies if c.initial_supplies is not None else c.initial_supply, c.reserve_capital)
    if attackers:
        book.cash = np.concatenate([book.cash, np.full(attackers, c.attack_capital)])
        book.holdings = np.vstack([book.holdings, np.zeros((attackers, c.tokens))])
        book.basis = np.vstack([book.basis, np.zeros((attackers, c.tokens))])
        book.realized = np.concatenate([book.realized, np.zeros(attackers)])
        book.initial_wealth = np.concatenate([book.initial_wealth, np.full(attackers, c.attack_capital)])
        book.initial_external += attackers*c.attack_capital
    start_prices = book.prices().copy()
    start_q = book.q.copy()
    momentum = np.zeros(c.tokens)
    history, price_rows, fills = [], [], []
    net_flow = volume = impacts = slippages = 0.0
    trades_count = rejects = attack_count = successful_attacks = 0
    min_reserve = book.reserve
    max_shortfall = 0.0

    def snapshot(step):
        if not record:
            return
        prices = book.prices()
        caps = prices*book.q
        # These hypothetical per-token liquidation values each assume that token
        # exits first. Their sum is NOT collectively executable at lambda > 0.
        liq_first = (prices*book.q-c.k*book.q**2/2)*(1-c.fee)
        history.append(dict(event=step, reserve=book.reserve, required=book.reserve_function(),
                            buffer=book.buffer, quoted_market_cap=float(caps.sum()),
                            collective_liquidation=book.required*(1-c.fee),
                            sum_first_exit_quotes=float(liq_first.sum()), volume=volume,
                            net_external_flow=net_flow, fees=book.fees,
                            solvency_surplus=book.reserve-book.reserve_function(),
                            attacker_pnl=float(book.realized[c.traders:].sum()) if attackers else 0))
        for token in range(c.tokens):
            price_rows.append(dict(event=step, token=f"T{token}", price=prices[token],
                                   supply=book.q[token], market_cap=caps[token], liquidation_first=liq_first[token],
                                   own_price_change=c.k*(book.q[token]-start_q[token]),
                                   spillover_price_change=c.k*c.coupling*((book.Q-start_q.sum())-(book.q[token]-start_q[token]))))

    def fill(w, token, d, side, event, tag="market", max_payment=None):
        nonlocal net_flow, volume, trades_count, impacts, slippages, min_reserve, max_shortfall
        if d <= 1e-12:
            return None
        tx = book.execute(w, token, d, side, max_payment=max_payment)
        net_flow -= tx.cash_change
        volume += tx.gross
        trades_count += 1
        impact = abs(tx.post_price-tx.pre_price)/tx.pre_price
        slippage = abs(tx.gross/tx.quantity-tx.pre_price)/tx.pre_price
        impacts += impact
        slippages += slippage
        min_reserve = min(min_reserve, book.reserve)
        max_shortfall = max(max_shortfall, book.reserve_function()-book.reserve, 0)
        if record:
            fills.append(dict(event=event, wallet=w, kind=str(kinds[w]) if w < c.traders else "attacker",
                              token=f"T{token}", side=side, quantity=d, gross=tx.gross, fee=tx.fee,
                              cash_change=tx.cash_change, price_before=tx.pre_price, price_after=tx.post_price,
                              price_impact=impact, execution_slippage=slippage, tag=tag))
        return tx

    snapshot(0)
    for t in range(c.events):
        w = int(tape.wallets[t])
        token, side, budget = intention(c, tape, t, str(kinds[w]), momentum)
        previous_target = book.price(token)
        if side == "buy":
            budget = min(budget, book.cash[w]*.95)
            d = book.buy_quantity(token, budget)
        else:
            if c.scenario == "bank_run" and t > c.events//2:
                # Redeem the largest available position, so empty random choices
                # do not disguise a run. Complete liquidation is a separate test.
                token = int(np.argmax(book.holdings[w]))
                previous_target = book.price(token)
                d = book.holdings[w, token]
            else:
                d = min(book.holdings[w, token], budget/book.price(token))
        if d <= 1e-12:
            rejects += 1
            continue
        if attackers and side == "buy":
            attack_count += 1
            other = (token+1) % c.tokens
            quote = (book.price(token)*d+c.k*d*d/2)*(1+c.fee)
            pre_pnl = float(book.realized[c.traders:].sum())
            acquired = []
            for a in range(attackers):
                aw = c.traders+a
                ad = book.buy_quantity(other, min(budget, book.cash[aw]*.95))
                if ad > 1e-12:
                    fill(aw, other, ad, "buy", t+1, "front_run")
                    acquired.append((aw, ad))
            try:
                fill(w, token, d, "buy", t+1, "victim", quote*(1+c.slippage_tolerance))
            except ValueError:
                rejects += 1
            # Last-in-first-out competition models a specific assumed ordering.
            for aw, ad in reversed(acquired):
                fill(aw, other, ad, "sell", t+1, "back_run")
            successful_attacks += float(book.realized[c.traders:].sum()) > pre_pnl+1e-10
        else:
            fill(w, token, d, side, t+1)
        momentum *= .98
        momentum[token] += book.price(token)/previous_target-1
        if (t+1) % max(100, c.sample_every) == 0:
            book.assert_invariants()
        if (t+1) % c.sample_every == 0:
            snapshot(t+1)
    if not history or history[-1]["event"] != c.events:
        snapshot(c.events)
    tolerance = book.assert_invariants()
    # A wallet-specific liquidation quote is executable if it exits first. The
    # aggregate is deliberately not reported as a realized group liquidation.
    prices = book.prices()
    own_liq = (book.holdings@prices-c.k/2*((1-c.coupling)*np.square(book.holdings).sum(axis=1)
                   +c.coupling*np.square(book.holdings.sum(axis=1))))*(1-c.fee)
    wealth_mark = book.cash+book.holdings@prices
    wallets = pd.DataFrame(dict(wallet=np.arange(len(book.cash)),
                                 kind=list(kinds)+["attacker"]*attackers,
                                 cash=book.cash, tokens_held=book.holdings.sum(axis=1),
                                 remaining_cost_basis=book.basis.sum(axis=1), realized_pnl=book.realized,
                                 quoted_wealth=wealth_mark, marked_pnl=wealth_mark-book.initial_wealth,
                                 first_exit_liquidation=own_liq,
                                 first_exit_pnl=book.cash+own_liq-book.initial_wealth,
                                 token_balances=[json.dumps({f"T{i}":float(q) for i,q in enumerate(row) if q>1e-12}) for row in book.holdings])) if record else pd.DataFrame()
    metrics = dict(seed=c.seed, events=c.events, executed_trades=trades_count, skipped_or_rejected=rejects,
                   initial_required=initial_required(c), initial_external=book.initial_external,
                   final_reserve=book.reserve, final_required=book.required, min_reserve=min_reserve,
                   reserve_shortfall_raw=max_shortfall, material_reserve_shortfall=max(0, max_shortfall-tolerance),
                   float_tolerance=tolerance, volume=volume, net_external_flow=net_flow,
                   fee_treasury=book.fees, mean_price_impact=impacts/max(1,trades_count),
                   mean_slippage=slippages/max(1,trades_count),
                   gross_volume_per_initial_backing=volume/max(initial_required(c),1e-12),
                   final_fixed_100_buy_cost=float(prices[0]*100+c.k*100**2/2),
                   fixed_100_absolute_price_impact=c.k*100,
                   final_quoted_market_cap=float(np.dot(prices, book.q)),
                   collective_liquidation=book.required*(1-c.fee),
                   trader_realized_pnl=float(book.realized[:c.traders].sum()),
                   trader_marked_pnl=float((wealth_mark-book.initial_wealth)[:c.traders].sum()),
                   attacker_profit=float(book.realized[c.traders:].sum()) if attackers else 0.,
                   attack_opportunities=attack_count, successful_attacks=successful_attacks,
                   attack_success_frequency=successful_attacks/max(1, attack_count),
                   bundled_group_realized_pnl=float(book.realized[:c.traders][np.isin(kinds,["creator","bundler","adversary"])].sum()),
                   t0_price_change=float(prices[0]-start_prices[0]),
                   t0_own_price_change=float(c.k*(book.q[0]-start_q[0])),
                   t0_spillover_price_change=float(c.k*c.coupling*((book.Q-start_q.sum())-(book.q[0]-start_q[0]))),
                   other_mean_price_change=float(np.mean(prices[1:]-start_prices[1:])) if c.tokens > 1 else 0.)
    return Result(c, pd.DataFrame(history), pd.DataFrame(price_rows), pd.DataFrame(fills), wallets, metrics)


def compare(config, basis="equal_supplies", *, record=True):
    if basis not in ("equal_supplies", "equal_capital"):
        raise ValueError("Unknown comparison basis")
    shared = config
    independent = replace(config, coupling=0)
    if basis == "equal_capital":
        # Match required backing, and keep any donation buffer equal in both.
        initial_capital = initial_required(config)
        if config.initial_supplies is None:
            independent = replace(independent, initial_supply=equal_capital_supply(initial_capital, independent))
        else:
            shape = np.array(config.initial_supplies)
            b = config.p0*shape.sum()
            a = config.k/2*np.square(shape).sum()
            scale = 1 if initial_capital == 0 else (initial_capital/b if a == 0 else 2*initial_capital/(b+np.sqrt(b*b+4*a*initial_capital)))
            independent = replace(independent, initial_supplies=tuple(shape*scale))
    tape = make_tape(config)
    return {"shared": run(shared, record=record, tape=tape),
            "independent": run(independent, record=record, tape=tape)}
