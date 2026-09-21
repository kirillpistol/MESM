from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_control_room_renders_without_exception():
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=30)
    app.run()

    assert not app.exception
    assert any("MESM" in title.value for title in app.title)
    assert any("экономический срез" in item.value for item in app.subheader)
    assert app.sidebar.radio
    assert app.sidebar.selectbox


def test_sources_monitor_page_renders_without_exception():
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=30)
    app.run()
    app.sidebar.radio[0].set_value("Источники")
    app.run()

    assert not app.exception
    assert any("Источники и pipeline" in item.value for item in app.subheader)


def test_model_tournament_page_renders_without_exception():
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=30)
    app.run()
    app.sidebar.radio[0].set_value("Модели")
    app.run()

    assert not app.exception
    assert any("Модельный турнир" in item.value for item in app.subheader)


def test_shock_monitor_page_renders_without_exception():
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=30)
    app.run()
    app.sidebar.radio[0].set_value("Монитор шоков")
    app.run()

    assert not app.exception
    assert any("Монитор шоков" in item.value for item in app.subheader)
