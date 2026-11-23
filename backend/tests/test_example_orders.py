"""The brief's 6 example orders, in order and with their own session."""
from .conftest import body


def post(client, auth, session, plot, **kw):
    """POST a dispatch for `plot` as `session`, using the contract's field names."""
    return client.post(f"/api/v1/suertes/{plot}/despachos", json=body(**kw), headers=auth(session))


def test_six_orders_in_sequence(client, auth):
    """The brief's six example orders, in order, each with its own session.

    Covers: a normal acceptance (1187), DAP counting its nitrogen (1190), a 409 that depends on
    the previous order (1191, max 52 bags), a bag count that fits only with nearest rounding
    (1195), a nitrogen-free product (1196) and a dispatch landing exactly on 160.00 (1198).
    """
    # 1187: S-104 URE 80 -> 147.83 -> 148 bags; prior cycle N is 65.48 (matches the audit)
    r = post(client, auth, "B-NORTE-01", "S-104", order="OF-2026-1187", product="URE", dose=80.0, national_id="1113654321")
    assert r.status_code == 201, r.json
    assert (r.json["bultos"], r.json["kg_entregados"], r.json["n_despacho_kg_ha"]) == (148, 7400, 80.09)
    assert r.json["capataz"] == "xxxxxx4321" and "1113654321" not in r.get_data(as_text=True)
    assert r.json["ventanilla"] == "NORTE-1" and r.json["registrado_por"] == "B-NORTE-01"

    # 1190: S-117 DAP 46 kg P2O5/ha -> 70 bags, contributes 17.90 of N (every product's N counts)
    r = post(client, auth, "B-NORTE-01", "S-117", order="OF-2026-1190", product="DAP", dose=46.0, national_id="94387120")
    assert r.status_code == 201 and r.json["bultos"] == 70 and r.json["n_despacho_kg_ha"] == 17.9

    # 1191: S-117 URE 40 -> 61 bags but only 52 fit (depends on 1190 being already registered)
    r = post(client, auth, "B-NORTE-01", "S-117", order="OF-2026-1191", product="URE", dose=40.0, national_id="94387120")
    assert r.status_code == 409
    assert r.json["motivo"] == "LIMITE_NITROGENO" and r.json["bultos_maximos"] == 52
    assert r.json["n_despacho_kg_ha"] == 39.86
    assert r.json["balance"]["n_ciclo_kg_ha"] == 125.57 and r.json["balance"]["n_disponible_kg_ha"] == 34.43
    assert len(r.json["balance"]["historial"]["despachos"]) == 3

    # 1195: S-212 URE 43.7 -> 52.06 -> 52 bags (43.65) fit in the 43.76 available
    r = post(client, auth, "B-SUR-02", "S-212", order="OF-2026-1195", product="URE", dose=43.7, national_id="1006281774")
    assert r.status_code == 201 and r.json["bultos"] == 52 and r.json["ventanilla"] == "SUR-2"

    # 1196: S-208 KCL 120 K2O -> 194 bags, 0 N: delivered even though the cycle already has 98.44
    r = post(client, auth, "B-SUR-01", "S-208", order="OF-2026-1196", product="KCL", dose=120.0, national_id="16723845")
    assert r.status_code == 201 and r.json["bultos"] == 194 and r.json["n_despacho_kg_ha"] == 0.0

    # 1198: S-221 URE 30 -> 21 bags: the cycle lands EXACTLY on 160.00 and is accepted (<=)
    r = post(client, auth, "B-SUR-01", "S-221", order="OF-2026-1198", product="URE", dose=30.0, national_id="1113990457")
    assert r.status_code == 201 and r.json["bultos"] == 21
    b = client.get("/api/v1/suertes/S-221/balance-nitrogeno", headers=auth("B-SUR-01")).json
    assert b["n_ciclo_kg_ha"] == 160.0 and b["n_disponible_kg_ha"] == 0.0


def test_full_cycle_rejects_nitrogen_products_but_not_kcl(client, auth):
    """Once a plot is at the limit, any nitrogen product is rejected (0 bags fit) but KCL is still delivered."""
    post(client, auth, "B-SUR-01", "S-221", order="OF-2026-1198", product="URE", dose=30.0, national_id="1113990457")
    r = post(client, auth, "B-SUR-01", "S-221", order="OF-2026-1199", product="URE", dose=1.0, national_id="1113990457")
    assert r.status_code == 409 and r.json["bultos_maximos"] == 0
    r = post(client, auth, "B-SUR-01", "S-221", order="OF-2026-1200", product="KCL", dose=10.0, national_id="1113990457")
    assert r.status_code == 201


def test_initial_s104_balance_matches_the_audit(client, auth):
    """S-104's initial balance is 65.48 kg N/ha (as in the audit) and excludes the previous cycle's June dispatch."""
    b = client.get("/api/v1/suertes/S-104/balance-nitrogeno", headers=auth("B-NORTE-01")).json
    assert b["n_ciclo_kg_ha"] == 65.48 and b["limite_n_kg_ha"] == 160 and b["inicio_ciclo"] == "2026-08-21"
    assert [d["producto"] for d in b["historial"]["despachos"]] == ["DAP", "URE"]   # June's is a previous cycle
