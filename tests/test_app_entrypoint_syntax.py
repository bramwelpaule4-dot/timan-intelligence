"""Static checks for the Streamlit application entrypoint."""

from pathlib import Path


def test_streamlit_entrypoint_compiles() -> None:
    """Catch syntax errors in app.py without importing Streamlit UI state."""
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")
    compile(source, str(app_path), "exec")
