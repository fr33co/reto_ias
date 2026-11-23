"""HTTP routes (Flask blueprint) for the two endpoints of the brief.

This module is the *input adapter*: it authenticates the request, parses the body,
calls a use case and maps domain exceptions to HTTP status codes. It contains no
business rules.
"""
import json
import logging
import re
import time
from decimal import Decimal
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.exceptions import HTTPException

from ..domain import nitrogen as nit
from ..domain.errors import (AccessDenied, DuplicateOrder, FieldError, InvalidData,
                             NitrogenLimitExceeded, PlotNotFound)
from .i18n import number, translate
from .schemas import parse_dispatch_request
from .serializers import balance_json, dispatch_json

bp = Blueprint("api", __name__, url_prefix="/api/v1")
log = logging.getLogger("ventanilla.api")
_PLOT = re.compile(r"S-\d{3}")


def _reject_constant(c):
    """Reject the JSON constants `NaN`, `Infinity` and `-Infinity` (not valid numbers for a dose).

    Raises:
        ValueError: Always.
    """
    raise ValueError(c)


def _error(status: int, code: str, **extra):
    """Build a JSON error response with a translated message.

    Args:
        status: HTTP status code.
        code: Message code to translate.
        **extra: Additional JSON fields (e.g. `motivo`).

    Returns:
        A `(response, status)` tuple.
    """
    return jsonify({"mensaje": translate(code), **extra}), status


def requires_session(f):
    """Decorator: require a valid `Authorization: Bearer <token>` header.

    On success the verified `OperatorSession` is stored in `flask.g.session`. Otherwise
    the request is answered with 401 and a `WWW-Authenticate: Bearer` header.

    Args:
        f: The view function to protect.

    Returns:
        The wrapped view.
    """
    @wraps(f)
    def wrapper(*a, **kw):
        """Validate the bearer token and call the wrapped view with the session available."""
        auth = request.headers.get("Authorization", "")
        session = None
        if auth.startswith("Bearer "):
            session = current_app.extensions["tokens"].verify(auth[7:].strip())
        if session is None:
            body, status = _error(401, "session_invalid")
            return body, status, {"WWW-Authenticate": "Bearer"}
        g.session = session
        return f(*a, **kw)
    return wrapper


@bp.errorhandler(PlotNotFound)
def _plot_not_found(_):
    """Map `PlotNotFound` to 404."""
    return _error(404, "plot_not_found")


@bp.errorhandler(AccessDenied)
def _access_denied(_):
    """Map `AccessDenied` (plot of another warehouse) to 403."""
    return _error(403, "plot_forbidden")


@bp.errorhandler(DuplicateOrder)
def _duplicate(_):
    """Map `DuplicateOrder` to 409 with `motivo: ORDEN_DUPLICADA`."""
    return _error(409, "duplicate_order", motivo="ORDEN_DUPLICADA")


@bp.errorhandler(InvalidData)
def _invalid(e: InvalidData):
    """Map `InvalidData` to 400 with the contract's `errores` list (one entry per field).

    Messages are translated here and never echo the submitted values (privacy).
    """
    return jsonify({"errores": [{"campo": x.field, "mensaje": translate(x.code, **x.params)}
                                for x in e.errors]}), 400


@bp.errorhandler(NitrogenLimitExceeded)
def _limit(e: NitrogenLimitExceeded):
    """Map `NitrogenLimitExceeded` to 409 `LIMITE_NITROGENO`.

    The body carries the dispatch's N per hectare, the maximum bags of that product that
    still fit and the full balance, so the client can adjust without another request.
    """
    b = e.balance
    available = nit.available_kg_ha(b.cycle_n_g, b.plot.net_area_dha)
    return jsonify({
        "motivo": "LIMITE_NITROGENO",
        "mensaje": translate("limit_exceeded", available=number(available)),
        "n_despacho_kg_ha": float(nit.to_kg_ha(e.dispatch_n_g, b.plot.net_area_dha)),
        "bultos_maximos": e.max_bags,
        "balance": balance_json(b),
    }), 409


@bp.post("/suertes/<code>/despachos")
@requires_session
def register_dispatch(code: str):
    """`POST /suertes/<code>/despachos`: register a dispatch if it respects the nitrogen limit.

    The JSON is parsed with `Decimal` floats so `43.7` arrives exactly.

    Args:
        code: Plot code (`S-NNN`).

    Returns:
        201 with the created dispatch.

    Raises:
        PlotNotFound: Malformed or unknown plot code (handled -> 404).
        InvalidData: Bad content type, broken JSON or invalid fields (handled -> 400).
    """
    if not _PLOT.fullmatch(code):
        raise PlotNotFound()
    if not request.is_json:
        raise InvalidData([FieldError("_general", "content_type_json")])
    try:
        # parse_float=Decimal: 43.7 arrives exactly, not as 43.70000000000000284...
        data = json.loads(request.get_data(), parse_float=Decimal, parse_constant=_reject_constant)
    except (ValueError, UnicodeDecodeError):
        raise InvalidData([FieldError("_general", "invalid_json")])
    dispatch = current_app.extensions["register"].execute(g.session, code, parse_dispatch_request(data))
    return jsonify(dispatch_json(dispatch)), 201


@bp.get("/suertes/<code>/balance-nitrogeno")
@requires_session
def nitrogen_balance(code: str):
    """`GET /suertes/<code>/balance-nitrogeno`: nitrogen balance and paginated history.

    Args:
        code: Plot code (`S-NNN`).

    Returns:
        200 with the balance. The query parameter `pagina` (default 1) selects the history page.

    Raises:
        PlotNotFound: Malformed or unknown plot code (handled -> 404).
        InvalidData: `pagina` is not a positive integer (handled -> 400).
    """
    if not _PLOT.fullmatch(code):
        raise PlotNotFound()
    raw = request.args.get("pagina", "1")
    if not (raw.isascii() and raw.isdigit() and 1 <= int(raw) <= 100000):
        raise InvalidData([FieldError("pagina", "page_invalid")])
    balance = current_app.extensions["balance"].execute(g.session, code, int(raw))
    return jsonify(balance_json(balance))


def register_hooks(app):
    """Register request hooks and global error handlers on the application.

    Adds security headers, one access-log line per request (never the body) and JSON
    error handlers for 404, 405, 413 and unexpected exceptions.

    Args:
        app: The Flask application.
    """
    @app.before_request
    def _start():
        """Start the request timer."""
        g.t0 = time.perf_counter()

    @app.after_request
    def _headers(r):
        """Add security headers and write the access-log line.

        Args:
            r: The outgoing response.

        Returns:
            The same response with `Cache-Control: no-store`, CSP, `nosniff` and `no-referrer`.
        """
        r.headers["Cache-Control"] = "no-store"
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        r.headers["Referrer-Policy"] = "no-referrer"
        s = g.get("session")
        log.info("%s %s %s %dms session=%s", request.method, request.path, r.status_code,
                 (time.perf_counter() - g.get("t0", time.perf_counter())) * 1000, s.id if s else "-")
        return r

    @app.errorhandler(413)
    def _too_large(_):
        """Map a request body above the size limit to a 413."""
        return _error(413, "too_large")

    @app.errorhandler(404)
    def _not_found(_):
        """Map an unknown route to a JSON 404."""
        return _error(404, "not_found")

    @app.errorhandler(405)
    def _method(_):
        """Map a disallowed method (PUT/PATCH/DELETE on dispatches) to a JSON 405."""
        return _error(405, "method_not_allowed")

    @app.errorhandler(Exception)
    def _unexpected(e):
        """Last-resort handler: log the error without the request body and answer a generic 500.

        HTTP exceptions raised by Flask/Werkzeug keep their own status.
        """
        if isinstance(e, HTTPException):
            return jsonify({"mensaje": e.name}), e.code or 500
        log.exception("unhandled error")   # never includes the request body
        return _error(500, "internal_error")
