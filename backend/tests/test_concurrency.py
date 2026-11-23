"""Concurrency: the two South counters must never exceed a plot's limit together."""
import threading

from .conftest import body


def test_two_south_counters_never_exceed_the_limit_together(client, auth, app):
    """S-221 has 30.19 left; each order asks for 14 bags (20.13). Only one can fit."""
    results, barrier = [], threading.Barrier(6)

    def fire(i):
        """Wait at the barrier so all requests start together, then post one dispatch and record the status."""
        session = "B-SUR-01" if i % 2 == 0 else "B-SUR-02"
        c = app.test_client()
        barrier.wait()
        r = c.post("/api/v1/suertes/S-221/despachos", json=body(f"OF-2026-30{i:02d}", "URE", 20.0, "1113990457"),
                   headers=auth(session))
        results.append(r.status_code)

    threads = [threading.Thread(target=fire, args=(i,)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert sorted(results) == [201, 409, 409, 409, 409, 409]
    b = client.get("/api/v1/suertes/S-221/balance-nitrogeno", headers=auth("B-SUR-01")).json
    assert b["n_ciclo_kg_ha"] <= 160
