"""INCIDENTE.md: the limit must never depend on the history page."""
from sqlalchemy import text

from .conftest import body


def test_balance_sums_the_whole_cycle_not_just_the_first_page(client, auth):
    """S-208 has 104 dispatches (3 pages): the balance must sum all of them (98.44), not one page."""
    b = client.get("/api/v1/suertes/S-208/balance-nitrogeno", headers=auth("B-SUR-01")).json
    # 104 dispatches x 2 bags of urea = 4784 kg N / 48.6 ha
    assert b["n_ciclo_kg_ha"] == 98.44 and b["n_disponible_kg_ha"] == 61.56
    assert b["historial"]["paginas"] == 3 and len(b["historial"]["despachos"]) == 50


def test_history_pages_of_50_newest_first(client, auth):
    """History pages hold 50 rows, newest first; page 3 has the remaining 4 and page 4 is empty."""
    page = lambda p: client.get(f"/api/v1/suertes/S-208/balance-nitrogeno?pagina={p}", headers=auth("B-SUR-01")).json["historial"]
    p1, p3 = page(1), page(3)
    assert p1["despachos"][0]["registrado_en"] > p1["despachos"][-1]["registrado_en"]
    assert p1["despachos"][0]["registrado_en"].startswith("2026-11-22T14:30")
    assert len(p3["despachos"]) == 4 and page(4)["despachos"] == []


def test_limit_still_applies_with_more_than_50_rows_in_the_cycle(app, client, auth):
    """Reproduces S-305: with 100+ dispatches in the cycle the limit must stay enforced."""
    with app.extensions["engine"].begin() as c:
        # 2,894,600 g of N on top of the 104 existing rows -> S-208 sits at 158.00 kg N/ha (cycle total 4,784 + 2,894.6 kg)
        c.execute(text("""INSERT INTO dispatches VALUES (gen_random_uuid(), 'OF-2026-0900', 'S-208', 'SAM', 100,
            276, 13800, 2894600, 'x', '0001', 'SUR-1', 'B-SUR-01', '2026-11-22 20:00-05', '2026-11-22')"""))
    h = auth("B-SUR-01")
    # 10 kg N/ha = 21 bags = 9.94 kg/ha -> 167.9 total: must be rejected (v1 would have accepted it)
    r = client.post("/api/v1/suertes/S-208/despachos", json=body("OF-2026-1300", "URE", 10.0, "16723845"), headers=h)
    assert r.status_code == 409 and r.json["balance"]["n_ciclo_kg_ha"] == 158.0
    # 2 kg N/ha = 4 bags = 1.89 kg/ha -> 159.89 total: still fits
    r = client.post("/api/v1/suertes/S-208/despachos", json=body("OF-2026-1301", "URE", 2.0, "16723845"), headers=h)
    assert r.status_code == 201, r.json
