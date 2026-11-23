"""Runtime configuration read from environment variables (fail fast when missing)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Application settings.

    Attributes:
        database_url: SQLAlchemy/PostgreSQL URL.
        jwt_secret: HMAC secret for session tokens (>= 32 characters).
        national_id_keys: Fernet keys; the first encrypts, all decrypt (key rotation).
        token_hours: Session token lifetime in hours.
    """
    database_url: str
    jwt_secret: str
    national_id_keys: tuple[str, ...]
    token_hours: int = 12

    @classmethod
    def from_env(cls, env=os.environ) -> "Config":
        """Build the configuration from environment variables.

        Args:
            env: Mapping to read (defaults to `os.environ`).

        Raises:
            RuntimeError: A required variable is missing or `JWT_SECRET` is too short.
        """
        missing = [k for k in ("DATABASE_URL", "JWT_SECRET", "CEDULA_KEYS") if not env.get(k)]
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
        if len(env["JWT_SECRET"]) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters long")
        return cls(env["DATABASE_URL"], env["JWT_SECRET"],
                   tuple(k.strip() for k in env["CEDULA_KEYS"].split(",") if k.strip()),
                   int(env.get("TOKEN_HOURS", "12")))
