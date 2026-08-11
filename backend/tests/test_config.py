from sqlalchemy.engine import make_url

from app.core.config import Settings


def test_database_url_escapes_reserved_password_characters() -> None:
    password = "a@b:c/d#e"
    settings = Settings(
        POSTGRES_USER="barber",
        POSTGRES_PASSWORD=password,
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_DB="barber_db",
    )

    async_url = make_url(settings.DATABASE_URL)
    sync_url = make_url(settings.DATABASE_URL_SYNC)

    assert async_url.password == password
    assert sync_url.password == password
    assert async_url.database == "barber_db"


def test_test_database_is_separate_from_development_database() -> None:
    settings = Settings(POSTGRES_DB="barber_db", TEST_POSTGRES_DB="barber_test_db")
    assert make_url(settings.TEST_DATABASE_URL).database == "barber_test_db"
    assert settings.TEST_POSTGRES_DB != settings.POSTGRES_DB
