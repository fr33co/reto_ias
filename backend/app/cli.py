"""Flask CLI commands: schema creation, example data and session-token issuing."""
import click

from .infrastructure.db import init_schema
from .infrastructure.services import OPERATORS
from .seed import seed_example_data


def register_commands(app):
    """Register the CLI commands `init-db`, `seed` and `issue-token`.

    Args:
        app: The Flask application.
    """
    @app.cli.command("init-db")
    def init_db():
        """Create the schema (idempotent)."""
        init_schema(app.extensions["engine"])
        click.echo("schema ready")

    @app.cli.command("seed")
    def seed():
        """Load the brief's example data (idempotent)."""
        seed_example_data(app.extensions["engine"], app.extensions["encryptor"])
        click.echo("example data loaded")

    @app.cli.command("issue-token")
    @click.argument("session", type=click.Choice(sorted(OPERATORS)))
    def issue_token(session):
        """Issue a simulated session token (stands in for the corporate IdP)."""
        click.echo(app.extensions["tokens"].issue(OPERATORS[session]))
