"""Privacy of the foreman's national id, security headers and dispatch immutability."""
import logging

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.infrastructure.services import PersonalDataFilter

from .conftest import body

NATIONAL_ID = "1113654321"


def register(client, auth):
    """Register OF-2026-1187 on S-104 with the test foreman id."""
    return client.post("/api/v1/suertes/S-104/despachos", json=body("OF-2026-1187", "URE", 80.0, NATIONAL_ID),
                       headers=auth("B-NORTE-01"))


def test_id_is_encrypted_in_the_db_and_never_in_responses(app, client, auth):
    """The id is stored encrypted (decryptable), and responses only show `xxxxxx4321`."""
    r = register(client, auth)
    assert NATIONAL_ID not in r.get_data(as_text=True)
    b = client.get("/api/v1/suertes/S-104/balance-nitrogeno", headers=auth("B-NORTE-01"))
    assert NATIONAL_ID not in b.get_data(as_text=True) and "xxxxxx4321" in b.get_data(as_text=True)
    with app.extensions["engine"].connect() as c:
        row = c.execute(text("SELECT foreman_encrypted_id, foreman_last4 FROM dispatches WHERE order_no='OF-2026-1187'")).one()
    assert NATIONAL_ID not in row.foreman_encrypted_id and row.foreman_last4 == "4321"
    assert app.extensions["encryptor"].decrypt(row.foreman_encrypted_id) == NATIONAL_ID


def test_id_never_reaches_the_logs(client, auth, caplog):
    """Neither valid nor invalid requests write the national id to the logs."""
    with caplog.at_level(logging.DEBUG):
        register(client, auth)
        client.post("/api/v1/suertes/S-104/despachos", json=body("bad", "URE", 80.0, NATIONAL_ID), headers=auth("B-NORTE-01"))
    assert NATIONAL_ID not in caplog.text


def test_log_filter_masks_ids_inside_messages():
    """The log filter replaces id-like digit runs but keeps order numbers such as `OF-2026-1187`."""
    r = logging.LogRecord("x", logging.INFO, "", 0, "foreman %s order OF-2026-1187", ("1113654321",), None)
    PersonalDataFilter().filter(r)
    assert r.msg == "foreman [ID] order OF-2026-1187"


def test_security_headers(client, auth):
    """Responses are not cacheable and not sniffable."""
    r = client.get("/api/v1/suertes/S-104/balance-nitrogeno", headers=auth("B-NORTE-01"))
    assert r.headers["Cache-Control"] == "no-store" and r.headers["X-Content-Type-Options"] == "nosniff"


def test_dispatches_are_immutable_in_the_database(app, client, auth):
    """UPDATE and DELETE on dispatches are rejected by the database trigger."""
    register(client, auth)
    for sql in ("UPDATE dispatches SET bags = 1", "DELETE FROM dispatches"):
        with pytest.raises(DBAPIError, match="immutable"):
            with app.extensions["engine"].begin() as c:
                c.execute(text(sql))


def test_there_are_no_routes_to_modify_or_delete(client, auth):
    """PUT, PATCH and DELETE on the dispatches route answer 405."""
    h = auth("B-NORTE-01")
    for method in (client.put, client.patch, client.delete):
        assert method("/api/v1/suertes/S-104/despachos", headers=h).status_code == 405
