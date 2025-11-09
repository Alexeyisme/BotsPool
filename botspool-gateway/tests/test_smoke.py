from src.main import app


def test_app_instance_exists() -> None:
    assert app.title
