from pathlib import Path
from streamlit.testing.v1 import AppTest


APP = str(Path(__file__).parents[1]/"dashboard.py")


def test_dashboard_run_compare_replay_reset():
    app = AppTest.from_file(APP,default_timeout=60).run()
    assert not app.exception
    next(n for n in app.number_input if n.label=="Duration (demand events)").set_value(100)
    next(b for b in app.button if b.label=="Run simulation").click().run()
    assert not app.exception
    assert app.session_state["result"].metrics["events"] == 100
    next(n for n in app.slider if n.label=="Demand event").set_value(0).run()
    next(b for b in app.button if b.label=="Play").click().run()
    assert not app.exception
    assert app.session_state["playing"]
    next(b for b in app.button if b.label=="Pause").click().run()
    assert not app.exception
    assert not app.session_state["playing"]
    previous_event = app.session_state["replay_event"]
    next(b for b in app.button if b.label=="Step").click().run()
    assert not app.exception
    assert app.session_state["replay_event"] == previous_event+1
    next(b for b in app.button if b.label=="Independent vs shared").click().run()
    assert not app.exception
    assert "independent" in app.session_state["comparison"]
    next(b for b in app.button if b.label=="Reset results").click().run()
    assert not app.exception
    assert "result" not in app.session_state


def test_dashboard_stress_and_exact_attack():
    app = AppTest.from_file(APP,default_timeout=60).run()
    next(b for b in app.button if b.label=="Run stress tests").click().run()
    assert not app.exception
    assert len(app.session_state["stress"]["attacks"]) == 108
    next(b for b in app.button if b.label=="Execute exact attack").click().run()
    assert not app.exception
