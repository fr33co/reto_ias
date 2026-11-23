"""Technical services: clock, national-id encryption, session tokens and log redaction."""
import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import jwt
from cryptography.fernet import Fernet, MultiFernet

from ..domain.models import OperatorSession

BOGOTA = ZoneInfo("America/Bogota")
ISSUER = "ventanilla-guabina"

# Simulated sessions. In production these are the corporate IdP's claims (see DECISIONES.md D-12).
OPERATORS = {
    "B-NORTE-01": OperatorSession("B-NORTE-01", "NORTE", "NORTE-1"),
    "B-SUR-01": OperatorSession("B-SUR-01", "SUR", "SUR-1"),
    "B-SUR-02": OperatorSession("B-SUR-02", "SUR", "SUR-2"),
}


class SystemClock:
    """Real clock in the America/Bogota timezone."""

    def now(self) -> datetime:
        """Current time with the Bogota timezone."""
        return datetime.now(BOGOTA)


class NationalIdEncryptor:
    """Fernet (AES-128-CBC + HMAC). MultiFernet: the first key encrypts, all keys decrypt (rotation)."""

    def __init__(self, keys: tuple[str, ...]):
        """Initialise the instance.

        Args:
            keys: Fernet keys; the first encrypts, every key can decrypt (rotation).
        """
        self._f = MultiFernet([Fernet(k) for k in keys])

    def encrypt(self, text: str) -> str:
        """Encrypt a national id.

        Returns:
            An opaque token that does not contain the id.
        """
        return self._f.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt a stored id (authorised audits only).

        Raises:
            cryptography.fernet.InvalidToken: The token is corrupt or the key is unknown.
        """
        return self._f.decrypt(token.encode()).decode()


class SessionTokens:
    """Issues and verifies simulated session tokens (HS256 JWT).

    In production the corporate identity provider issues the token and only `verify` changes.
    """
    def __init__(self, secret: str, hours: int = 12):
        """Initialise the instance.

        Args:
            secret: HMAC secret (>= 32 characters).
            hours: Token lifetime.
        """
        self._secret, self._hours = secret, hours

    def issue(self, s: OperatorSession) -> str:
        """Create a signed token carrying warehouse and counter as claims.

        Args:
            s: The operator's session.

        Returns:
            The encoded JWT (`sub`, `bodega`, `ventanilla`, `iss`, `iat`, `exp`).
        """
        now = datetime.now(timezone.utc)
        return jwt.encode({"sub": s.id, "bodega": s.warehouse, "ventanilla": s.counter, "iss": ISSUER,
                           "iat": now, "exp": now + timedelta(hours=self._hours)},
                          self._secret, algorithm="HS256")

    def verify(self, token: str) -> OperatorSession | None:
        """Verify signature, issuer and expiry.

        Only HS256 is accepted (so `alg=none` is rejected).

        Args:
            token: The bearer token.

        Returns:
            The session, or `None` if the token is invalid, expired or has an unknown warehouse.
        """
        try:
            c = jwt.decode(token, self._secret, algorithms=["HS256"], issuer=ISSUER,
                           options={"require": ["exp", "sub", "bodega", "ventanilla"]})
        except jwt.PyJWTError:
            return None
        if c["bodega"] not in ("NORTE", "SUR"):
            return None
        return OperatorSession(str(c["sub"]), c["bodega"], str(c["ventanilla"]))


class PersonalDataFilter(logging.Filter):
    """Defense in depth: no 6-10 digit sequence (a national id) ever reaches the logs."""
    _ID = re.compile(r"(?<![\w-])\d{6,10}(?![\w-])")

    def filter(self, record: logging.LogRecord) -> bool:
        """Replace any 6-10 digit sequence in the message with `[ID]`.

        Returns:
            Always `True` (the record is kept, only redacted).
        """
        record.msg = self._ID.sub("[ID]", record.getMessage())
        record.args = ()
        return True
