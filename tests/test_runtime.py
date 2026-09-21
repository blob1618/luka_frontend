from types import SimpleNamespace

from app.models.database import _normalize_database_url
from app.runtime import configure_worker_env, get_database_url, get_setting


def teardown_function():
    configure_worker_env(None)


def test_worker_bindings_are_available_after_request_configuration():
    worker_env = SimpleNamespace(
        APP_ENV="production",
        HYPERDRIVE=SimpleNamespace(connectionString="postgresql://worker/database"),
    )

    configure_worker_env(worker_env)

    assert get_setting("APP_ENV") == "production"
    assert get_database_url() == "postgresql://worker/database"


def test_cloudflare_database_url_uses_pure_python_driver():
    assert (
        _normalize_database_url(
            "postgresql://worker/database", postgres_driver="pg8000"
        )
        == "postgresql+pg8000://worker/database"
    )
