import logging
import os

from flask import Flask

from .api.routes import bp, register_hooks
from .application.use_cases import GetBalance, RegisterDispatch
from .config import Config
from .infrastructure.db import create_db_engine
from .infrastructure.repositories import uow_factory
from .infrastructure.services import NationalIdEncryptor, PersonalDataFilter, SessionTokens, SystemClock


def create_app(config: Config | None = None, clock=None) -> Flask:
    """Application factory and composition root.

    This is the only place that knows the concrete implementations: it builds the
    engine, encryptor, token service and use cases and wires them together.

    Args:
        config: Settings. When omitted they are read from the environment.
        clock: Time source. Tests inject a fixed clock; production uses the system clock.

    Returns:
        A configured Flask application.
    """
    config = config or Config.from_env()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4096
    app.json.sort_keys = False

    _configure_logging()
    engine = create_db_engine(config.database_url)
    uow = uow_factory(engine)
    encryptor = NationalIdEncryptor(config.national_id_keys)
    # Composition root: the only place that knows the concrete implementations.
    app.extensions.update(
        config=config, engine=engine, encryptor=encryptor,
        tokens=SessionTokens(config.jwt_secret, config.token_hours),
        register=RegisterDispatch(uow, clock or SystemClock(), encryptor),
        balance=GetBalance(uow),
    )
    app.register_blueprint(bp)
    register_hooks(app)

    from .cli import register_commands
    register_commands(app)
    return app


def _configure_logging() -> None:
    """Install a single stream handler that redacts personal data (see `PersonalDataFilter`).

    The level comes from the `LOG_LEVEL` environment variable (default INFO).
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(PersonalDataFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
