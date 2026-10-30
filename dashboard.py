"""Streamlit research laboratory. Run: python -m streamlit run dashboard.py."""
from dataclasses import asdict
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from bonding_lab.attacks import frontrun
from bonding_lab.experiments import attack_grid, bank_run_orders, bundle_grid, controlled_spillover, growth, scaling
from bonding_lab.simulation import Config, SCENARIOS, compare, initial_required, run

st.set_page_config(page_title="Shared Bonding Lab", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container {padding-top:4rem; max-width:1600px}
h1 {letter-spacing:-.055em; font-weight:750!important}
[data-testid="stMetric"] {background:#141f33;border:1px solid #26354c;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"] {color:#9eacc2}
.lab-eyebrow {color:#4edbc0;font-size:12px;letter-spacing:.18em;font-weight:700}
.lab-subtitle {color:#9eacc2;font-size:17px;max-width:900px;margin-bottom:22px}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="lab-eyebrow">MECHANISM RESEARCH / QUADRATIC SURFACE</div>',unsafe_allow_html=True)
st.title("Shared Bonding Lab")
st.markdown('<div class="lab-subtitle">Explore the boundary between shared pricing, executable liquidity, and financial contagion.</div>',unsafe_allow_html=True)
st.caption("SYNTHETIC RESEARCH · Fixed parameters per run · Fully funded issuance · No real transactions")


def chart(fig, key=None):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Arial",color="#c6d3e5"), margin=dict(l=10,r=10,t=40,b=10),
                      legend=dict(orientation="h", y=-.2), hovermode="x unified")
    st.plotly_chart(fig, width="stretch", key=key)


with st.sidebar:
    st.subheader("Market design")
    tokens = st.select_slider("Number of tokens", [2,5,10,25,100,1000], value=10)
    coupling = st.slider("Coupling λ",0.,1.,.25,.05)
    q0 = st.number_input("Starting supply per token", min_value=0.,value=1000.,step=100.)
    custom_q = st.text_input("Optional per-token supplies (CSV)",help="One nonnegative quantity per token; overrides the uniform supply.")
    capital = st.number_input("Starting reserve USDC (0 = exact backing)",min_value=0.,value=0.,step=1000.)
    with st.expander("Curve & fees",expanded=False):
        p0 = st.number_input("Minimum price p₀",min_value=.00000001,value=.01,format="%.8f")
        k = st.number_input("Sensitivity k",min_value=0.,value=.0001,format="%.8f")
        fee = st.slider("Transaction fee (%)",0.,5.,.3,.1)/100
    st.subheader("Synthetic demand")
    traders = st.number_input("Traders",min_value=10,max_value=1000,value=100,step=10)
    retail = st.slider("Retail share",0.,1.,.6,.05)
    whale = st.slider("Whale share",0.,1.,.1,.05,help="Retail and whale fractions must sum to at most 1.")
    cash = st.number_input("Trading cash per trader (USDC)",min_value=0.,value=1000.,step=100.)
    size = st.number_input("Typical trade notional (USDC)",min_value=.01,value=20.,step=5.)
    pressure = st.slider("Buy pressure",0.,1.,.55,.05)
    volatility = st.slider("Trade-size log volatility",0.,2.,.8,.1)
    events = st.number_input("Duration (demand events)",min_value=10,max_value=20000,value=2000,step=100)
    seed = st.number_input("Random seed",min_value=0,value=42,step=1)
    scenario = st.selectbox("Scenario",SCENARIOS)
    with st.expander("Pending-order attack assumptions"):
        attack_capital = st.number_input("USDC per attacker",min_value=0.,value=500.,step=100.)
        slippage = st.slider("Victim payment tolerance (%)",0.,100.,2.,1.)/100
        competitors = st.slider("Competing attackers",1,10,1)
    st.caption("Remaining agents cycle through momentum, holders, creators, snipers, bundlers, coupling followers and adversaries. Policies are assumptions.")

try:
    config = Config(tokens=tokens,coupling=coupling,initial_supply=q0,
                    initial_supplies=tuple(float(x.strip()) for x in custom_q.split(",")) if custom_q else None,
                    reserve_capital=capital,p0=p0,k=k,traders=int(traders),retail_fraction=retail,
                    whale_fraction=whale,trader_cash=cash,trade_size=size,buy_pressure=pressure,
                    volatility=volatility,events=int(events),fee=fee,seed=int(seed),scenario=scenario,
                    sample_every=max(1,int(events)//200),attack_capital=attack_capital,
                    slippage_tolerance=slippage,competitors=competitors)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

columns = st.columns([1,1.8,1,1])
run_clicked = columns[0].button("Run simulation",type="primary",width="stretch")
compare_clicked = columns[1].button("Independent vs shared",width="stretch")
stress_clicked = columns[2].button("Run stress tests",width="stretch")
reset_clicked = columns[3].button("Reset results",width="stretch")
basis = st.radio("Comparison basis",["equal_supplies","equal_capital"],format_func=lambda x:x.replace("_"," ").title(),horizontal=True)
st.caption(f"Configured genesis backing: ${initial_required(config):,.2f}. Trading cash is additional. Extra reserve capital is a donation buffer.")
if reset_clicked:
    for name in ("result","comparison","stress","replay_event","playing"):
        st.session_state.pop(name,None)
    st.rerun()
try:
    if run_clicked:
        with st.spinner("Executing deterministic market and checking accounting…"):
            st.session_state.result = run(config)
            st.session_state.replay_event = config.events
            st.session_state.playing = False
            st.session_state.pop("selected_tokens",None)
    if compare_clicked:
        with st.spinner("Matching random demand across both fixed-parameter markets…"):
            st.session_state.comparison = compare(config,basis)
    if stress_clicked:
        with st.spinner("Running exact attacks, full redemptions and scaling analyses…"):
            st.session_state.stress = dict(attacks=attack_grid(),bank_runs=bank_run_orders(10),
                                           scaling=scaling(),growth=growth(),bundles=bundle_grid(),
                                           spillover=controlled_spillover())
except (ValueError, AssertionError) as exc:
    st.error(f"Run failed; results were not replaced. {exc}")

market_tab, compare_tab, stress_tab, math_tab = st.tabs(["Market laboratory","Matched comparison","Stress & adversaries","Model & interpretation"])


@st.fragment(run_every=1 if st.session_state.get("playing",False) else None)
def replay(result):
    c = result.config
    st.subheader("Transaction replay")
    st.caption(f"Saved run: seed {c.seed} · {c.tokens} tokens · λ={c.coupling:.2f} · {c.scenario}. Replay shows completed demand events; event logs retain every fill.")
    cols = st.columns([1,1,1,5])
    if cols[0].button("Play", key="play"):
        st.session_state.playing = True
        if st.session_state.replay_event >= c.events:
            st.session_state.replay_event = 0
        st.rerun()
    if cols[1].button("Pause", key="pause"):
        st.session_state.playing = False
        st.rerun()
    if cols[2].button("Step", key="step"):
        st.session_state.playing = False
        st.session_state.replay_event = min(c.events,st.session_state.replay_event+1)
        st.rerun()
    if st.session_state.get("playing",False):
        st.session_state.replay_event = min(c.events,st.session_state.replay_event+max(1,c.events//100))
        if st.session_state.replay_event == c.events:
            st.session_state.playing = False
            st.rerun()
    cursor = cols[3].slider("Demand event",0,c.events,key="replay_event")
    st.caption("Charts show sampled states up to the cursor. The transaction table below supports exact one-event stepping. Wallet statistics report the completed run.")
    h = result.history[result.history.event<=cursor]
    p = result.prices[result.prices.event<=cursor]
    latest = h.iloc[-1]
    a,b,d,e = st.columns(4)
    a.metric("Locked reserve",f"${latest.reserve:,.2f}")
    b.metric("Quoted total cap",f"${latest.quoted_market_cap:,.2f}")
    d.metric("Collective net redemption",f"${latest.collective_liquidation:,.2f}")
    e.metric("Surplus incl. buffer",f"${latest.solvency_surplus:,.6f}")
    selected = st.multiselect("Tokens to inspect",list(result.prices.token.unique()),default=list(result.prices.token.unique())[:min(c.tokens,10)],key="selected_tokens")
    selected_p = p[p.token.isin(selected)]
    chart(px.line(selected_p,x="event",y="price",color="token",title="Marginal prices · USDC per token"),"prices")
    left,right = st.columns(2)
    with left:
        chart(px.line(h,x="event",y=["reserve","required","buffer"],title="Backing, actual reserve and donated buffer"),"reserve")
        chart(px.line(h,x="event",y=["volume","net_external_flow","fees"],title="Gross volume, net trader cash flow and fees"),"flows")
        chart(px.line(selected_p,x="event",y="market_cap",color="token",title="Individual quoted market caps"),"caps")
    with right:
        chart(px.line(h,x="event",y=["quoted_market_cap","collective_liquidation","sum_first_exit_quotes"],title="Paper cap vs executable collective redemption"),"liquidation")
        chart(px.line(selected_p,x="event",y=["own_price_change","spillover_price_change"],facet_col="token",facet_col_wrap=3,title="Own issuance and cross-token price attribution"),"attribution")
        chart(px.line(h,x="event",y=["solvency_surplus","attacker_pnl"],title="Reserve surplus and realized attacker P&L"),"solvency")
    st.info("Collective redemption equals the reserve function after sell fees. Each first-exit quote assumes it redeems before other holders; their sum cannot be paid simultaneously. A solvent run can still redistribute value unfairly.")
    trades = result.trades[result.trades.event<=cursor] if not result.trades.empty else result.trades
    if not trades.empty:
        left,right = st.columns(2)
        with left:
            chart(px.scatter(trades,x="event",y="execution_slippage",color="side",title="Gross execution slippage versus pre-trade quote",opacity=.45),"slippage")
        with right:
            chart(px.scatter(trades,x="event",y="price_impact",color="side",title="Marginal price impact per fill",opacity=.45),"impact")
        st.dataframe(trades.tail(25),width="stretch",hide_index=True)
    st.subheader("Completed-run wallet accounting")
    chart(px.bar(result.wallets.groupby("kind",as_index=False)[["realized_pnl","marked_pnl"]].sum(),x="kind",y=["realized_pnl","marked_pnl"],barmode="group",title="Group P&L · realized cash and marked inventory"),"wallet_pnl")
    st.caption("Individual wallet first-exit values appear in the table. They assume that wallet exits first and cannot be added into executable group proceeds.")
    st.dataframe(result.wallets,width="stretch",hide_index=True)
    with st.expander("Completed-run metrics and fixed configuration"):
        st.json(result.metrics)
        st.json(asdict(c))
    st.download_button("Export run (CSV + JSON ZIP)",result.export_zip(),file_name=f"bonding_seed_{c.seed}.zip",mime="application/zip")


with market_tab:
    if "result" in st.session_state:
        result = st.session_state.result
        if asdict(config) != asdict(result.config):
            st.warning("Controls differ from the saved run. Run again to apply them; saved parameters remain fixed.")
        replay(result)
    else:
        st.info("Configure a market and select Run simulation. All charts will come from that executed run.")
        st.markdown("""**Research questions**

- Does the same quantity trade with less absolute price impact?
- Who funds cross-token appreciation, and who captures the exit proceeds?
- Does tighter ordering protection remove profitable cross-token attacks?
- How does a fully backed run distribute losses during mass redemption?""")

with compare_tab:
    if "comparison" not in st.session_state:
        st.info("Select Independent vs shared to execute a matched pair using the chosen basis.")
    else:
        pair = st.session_state.comparison
        st.caption("Same underlying random tape. Fills, cash constraints and momentum may diverge. Independent curves use λ=0 within this quadratic model.")
        st.dataframe(pd.DataFrame({name:r.metrics for name,r in pair.items()}).T,width="stretch")
        histories = pd.concat([r.history.assign(model=name) for name,r in pair.items()])
        chart(px.line(histories,x="event",y="collective_liquidation",color="model",title="Executable collective redemption"))
        chart(px.line(histories,x="event",y="quoted_market_cap",color="model",title="Aggregate quoted market cap"))
        data = io.BytesIO()
        with zipfile.ZipFile(data,"w",zipfile.ZIP_DEFLATED) as z:
            for name,r in pair.items():
                z.writestr(name+".zip",r.export_zip())
        st.download_button("Export matched pair",data.getvalue(),file_name="matched_pair.zip",mime="application/zip")

with stress_tab:
    st.subheader("Pending-order attack workbench")
    st.caption("Exact Decimal execution. The victim quantity is fixed; fee and payment-cap constraints apply. Network expense is an external modeled cost.")
    cols = st.columns(4)
    da = cols[0].number_input("Victim quantity A",min_value=1,value=1000)
    db = cols[1].number_input("Attacker quantity B",min_value=1,value=500)
    order = cols[2].selectbox("Ordering",["lifo","fifo","victim_first"])
    gas = cols[3].number_input("Network cost per attacker tx",min_value=0.,value=0.,step=.01)
    if st.button("Execute exact attack"):
        try:
            attack = frontrun(coupling=str(coupling),fee=str(round(fee,8)),amount_a=str(da),amount_b=str(db),
                              initial_supply=str(q0),capital=str(attack_capital),slippage=str(round(slippage,8)),
                              competitors=competitors,ordering=order,gas_per_tx=str(gas),p0=str(p0),k=str(k))
            st.json(attack)
        except ValueError as exc:
            st.error(str(exc))
    if "stress" in st.session_state:
        stress = st.session_state.stress
        st.caption("Stress tables below use labeled standard research defaults (10 tokens, q=1000, p₀=.01, k=.0001 where relevant); they sweep coupling and fees independently of the sidebar.")
        for name,table in stress.items():
            with st.expander(name.replace("_"," ").title(),expanded=name=="attacks"):
                st.dataframe(table,width="stretch",hide_index=True)
                st.download_button("Export "+name,table.to_csv(index=False),file_name=name+".csv",mime="text/csv",key="export_"+name)
        chart(px.line(stress["scaling"],x="tokens",y="new_token_starting_price",color="coupling",log_x=True,title="Price of a newly created zero-supply token"))
        chart(px.box(stress["bank_runs"],x="exit_position",y="proceeds",color="coupling",title="Exact full bank run · proceeds by exit position"))
    else:
        st.info("Run stress tests to produce exact bank runs, bundle sequences, attack sweeps, scaling and 2×/10×/100× growth tables.")

with math_tab:
    st.latex(r"R(q)=p_0 Q+\frac{k}{2}\left[(1-\lambda)\sum_i q_i^2+\lambda Q^2\right]")
    st.latex(r"p_i=p_0+k(q_i+\lambda\sum_{j\ne i}q_j),\quad C_i(d)=p_i d+\frac{k d^2}{2}")
    st.markdown("""**What this model proves:** self-price slope is k; cross-price slope is kλ. Valid funded trades preserve backing. Closed trade paths have zero gross aggregate cost. Full redemption pays the required reserve, with order-dependent distributions among holders.

**What simulations assume:** synthetic agent policies, comparable token units, fixed parameters, exact reserve execution, a constant fee and a specified transaction order. No external exchange, real mempool, organic demand calibration, or six-decimal settlement is modeled.

**What to compare:** match supplies to study the same issued quantity; match initial backing to study the same seed capital. Compare fixed-quantity depth as well as relative slippage. Lower percentage slippage at higher prices need not mean better executable liquidity.

**Accounting labels:** reserve is actual backing plus a donated buffer; quoted cap is price × supply; collective liquidation is the gross reserve potential less sell fees. Wallet marked values and first-exit quotes are hypothetical.

**Scale up:** use `python -m bonding_lab.cli research --seeds 1000 --events 10000 --out results/large` for seed-level distributions, paired differences and uncertainty intervals.""")
    st.latex(r"M=2R-p_0Q,\qquad \Pi_{\mathrm{gross}}=k\lambda a b")
    for name in ("MATHEMATICS.md","RESEARCH_FINDINGS.md"):
        path = Path(__file__).parent/name
        if path.exists():
            st.download_button("Download "+name,path.read_text(encoding="utf-8"),file_name=name,mime="text/markdown")
