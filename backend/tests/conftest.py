"""Shared fixtures: a real PostgreSQL test database reset to the brief's initial state before each test."""
import os
from datetime import datetime

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text

from app import create_app
from app.config import Config
from app.infrastructure.db import init_schema
from app.infrastructure.services import BOGOTA, OPERATORS, SessionTokens
from app.seed import seed_example_data

BASE_URL = os.environ["TEST_DATABASE_URL"]          # .../reto_test
KEY = Fernet.generate_key().decode()
SECRET = "s" * 40
TODAY = datetime(2026, 11, 23, 10, 0, tzinfo=BOGOTA)   # the brief's "Monday 23 November 2026"


class FixedClock:
    """Clock frozen at a given instant, injected so tests do not depend on the real time."""

    def __init__(self, t):
        """Initialise the instance.

        Args:
            t: The instant `now()` will always return.
        """
        self.t = t

    def now(self):
        """Return the frozen instant."""
        return self.t


def _create_db_if_missing():
    """Create the `reto_test` database in the Compose PostgreSQL if it does not exist yet."""
    admin = BASE_URL.rsplit("/", 1)[0] + "/postgres"
    name = BASE_URL.rsplit("/", 1)[1]
    e = create_engine(admin.replace("postgresql://", "postgresql+psycopg://"), isolation_level="AUTOCOMMIT")
    with e.connect() as c:
        if not c.execute(text("SELECT 1 FROM pg_database WHERE datname=:n"), {"n": name}).first():
            c.execute(text(f'CREATE DATABASE "{name}"'))
    e.dispose()


@pytest.fixture(scope="session")
def app():
    """Session-scoped Flask app bound to the test database, with the schema initialised."""
    _create_db_if_missing()
    a = create_app(Config(BASE_URL, SECRET, (KEY,)), clock=FixedClock(TODAY))
    init_schema(a.extensions["engine"])
    return a


@pytest.fixture(autouse=True)
def data(app):
    """Brief's initial state before every test (TRUNCATE does not fire the immutability trigger)."""
    e = app.extensions["engine"]
    with e.begin() as c:
        c.execute(text("TRUNCATE dispatches, plots CASCADE"))
    seed_example_data(e, app.extensions["encryptor"])


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def auth(app):
    """Factory of `Authorization` headers.

    Called as `auth("B-SUR-01")` or `auth("B-SUR-01", "en")` to also set `Accept-Language`.
    """
    tokens = SessionTokens(SECRET)
    return lambda session, lang=None: {"Authorization": "Bearer " + tokens.issue(OPERATORS[session]),
                                       **({"Accept-Language": lang} if lang else {})}


def body(order, product, dose, national_id, **extra):
    """Request body using the API's (Spanish) wire field names."""
    return {"orden": order, "producto": product, "dosis_kg_ha": dose, "cedula_capataz": national_id, **extra}
