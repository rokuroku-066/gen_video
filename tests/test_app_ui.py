"""Basic sanity tests for the Streamlit UI."""

from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


class _DummySessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:  # pragma: no cover - mirrors streamlit behavior
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


class _DummyContainer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _stub_streamlit_module() -> types.ModuleType:
    """Create a lightweight stub of the Streamlit API for import-time execution."""
    st = types.ModuleType("streamlit")
    st.session_state = _DummySessionState()

    def _noop(*args, **kwargs):
        return None

    st.set_page_config = _noop
    st.title = _noop
    st.markdown = _noop
    st.subheader = _noop
    st.image = _noop
    st.video = _noop
    st.download_button = _noop
    st.warning = _noop
    st.info = _noop
    st.error = _noop
    st.success = _noop
    st.experimental_rerun = _noop

    def text_input(label, value: str = "", **kwargs):
        return value

    def text_area(label, value: str = "", **kwargs):
        return value

    st.text_input = text_input
    st.text_area = text_area
    st.selectbox = lambda label, options, index=0, **kwargs: list(options)[index]

    def checkbox(label, value: bool = False, **kwargs):
        return value

    st.checkbox = checkbox

    def button(label, **kwargs):
        return False

    st.button = button

    def file_uploader(*args, **kwargs):
        return None

    st.file_uploader = file_uploader

    def columns(spec: Iterable[int] | int):
        n = spec if isinstance(spec, int) else len(list(spec))
        return [_DummyContainer() for _ in range(n)]

    st.columns = columns
    st.container = lambda **kwargs: _DummyContainer()
    st.spinner = lambda *args, **kwargs: _DummyContainer()

    return st


def test_app_boots_in_fake_mode(monkeypatch):
    """Ensure the Streamlit script runs against a stubbed API."""
    monkeypatch.setenv("USE_FAKE_GENAI", "1")
    monkeypatch.delenv("ENABLE_REAL_GENAI", raising=False)

    # Stub streamlit so the UI code can run without a real Streamlit runtime.
    monkeypatch.setitem(sys.modules, "streamlit", _stub_streamlit_module())
    sys.modules.pop("app", None)

    app_path = ROOT / "app.py"
    runpy.run_path(str(app_path), run_name="__main__")

    st_stub = sys.modules["streamlit"]
    assert "frames" in st_stub.session_state
    assert len(st_stub.session_state["frames"]) >= 2
