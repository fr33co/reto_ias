"""Input validation, access control (401/403/404), idempotency and message translation."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from .conftest import body

URL = "/api/v1/suertes/S-104/despachos"
OK = body("OF-2026-1187", "URE", 80.0, "1113654321")


@pytest.mark.parametrize("field,value", [
    ("orden", "OF-26-1187"), ("orden", None), ("producto", "XXX"), ("producto", 5),
    ("dosis_kg_ha", 0), ("dosis_kg_ha", -1), ("dosis_kg_ha", 200.1), ("dosis_kg_ha", 80.05),
    ("dosis_kg_ha", "80"), ("dosis_kg_ha", True), ("dosis_kg_ha", None),
    ("cedula_capataz", "12345"), ("cedula_capataz", "12345678901"), ("cedula_capataz", 1113654321),
    ("cedula_capataz", "11136a4321"),
])
def test_400_names_the_field_and_never_echoes_the_id(client, auth, field, value):
    """Each invalid value yields a 400 naming exactly that field and never repeats the national id."""
    r = client.post(URL, json={**OK, field: value}, headers=auth("B-NORTE-01"))
    assert r.status_code == 400
    assert [e["campo"] for e in r.json["errores"]] == [field]
    assert "1113654321" not in r.get_data(as_text=True)


@pytest.mark.parametrize("dose", [0.1, 200.0, 200, 1, 80])
def test_valid_dose_boundaries_pass_format_validation(client, auth, dose):
    """Doses at the edges (0.1, 200, integers) pass format validation; any 400 must be a dose error, not a format one."""
    r = client.post(URL, json={**OK, "dosis_kg_ha": dose}, headers=auth("B-NORTE-01"))
    assert r.status_code in (201, 400, 409)
    if r.status_code == 400:   # 0.1 kg/ha on S-104 is less than a bag: a dose error, not a format error
        assert r.json["errores"][0]["campo"] == "dosis_kg_ha"


def test_several_errors_at_once(client, auth):
    """All wrong fields are reported together in one 400."""
    r = client.post(URL, json={"orden": "x", "producto": "URE", "dosis_kg_ha": 0, "cedula_capataz": "1"},
                    headers=auth("B-NORTE-01"))
    assert {e["campo"] for e in r.json["errores"]} == {"orden", "dosis_kg_ha", "cedula_capataz"}


def test_extra_fields_broken_json_and_content_type(client, auth):
    """Unknown fields, broken JSON, `NaN`, wrong content type and oversized bodies are rejected (400/413)."""
    h = auth("B-NORTE-01")
    assert client.post(URL, json={**OK, "admin": 1}, headers=h).status_code == 400
    assert client.post(URL, data="{broken", content_type="application/json", headers=h).status_code == 400
    assert client.post(URL, data='{"dosis_kg_ha": NaN}', content_type="application/json", headers=h).status_code == 400
    assert client.post(URL, data="x", content_type="text/plain", headers=h).status_code == 400
    assert client.post(URL, data="x" * 5000, content_type="application/json", headers=h).status_code == 413


def test_confirmed_bags_must_match(client, auth):
    """If `bultos_confirmados` differs from the computed bags the request is rejected and nothing is registered."""
    h = auth("B-NORTE-01")
    r = client.post(URL, json={**OK, "bultos_confirmados": 147}, headers=h)
    assert r.status_code == 400 and r.json["errores"][0]["campo"] == "bultos_confirmados"
    assert client.post(URL, json={**OK, "bultos_confirmados": 148}, headers=h).status_code == 201


def test_a_duplicate_order_is_not_dispatched_twice(client, auth):
    """A repeated order answers 409 `ORDEN_DUPLICADA`."""
    h = auth("B-NORTE-01")
    assert client.post(URL, json=OK, headers=h).status_code == 201
    r = client.post(URL, json=OK, headers=h)
    assert r.status_code == 409 and r.json["motivo"] == "ORDEN_DUPLICADA"


def test_403_other_warehouse_404_missing_401_no_session(client, auth):
    """403 for another warehouse's plot, 404 for unknown or malformed codes, 401 without a valid token."""
    assert client.post("/api/v1/suertes/S-208/despachos", json=OK, headers=auth("B-NORTE-01")).status_code == 403
    assert client.get("/api/v1/suertes/S-104/balance-nitrogeno", headers=auth("B-SUR-01")).status_code == 403
    assert client.post("/api/v1/suertes/S-999/despachos", json=OK, headers=auth("B-NORTE-01")).status_code == 404
    assert client.get("/api/v1/suertes/XYZ/balance-nitrogeno", headers=auth("B-NORTE-01")).status_code == 404
    assert client.get("/api/v1/suertes/S-104/balance-nitrogeno").status_code == 401
    assert client.get("/api/v1/suertes/S-104/balance-nitrogeno", headers={"Authorization": "Bearer abc"}).status_code == 401


def test_foreign_expired_and_unsigned_tokens_are_rejected(client):
    """Tokens signed with another key, expired, or with `alg=none` are rejected with 401."""
    base = {"sub": "B-SUR-01", "bodega": "SUR", "ventanilla": "SUR-1", "iss": "ventanilla-guabina"}
    foreign = jwt.encode({**base, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "z" * 40, algorithm="HS256")
    expired = jwt.encode({**base, "exp": datetime.now(timezone.utc) - timedelta(hours=1)}, "s" * 40, algorithm="HS256")
    unsigned = jwt.encode({**base, "exp": 9999999999}, None, algorithm="none")
    for t in (foreign, expired, unsigned):
        r = client.get("/api/v1/suertes/S-208/balance-nitrogeno", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code == 401


@pytest.mark.parametrize("page", ["0", "-1", "x", "1.5", ""])
def test_invalid_page(client, auth, page):
    """`pagina` must be a positive integer."""
    r = client.get(f"/api/v1/suertes/S-104/balance-nitrogeno?pagina={page}", headers=auth("B-NORTE-01"))
    assert r.status_code == 400 and r.json["errores"][0]["campo"] == "pagina"


def test_messages_are_translated_from_accept_language(client, auth):
    """Error messages follow `Accept-Language` (Spanish by default, English on request)."""
    bad = {**OK, "orden": "x"}
    es = client.post(URL, json=bad, headers=auth("B-NORTE-01")).json["errores"][0]["mensaje"]
    en = client.post(URL, json=bad, headers=auth("B-NORTE-01", "en")).json["errores"][0]["mensaje"]
    assert es.startswith("Use el formato") and en.startswith("Use the format")
    assert client.get("/api/v1/suertes/S-104/balance-nitrogeno", headers={"Accept-Language": "en"}).json["mensaje"] \
        == "Invalid or expired session."


def test_limit_message_uses_the_language_decimal_separator(client, auth):
    """The 409 message uses a comma in Spanish (34,43) and a point in English (34.43)."""
    h, h_en = auth("B-NORTE-01"), auth("B-NORTE-01", "en")
    client.post("/api/v1/suertes/S-117/despachos", json=body("OF-2026-1190", "DAP", 46.0, "94387120"), headers=h)
    attempt = body("OF-2026-1191", "URE", 40.0, "94387120")
    assert "Disponible: 34,43 kg" in client.post("/api/v1/suertes/S-117/despachos", json=attempt, headers=h).json["mensaje"]
    assert "Available: 34.43 kg" in client.post("/api/v1/suertes/S-117/despachos", json=attempt, headers=h_en).json["mensaje"]
